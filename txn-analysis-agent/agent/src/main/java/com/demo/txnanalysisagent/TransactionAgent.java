package com.demo.txnanalysisagent;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.function.Consumer;

/**
 * Core agent that invokes the Bedrock model with a transaction log.
 * Stateless — receives log content as input, knows nothing about workdir or file I/O.
 */
public class TransactionAgent {

    private static final Logger log = LoggerFactory.getLogger(TransactionAgent.class);

    private final String systemPrompt;
    private final String defaultModelId;
    private final BedrockInvoker invoker;

    public TransactionAgent(String systemPrompt, String defaultModelId, BedrockInvoker invoker) {
        this.systemPrompt = systemPrompt;
        this.defaultModelId = defaultModelId;
        this.invoker = invoker;
    }

    /**
     * Analyses a transaction log (non-streaming).
     *
     * @param txnId      transaction ID (for labelling only)
     * @param logContent the raw log text
     * @param modelId    model to use (null = default)
     */
    public AnalysisResult analyse(String txnId, String logContent, String modelId) {
        String effectiveModelId = (modelId != null && !modelId.isBlank()) ? modelId : defaultModelId;
        log.info("Analysing txn={} with model={} ({} bytes)", txnId, effectiveModelId, logContent.length());

        BedrockInvoker.InvocationResult inv = invoker.invoke(effectiveModelId, systemPrompt, logContent);

        return new AnalysisResult(txnId, logContent, inv.responseText(), effectiveModelId,
                inv.latencyMs(), inv.inputTokens(), inv.outputTokens());
    }

    /**
     * Streaming variant — streams text chunks via onChunk callback.
     */
    public AnalysisResult analyseStreaming(String txnId, String logContent, String modelId, Consumer<String> onChunk) {
        String effectiveModelId = (modelId != null && !modelId.isBlank()) ? modelId : defaultModelId;
        log.info("Analysing (streaming) txn={} with model={} ({} bytes)", txnId, effectiveModelId, logContent.length());

        BedrockInvoker.InvocationResult inv = invoker.invokeStreaming(effectiveModelId, systemPrompt, logContent, onChunk);

        return new AnalysisResult(txnId, logContent, inv.responseText(), effectiveModelId,
                inv.latencyMs(), inv.inputTokens(), inv.outputTokens());
    }

    public record AnalysisResult(
            String transactionId,
            String inputLog,
            String responseText,
            String modelId,
            long latencyMs,
            int inputTokens,
            int outputTokens
    ) {}
}
