# Transaction Analysis Agent

A Java 17 agent that analyses payment transaction log files using Amazon Bedrock foundation models. Supports batch evaluation across multiple models and real-time streaming via WebSocket when deployed in Amazon Bedrock AgentCore Runtime.

## Prerequisites

- Java 17+
- Maven 3.8+
- AWS credentials configured (environment variables, `~/.aws/credentials`, or IAM role)
- Access to Amazon Bedrock models in `ap-south-1` (or your configured region)

## Project Structure

```
txn-analysis-agent/
├── agent/                         # Java Maven project (this directory)
│   ├── pom.xml                    # Maven build (shade plugin → fat jar)
│   ├── Dockerfile                 # Multi-stage ARM64 build for AgentCore
│   ├── run.sh                     # Convenience script for local runs
│   └── src/main/java/com/demo/txnanalysisagent/
│       ├── Application.java       # Local batch evaluation entry point (mvn exec:java)
│       ├── AgentConfig.java       # Config loader (properties + env var overrides)
│       ├── BedrockInvoker.java    # AWS SDK Bedrock Converse API wrapper (sync + streaming)
│       ├── TransactionAgent.java  # Core agent: stateless, takes log content as input
│       ├── CsvWriter.java         # Appends evaluation results to CSV
│       └── RuntimeServer.java     # Jetty server: HTTP + WebSocket on port 8080
│
├── agentcore-client/python/       # Batch evaluation client (WebSocket streaming)
│   ├── agentcore_client.py        # Connects via AgentCore WebSocket, streams response
│   └── requirements.txt           # boto3, bedrock-agentcore, websockets
│
├── deploy-in-agentcore/           # Deployment tooling (Python + boto3)
│   ├── deploy.py                  # Build, push, create/update AgentCore runtime
│   └── deployment_info.json       # Saved ARN/region after deployment
│
└── workdir/                       # Runtime data (not shipped in jar)
    ├── evaluation_results.csv     # Output CSV from batch runs
    └── evaluation-dataset/        # Transaction log files (txn_001.log, etc.)
```

## Configuration

Settings in `src/main/resources/application.properties`, overridable by env vars:

| Environment Variable | Property Key       | Default                                           |
|----------------------|--------------------|---------------------------------------------------|
| `BEDROCK_MODEL_ID`   | `bedrock.model.id` | `global.anthropic.claude-haiku-4-5-20251001-v1:0` |
| `BEDROCK_REGION`     | `bedrock.region`   | `ap-south-1`                                      |
| `AGENT_WORKDIR`      | `agent.workdir`    | `./workdir`                                       |

System prompt is loaded from classpath (`src/main/resources/system_prompt.md`), not from workdir.

## Evaluated Models

Models and their pricing (USD per 1M tokens) are defined in `Application.java`'s `MODEL_PRICING` map. Adding or removing a model there is all that's needed.

| Model ID | Input $/1M | Output $/1M |
|----------|-----------|------------|
| `global.anthropic.claude-haiku-4-5-20251001-v1:0` | 1.00 | 5.00 |
| `apac.anthropic.claude-sonnet-4-20250514-v1:0` | 3.00 | 15.00 |
| `global.anthropic.claude-sonnet-4-6` | 3.00 | 15.00 |
| `global.anthropic.claude-opus-4-8` | 5.00 | 25.00 |
| `apac.amazon.nova-pro-v1:0` | 1.48 | 1.48 |
| `deepseek.v3-v1:0` | 0.68 | 1.98 |
| `deepseek.v3.2` | 0.74 | 2.22 |
| `minimax.minimax-m2.5` | 0.36 | 1.44 |
| `moonshotai.kimi-k2.5` | 0.72 | 3.60 |
| `qwen.qwen3-next-80b-a3b` | 0.18 | 1.41 |
| `zai.glm-5` | 1.20 | 3.84 |

## Build and Run

```bash
cd agent

# Compile
mvn clean compile

# Run batch evaluation (local, direct Bedrock invocation)
mvn exec:java
# or
./run.sh --build

# Package fat jar (for Docker / deployment)
mvn clean package -DskipTests
```

> **Rebuild after editing `application.properties`** — it's read from the classpath (`target/classes/`), not `src/`.

## Deployment to AgentCore

```bash
cd deploy-in-agentcore
pip install -r requirements.txt
python deploy.py
```

The container is built for `linux/arm64` (Graviton), exposes port 8080 with:
- `GET /ping` — health check
- `POST /invocations` — non-streaming analysis
- `WS /ws` — streaming analysis (real-time token-by-token response)

### WebSocket Protocol

Client sends a JSON text frame:
```json
{"transaction_id": "txn_001", "log_data": "...full log content...", "model_id": "optional"}
```

Server streams back:
```json
{"text": "chunk of response..."}
{"text": "more text..."}
{"done": true, "transaction_id": "...", "model_id": "...", "latency_ms": ..., "input_tokens": ..., "output_tokens": ...}
```

### Batch Evaluation via Deployed Agent

```bash
cd agentcore-client/python
pip install -r requirements.txt
python agentcore_client.py
```

Connects via WebSocket to the deployed agent, streams responses to console, writes results to `workdir/evaluation_results.csv`.

## AWS Credentials

Uses the standard AWS credential chain. If the Java SDK can't resolve credentials from SSO/login_session profiles:

```bash
set -a; eval "$(aws configure export-credentials --format env)"; set +a
cd agent && ./run.sh --build
```
