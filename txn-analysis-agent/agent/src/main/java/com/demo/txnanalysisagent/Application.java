package com.demo.txnanalysisagent;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.LinkedHashMap;
import java.util.Map;

/**
 * Entry point for local invocation of the transaction analysis agent.
 * Orchestrates the batch evaluation: calls TransactionAgent, then handles
 * cost calculation and CSV writing externally.
 */
public class Application {



    private static final Logger log = LoggerFactory.getLogger(Application.class);

    /**
     * Model pricing for ap-south-1 region (USD per 1M tokens).
     * Format: model_id -> [input_price_per_1M_tokens, output_price_per_1M_tokens]
     * Insertion order defines evaluation order.
     */
    private static final Map<String, double[]> MODEL_PRICING;

    static {
        MODEL_PRICING = new LinkedHashMap<>();
        MODEL_PRICING.put("global.anthropic.claude-haiku-4-5-20251001-v1:0", new double[]{1.00, 5.00});
        // MODEL_PRICING.put("apac.anthropic.claude-sonnet-4-20250514-v1:0",    new double[]{3.00, 15.00});
        // MODEL_PRICING.put("global.anthropic.claude-sonnet-4-6",              new double[]{3.00, 15.00});
        // MODEL_PRICING.put("global.anthropic.claude-opus-4-8",                new double[]{5.00, 25.00});
        // MODEL_PRICING.put("apac.amazon.nova-pro-v1:0",                       new double[]{1.48, 1.48});
        // MODEL_PRICING.put("deepseek.v3-v1:0",                                new double[]{0.682424, 1.976678});
        // MODEL_PRICING.put("deepseek.v3.2",                                   new double[]{0.74, 2.22});
        // MODEL_PRICING.put("minimax.minimax-m2.5",                            new double[]{0.36, 1.44});
        // MODEL_PRICING.put("moonshotai.kimi-k2.5",                            new double[]{0.72, 3.60});
        // MODEL_PRICING.put("qwen.qwen3-next-80b-a3b",                        new double[]{0.18, 1.41});
        // MODEL_PRICING.put("zai.glm-5",                                       new double[]{1.20, 3.84});
    }

    public static void main(String[] args) {
        AgentConfig config = AgentConfig.load();
        log.info("Starting Transaction Analysis Agent with config: {}", config);

        // Hardcoded transaction IDs to evaluate
        String[] transactionIds = {
                "txn_001",
                "txn_002",
                "txn_003",
                "txn_004",
                "txn_005"
        };

        BedrockInvoker invoker = new BedrockInvoker(config.getRegion());
        TransactionAgent agent = new TransactionAgent(config.getSystemPrompt(), config.getModelId(), invoker);
        CsvWriter csvWriter = new CsvWriter(config.getOutputCsvPath());

        log.info("Output CSV: {}", config.getOutputCsvPath());
        log.info("Models to evaluate: {}", MODEL_PRICING.size());
        log.info("Transactions to process per model: {}", transactionIds.length);

        for (String modelId : MODEL_PRICING.keySet()) {
            log.info("--- Evaluating model: {} ---", modelId);
            for (String txnId : transactionIds) {
                try {
                    // Read log file (outer layer responsibility)
                    Path logFile = config.resolveLogFile(txnId);
                    if (!Files.exists(logFile)) {
                        log.error("Log file not found: {}", logFile);
                        continue;
                    }
                    String logContent = Files.readString(logFile, StandardCharsets.UTF_8);

                    // Stream tokens to console, accumulate full response for CSV
                    System.out.printf("%n[%s | %s] ", modelId, txnId);
                    TransactionAgent.AnalysisResult result = agent.analyseStreaming(txnId, logContent, modelId,
                            chunk -> System.out.print(chunk));
                    System.out.println(); // newline after streaming completes

                    // Orchestration concerns: cost calculation + CSV writing
                    double totalCost = calculateCost(result.modelId(), result.inputTokens(), result.outputTokens());

                    log.info("Invocation complete: txn={}, model={}, latency={}ms, inputTokens={}, outputTokens={}, cost=${}",
                            txnId, result.modelId(), result.latencyMs(), result.inputTokens(), result.outputTokens(),
                            String.format("%.6f", totalCost));

                    // Write to CSV
                    csvWriter.append(
                            result.transactionId(),
                            result.inputLog(),
                            result.responseText(),
                            result.modelId(),
                            result.latencyMs(),
                            result.inputTokens(),
                            result.outputTokens(),
                            totalCost
                    );

                    log.info("Completed: model={}, txn={}, response={} chars", modelId, txnId, result.responseText().length());
                } catch (Exception e) {
                    log.error("Failed: model={}, txn={}", modelId, txnId, e);
                }
            }
        }

        log.info("All evaluations complete. Results written to: {}", config.getOutputCsvPath());
    }

    /**
     * Calculates the cost of a single invocation in USD.
     * cost = (inputTokens / 1_000_000 * inputPrice) + (outputTokens / 1_000_000 * outputPrice)
     */
    public static double calculateCost(String modelId, int inputTokens, int outputTokens) {
        double[] pricing = MODEL_PRICING.get(modelId);
        if (pricing == null) {
            log.warn("No pricing data for model: {}, returning 0.0", modelId);
            return 0.0;
        }
        double inputCost = (inputTokens / 1_000_000.0) * pricing[0];
        double outputCost = (outputTokens / 1_000_000.0) * pricing[1];
        return inputCost + outputCost;
    }
}
