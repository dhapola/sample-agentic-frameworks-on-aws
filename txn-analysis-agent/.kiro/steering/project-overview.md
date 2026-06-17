---
title: Project Overview
inclusion: always
---

# Project Overview

This is a Java 17 AI agent using the AWS SDK Bedrock Converse API directly (no framework), deployable to Amazon Bedrock AgentCore Runtime with WebSocket streaming support.

## Tech Stack

- **Language:** Java 17
- **Build tool:** Maven 3.8+
- **LLM integration:** AWS SDK v2 Bedrock Converse API (direct, no LangChain4j)
- **LLM provider:** Amazon Bedrock (Claude, Nova, Llama, DeepSeek, etc.)
- **HTTP + WebSocket server:** Jetty 11 embedded (for AgentCore runtime)
- **Logging:** SLF4J + Logback
- **JSON:** Jackson 2.18
- **Container:** Docker (ARM64 / Graviton) for AgentCore deployment
- **Client:** Python 3 + bedrock-agentcore SDK for WebSocket streaming evaluation

## Project Structure

```
txn-analysis-agent/
├── agent/                 # Java Maven project (the deployed agent)
├── agentcore-client/      # Python batch evaluation client (WebSocket streaming)
├── workdir/               # Runtime data (log files, evaluation dataset)
└── deploy-in-agentcore/   # Python deployment scripts
```

Source files (in `agent/src/main/java/com/demo/txnanalysisagent/`):

| File | Role |
|------|------|
| `Application.java` | Local batch evaluation entry point (`mvn exec:java`) — reads logs, invokes agent directly |
| `AgentConfig.java` | Configuration (properties + env var overrides, classpath system prompt) |
| `BedrockInvoker.java` | AWS SDK Bedrock Converse API wrapper (sync + streaming) |
| `TransactionAgent.java` | Core agent: stateless, receives log content as input |
| `CsvWriter.java` | Appends evaluation results to CSV |
| `RuntimeServer.java` | Jetty server: HTTP (/ping, /invocations) + WebSocket (/ws) on port 8080 |

## Three Ways to Run

1. **Local direct:** `Application.java` — reads logs from workdir, invokes `TransactionAgent` in-process, writes CSV
2. **Deployed agent:** `RuntimeServer.java` — Jetty on port 8080, receives `{transaction_id, log_data, model_id}` via HTTP or WebSocket, streams analysis
3. **Remote client:** `agentcore-client/python/agentcore_client.py` — connects via AgentCore WebSocket, streams response to console, writes CSV

## Configuration

Configuration is loaded from `agent/src/main/resources/application.properties` with environment variable overrides taking precedence:

| Env Var | Property Key | Default | Used by |
|---------|-------------|---------|---------|
| `BEDROCK_MODEL_ID` | `bedrock.model.id` | `global.anthropic.claude-haiku-4-5-20251001-v1:0` | Both |
| `BEDROCK_REGION` | `bedrock.region` | `ap-south-1` | Both |
| `AGENT_WORKDIR` | `agent.workdir` | (absolute path to workdir) | Application.java only |

System prompt is loaded from classpath (`system_prompt.md` in resources), not from workdir.
