package com.demo.txnanalysisagent;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import software.amazon.awssdk.regions.Region;
import software.amazon.awssdk.services.bedrockruntime.BedrockRuntimeAsyncClient;
import software.amazon.awssdk.services.bedrockruntime.BedrockRuntimeClient;
import software.amazon.awssdk.services.bedrockruntime.model.*;

import java.util.List;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.function.Consumer;

/**
 * Invokes Amazon Bedrock's Converse API and returns the response
 * along with invocation metadata (tokens, latency).
 */
public class BedrockInvoker {

    private static final Logger log = LoggerFactory.getLogger(BedrockInvoker.class);

    private final BedrockRuntimeClient client;
    private final BedrockRuntimeAsyncClient asyncClient;

    public BedrockInvoker(String region) {
        this.client = BedrockRuntimeClient.builder()
                .region(Region.of(region))
                .build();
        this.asyncClient = BedrockRuntimeAsyncClient.builder()
                .region(Region.of(region))
                .build();
    }

    /**
     * Invokes the Bedrock Converse API with the given system prompt and user message.
     *
     * @param modelId      the Bedrock model ID to invoke
     * @param systemPrompt the system prompt text
     * @param userMessage  the user message (transaction log data)
     * @return an InvocationResult containing the response and metadata
     */
    public InvocationResult invoke(String modelId, String systemPrompt, String userMessage) {
        log.info("Invoking model: {} (message length: {} chars)", modelId, userMessage.length());

        SystemContentBlock system = SystemContentBlock.builder()
                .text(systemPrompt)
                .build();

        Message userMsg = Message.builder()
                .role(ConversationRole.USER)
                .content(ContentBlock.fromText(userMessage))
                .build();

        ConverseRequest request = ConverseRequest.builder()
                .modelId(modelId)
                .system(system)
                .messages(List.of(userMsg))
                .build();

        long startTime = System.currentTimeMillis();
        ConverseResponse response = client.converse(request);
        long latencyMs = System.currentTimeMillis() - startTime;

        // Extract response text
        String responseText = response.output().message().content().stream()
                .filter(block -> block.text() != null)
                .map(ContentBlock::text)
                .reduce("", (a, b) -> a + b);

        // Extract token usage
        TokenUsage usage = response.usage();
        int inputTokens = usage != null ? usage.inputTokens() : 0;
        int outputTokens = usage != null ? usage.outputTokens() : 0;

        log.info("Model response received: latency={}ms, inputTokens={}, outputTokens={}",
                latencyMs, inputTokens, outputTokens);

        return new InvocationResult(responseText, modelId, latencyMs, inputTokens, outputTokens);
    }

    /**
     * Holds the result of a Bedrock model invocation.
     */
    public record InvocationResult(
            String responseText,
            String modelId,
            long latencyMs,
            int inputTokens,
            int outputTokens
    ) {}

    /**
     * Streaming invocation via Bedrock ConverseStream API.
     * Calls onChunk for each text delta as it arrives, then returns the full InvocationResult.
     */
    public InvocationResult invokeStreaming(String modelId, String systemPrompt, String userMessage,
                                           Consumer<String> onChunk) {
        log.info("Invoking model (streaming): {} (message length: {} chars)", modelId, userMessage.length());

        SystemContentBlock system = SystemContentBlock.builder()
                .text(systemPrompt)
                .build();

        Message userMsg = Message.builder()
                .role(ConversationRole.USER)
                .content(ContentBlock.fromText(userMessage))
                .build();

        ConverseStreamRequest request = ConverseStreamRequest.builder()
                .modelId(modelId)
                .system(system)
                .messages(List.of(userMsg))
                .build();

        StringBuilder fullResponse = new StringBuilder();
        AtomicInteger inputTokens = new AtomicInteger(0);
        AtomicInteger outputTokens = new AtomicInteger(0);

        long startTime = System.currentTimeMillis();

        var handler = ConverseStreamResponseHandler.builder()
                .onEventStream(stream -> stream.subscribe(event -> {
                    if (event instanceof ContentBlockDeltaEvent delta) {
                        String text = delta.delta().text();
                        if (text != null) {
                            fullResponse.append(text);
                            onChunk.accept(text);
                        }
                    } else if (event instanceof ConverseStreamMetadataEvent metadata) {
                        TokenUsage usage = metadata.usage();
                        if (usage != null) {
                            inputTokens.set(usage.inputTokens());
                            outputTokens.set(usage.outputTokens());
                        }
                    }
                }))
                .build();

        asyncClient.converseStream(request, handler).join();

        long latencyMs = System.currentTimeMillis() - startTime;

        log.info("Streaming complete: latency={}ms, inputTokens={}, outputTokens={}",
                latencyMs, inputTokens.get(), outputTokens.get());

        return new InvocationResult(fullResponse.toString(), modelId, latencyMs, inputTokens.get(), outputTokens.get());
    }
}
