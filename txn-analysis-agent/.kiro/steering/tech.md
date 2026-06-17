---
title: Tech Stack
inclusion: always
---

# Tech Stack

## Language & Runtime

- Java 17 (records, text blocks, pattern matching available)
- No application framework (no Spring, Quarkus, etc.) — Jetty embedded for HTTP + WebSocket

## Build System

- Maven 3.8+ with `maven-shade-plugin` producing a fat jar
- `exec-maven-plugin` for local execution
- Maven project root is `agent/`

## Dependencies

| Library | Version | Purpose |
|---------|---------|---------|
| AWS SDK v2 (`bedrockruntime`) | 2.46.11 | Bedrock Converse API |
| Jetty (server, servlet, websocket) | 11.0.24 | HTTP + WebSocket server on port 8080 |
| Jackson (`jackson-databind`) | 2.18.2 | JSON serialization |
| SLF4J + Logback | 2.0.16 / 1.5.12 | Logging |

## LLM Integration

- Direct AWS SDK Bedrock Converse API
- Single-turn invocations: system prompt + user message, no chat memory
- Model is configurable via `application.properties` or env vars
- System prompt is baked into the jar (`agent/src/main/resources/system_prompt.md`)
- `TransactionAgent` is stateless — receives log content as input, no file I/O
- `RuntimeServer` does no file I/O — log content arrives in the request body (HTTP or WebSocket)

## Deployment

- Docker multi-stage build targeting `linux/arm64` (Graviton)
- Amazon Bedrock AgentCore Runtime (HTTP + WebSocket protocol, port 8080)
- Python 3 + boto3 deploy scripts in `deploy-in-agentcore/`
- Python 3 + bedrock-agentcore SDK batch client in `agentcore-client/python/`

## Common Commands

```bash
cd agent

# Compile
mvn clean compile

# Package fat jar (for Docker / deployment)
mvn clean package -DskipTests

# Run locally (batch evaluation, direct invocation)
mvn exec:java
# or
./run.sh --build

# Docker build (ARM64)
docker buildx build --platform linux/arm64 -t bedrock-agent .

# Deploy to AgentCore
cd ../deploy-in-agentcore && python deploy.py

# Batch evaluate via deployed agent (WebSocket streaming)
cd ../agentcore-client/python && python agentcore_client.py
```

## Configuration

Loaded from `agent/src/main/resources/application.properties`, overridable by environment variables:

| Env Var | Property Key | Default | Used by |
|---------|-------------|---------|---------|
| `BEDROCK_MODEL_ID` | `bedrock.model.id` | `global.anthropic.claude-haiku-4-5-20251001-v1:0` | Both |
| `BEDROCK_REGION` | `bedrock.region` | `ap-south-1` | Both |
| `AGENT_WORKDIR` | `agent.workdir` | (absolute path) | Application.java only |

After editing properties, always rebuild before running (`mvn clean compile`).
