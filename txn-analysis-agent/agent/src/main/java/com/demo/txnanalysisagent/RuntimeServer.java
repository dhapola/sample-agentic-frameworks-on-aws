package com.demo.txnanalysisagent;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ObjectNode;
import jakarta.servlet.http.HttpServlet;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.eclipse.jetty.server.Server;
import org.eclipse.jetty.servlet.ServletContextHandler;
import org.eclipse.jetty.servlet.ServletHolder;
import org.eclipse.jetty.websocket.api.Session;
import org.eclipse.jetty.websocket.api.WebSocketAdapter;
import org.eclipse.jetty.websocket.server.config.JettyWebSocketServletContainerInitializer;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.IOException;
import java.time.Duration;

/**
 * Jetty-based server for AgentCore Runtime.
 * Handles HTTP (/ping, /invocations) and WebSocket (/ws) on port 8080.
 *
 * WebSocket contract (for AgentCore streaming):
 *   Client sends JSON: {"transaction_id": "txn_001", "log_data": "...", "model_id": "optional"}
 *   Server streams back JSON frames: {"text": "chunk..."} for each token
 *   Final frame: {"done": true, "transaction_id": "...", "model_id": "...", "latency_ms": ..., "input_tokens": ..., "output_tokens": ...}
 *
 * HTTP /invocations contract (non-streaming fallback):
 *   Same request/response as before — full JSON in, full JSON out.
 */
public class RuntimeServer {

    private static final Logger log = LoggerFactory.getLogger(RuntimeServer.class);
    private static final ObjectMapper MAPPER = new ObjectMapper();
    private static final int PORT = 8080;

    private static final AgentConfig CONFIG = AgentConfig.load();
    private static final BedrockInvoker INVOKER = new BedrockInvoker(CONFIG.getRegion());
    private static final TransactionAgent AGENT = new TransactionAgent(CONFIG.getSystemPrompt(), CONFIG.getModelId(), INVOKER);

    public static void main(String[] args) throws Exception {
        log.info("Starting AgentCore RuntimeServer (Jetty) with config: {}", CONFIG);

        Server server = new Server(PORT);

        ServletContextHandler context = new ServletContextHandler(ServletContextHandler.SESSIONS);
        context.setContextPath("/");
        server.setHandler(context);

        // HTTP endpoints
        context.addServlet(new ServletHolder(new PingServlet()), "/ping");
        context.addServlet(new ServletHolder(new InvocationsServlet()), "/invocations");

        // WebSocket endpoint at /ws
        JettyWebSocketServletContainerInitializer.configure(context, (servletContext, wsContainer) -> {
            wsContainer.setMaxTextMessageSize(1024 * 1024); // 1MB for large log payloads
            wsContainer.setIdleTimeout(Duration.ofMinutes(5));
            wsContainer.addMapping("/ws", (req, resp) -> new AgentWebSocket());
        });

        server.start();
        log.info("RuntimeServer listening on 0.0.0.0:{} (/ping, /invocations, /ws)", PORT);
        server.join();
    }

    // --- HTTP: GET /ping ---
    public static class PingServlet extends HttpServlet {
        @Override
        protected void doGet(HttpServletRequest req, HttpServletResponse resp) throws IOException {
            resp.setContentType("application/json");
            resp.setStatus(200);
            resp.getWriter().write("{\"status\":\"Healthy\"}");
        }
    }

    // --- HTTP: POST /invocations (non-streaming) ---
    public static class InvocationsServlet extends HttpServlet {
        @Override
        protected void doPost(HttpServletRequest req, HttpServletResponse resp) throws IOException {
            try {
                JsonNode root = MAPPER.readTree(req.getInputStream());

                String txnId = root.hasNonNull("transaction_id") ? root.get("transaction_id").asText() : null;
                if (txnId == null || txnId.isBlank()) {
                    sendError(resp, 400, "missing 'transaction_id' in request body");
                    return;
                }

                String logData = root.hasNonNull("log_data") ? root.get("log_data").asText() : null;
                if (logData == null || logData.isBlank()) {
                    sendError(resp, 400, "missing 'log_data' in request body");
                    return;
                }

                String modelId = root.hasNonNull("model_id") ? root.get("model_id").asText() : null;

                TransactionAgent.AnalysisResult result = AGENT.analyse(txnId, logData, modelId);

                ObjectNode out = MAPPER.createObjectNode();
                out.put("transaction_id", result.transactionId());
                out.put("response", result.responseText());
                out.put("model_id", result.modelId());
                out.put("latency_ms", result.latencyMs());
                out.put("input_tokens", result.inputTokens());
                out.put("output_tokens", result.outputTokens());

                resp.setContentType("application/json");
                resp.setStatus(200);
                resp.getWriter().write(MAPPER.writeValueAsString(out));

            } catch (Exception e) {
                log.error("Error handling /invocations", e);
                sendError(resp, 500, e.getMessage());
            }
        }

        private void sendError(HttpServletResponse resp, int status, String message) throws IOException {
            resp.setContentType("application/json");
            resp.setStatus(status);
            resp.getWriter().write("{\"error\":\"" + message.replace("\"", "\\\"") + "\"}");
        }
    }

    // --- WebSocket: /ws (streaming) ---
    public static class AgentWebSocket extends WebSocketAdapter {

        @Override
        public void onWebSocketText(String message) {
            Session session = getSession();
            try {
                JsonNode root = MAPPER.readTree(message);

                String txnId = root.hasNonNull("transaction_id") ? root.get("transaction_id").asText() : null;
                if (txnId == null || txnId.isBlank()) {
                    session.getRemote().sendString("{\"error\":\"missing 'transaction_id'\"}");
                    return;
                }

                String logData = root.hasNonNull("log_data") ? root.get("log_data").asText() : null;
                if (logData == null || logData.isBlank()) {
                    session.getRemote().sendString("{\"error\":\"missing 'log_data'\"}");
                    return;
                }

                String modelId = root.hasNonNull("model_id") ? root.get("model_id").asText() : null;

                // Stream tokens as they arrive
                TransactionAgent.AnalysisResult result = AGENT.analyseStreaming(txnId, logData, modelId, chunk -> {
                    try {
                        ObjectNode frame = MAPPER.createObjectNode();
                        frame.put("text", chunk);
                        session.getRemote().sendString(MAPPER.writeValueAsString(frame));
                    } catch (IOException e) {
                        log.warn("Error sending WebSocket chunk", e);
                    }
                });

                // Final metadata frame
                ObjectNode done = MAPPER.createObjectNode();
                done.put("done", true);
                done.put("transaction_id", result.transactionId());
                done.put("model_id", result.modelId());
                done.put("latency_ms", result.latencyMs());
                done.put("input_tokens", result.inputTokens());
                done.put("output_tokens", result.outputTokens());
                session.getRemote().sendString(MAPPER.writeValueAsString(done));
                session.close(1000, "complete");

            } catch (Exception e) {
                log.error("Error in WebSocket handler", e);
                try {
                    session.getRemote().sendString("{\"error\":\"" + e.getMessage().replace("\"", "\\\"") + "\"}");
                } catch (IOException ignored) {}
            }
        }

        @Override
        public void onWebSocketError(Throwable cause) {
            log.error("WebSocket error", cause);
        }
    }
}
