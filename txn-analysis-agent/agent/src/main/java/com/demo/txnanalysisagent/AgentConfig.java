package com.demo.txnanalysisagent;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.IOException;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.nio.file.Path;
import java.util.Properties;

/**
 * Loads agent configuration from application.properties and environment variables.
 * Environment variables take precedence over properties file values.
 */
public class AgentConfig {

    private static final Logger log = LoggerFactory.getLogger(AgentConfig.class);

    private final String modelId;
    private final String region;
    private final Path workdir;
    private final String systemPrompt;

    private AgentConfig(String modelId, String region, Path workdir, String systemPrompt) {
        this.modelId = modelId;
        this.region = region;
        this.workdir = workdir;
        this.systemPrompt = systemPrompt;
    }

    public static AgentConfig load() {
        Properties props = new Properties();
        try (InputStream input = AgentConfig.class.getClassLoader()
                .getResourceAsStream("application.properties")) {
            if (input != null) {
                props.load(input);
            }
        } catch (IOException e) {
            throw new RuntimeException("Failed to load application.properties", e);
        }

        String modelId = resolve("BEDROCK_MODEL_ID", "bedrock.model.id", props,
                "global.anthropic.claude-haiku-4-5-20251001-v1:0");
        String region = resolve("BEDROCK_REGION", "bedrock.region", props, "ap-south-1");
        String workdirStr = resolve("AGENT_WORKDIR", "agent.workdir", props, "./workdir");
        Path workdir = Path.of(workdirStr).toAbsolutePath().normalize();

        String systemPrompt = loadSystemPromptFromClasspath();

        log.info("Agent config loaded: model={}, region={}, workdir={}", modelId, region, workdir);
        return new AgentConfig(modelId, region, workdir, systemPrompt);
    }

    private static String loadSystemPromptFromClasspath() {
        try (InputStream is = AgentConfig.class.getClassLoader().getResourceAsStream("system_prompt.md")) {
            if (is == null) {
                log.warn("system_prompt.md not found on classpath, using default");
                return "You are a helpful AI assistant.";
            }
            return new String(is.readAllBytes(), StandardCharsets.UTF_8).trim();
        } catch (IOException e) {
            log.error("Failed to read system_prompt.md from classpath", e);
            return "You are a helpful AI assistant.";
        }
    }

    private static String resolve(String envKey, String propKey, Properties props, String defaultValue) {
        String envValue = System.getenv(envKey);
        if (envValue != null && !envValue.isBlank()) {
            return envValue;
        }
        return props.getProperty(propKey, defaultValue);
    }

    public String getModelId() { return modelId; }
    public String getRegion() { return region; }
    public Path getWorkdir() { return workdir; }
    public String getSystemPrompt() { return systemPrompt; }

    /** Path to the evaluation-dataset directory. */
    public Path getEvaluationDatasetDir() { return workdir.resolve("evaluation-dataset"); }

    /** Resolves the log file path for a given transaction ID. */
    public Path resolveLogFile(String txnId) { return getEvaluationDatasetDir().resolve(txnId + ".log"); }

    /** Path to the output CSV file. */
    public Path getOutputCsvPath() { return workdir.resolve("evaluation_results.csv"); }

    @Override
    public String toString() {
        return "AgentConfig{modelId='%s', region='%s', workdir=%s}".formatted(modelId, region, workdir);
    }
}
