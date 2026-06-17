---
title: Coding Conventions
inclusion: always
---

# Coding Conventions

## Java Style

- Java 17 language features are available (records, sealed classes, pattern matching, text blocks)
- Package structure: `com.demo.txnanalysisagent` (flat, no sub-packages)
- Use SLF4J for all logging — never `System.out.println` in production code
- `System.out.print` is acceptable in `Application.java` for streaming user-facing output during batch evaluation
- No DI framework — classes are wired manually

## Bedrock SDK Patterns

- `BedrockInvoker` wraps both sync (`converse`) and streaming (`converseStream`) API calls
- Single-turn invocations only: system prompt + user message, no chat memory
- `TransactionAgent` is stateless — receives log content as a String, knows nothing about file I/O
- Results are returned as Java records (`InvocationResult`, `AnalysisResult`)
- File I/O (reading logs, writing CSV) is handled by the outer layer (`Application`, `agentcore_client.py`)
- `RuntimeServer` does no file I/O — log content arrives in the HTTP/WebSocket request

## Server Architecture

- `RuntimeServer` uses Jetty 11 embedded — HTTP + WebSocket on the same port (8080)
- HTTP servlets for `/ping` and `/invocations` (non-streaming)
- Jetty WebSocket adapter for `/ws` (streaming — sends JSON frames per token chunk)
- WebSocket frames: `{"text": "chunk"}` for data, `{"done": true, ...metadata}` at end

## Error Handling

- `RuntimeServer` HTTP catches all exceptions and returns JSON error responses (400/500)
- `RuntimeServer` WebSocket sends `{"error": "message"}` frame on failure
- `CsvWriter` wraps IO failures in `RuntimeException`

## Configuration

- New config values: add to `application.properties` with a corresponding env var override in `AgentConfig.java`
- Follow the existing pattern: `resolve("ENV_VAR_NAME", "property.key", props, "default-value")`
- System prompt is loaded from classpath (`src/main/resources/system_prompt.md`), not from workdir
- `agent.workdir` is used by `Application.java` to locate log files locally; not used by `RuntimeServer`

## Dependencies

- Managed in `pom.xml` with explicit versions (no BOM)
- The `maven-shade-plugin` produces a fat jar — ensure new dependencies don't conflict with merged `META-INF/services`
