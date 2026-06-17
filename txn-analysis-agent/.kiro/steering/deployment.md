---
title: Deployment to AgentCore
inclusion: always
---

# Deployment to AgentCore

## Architecture

The agent runs as a Docker container in Amazon Bedrock AgentCore Runtime:
- Container must be `linux/arm64` (AWS Graviton)
- Jetty embedded server on port 8080
- HTTP endpoints: `GET /ping` (health check), `POST /invocations` (non-streaming)
- WebSocket endpoint: `/ws` (streaming — AgentCore connects here for real-time responses)
- **No file I/O** — the agent receives log content in the request and returns analysis in the response

## Invocation Flow (WebSocket streaming)

```
agentcore_client.py  →  AgentCore WebSocket (/ws)  →  RuntimeServer  →  TransactionAgent  →  Bedrock
     ↑                                                                                          |
     └─── reads logs from workdir, streams response, writes CSV ←── streaming chunks ──────────┘
```

## WebSocket Protocol

Client sends JSON text frame:
```json
{"transaction_id": "txn_001", "log_data": "...full log content...", "model_id": "optional"}
```

Server streams back text frames:
```json
{"text": "chunk of response..."}
{"text": "more text..."}
...
{"done": true, "transaction_id": "...", "model_id": "...", "latency_ms": ..., "input_tokens": ..., "output_tokens": ...}
```

## Deployment Flow

The `deploy-in-agentcore/deploy.py` script handles the full pipeline:
1. Creates ECR repository (if needed)
2. Builds ARM64 Docker image (from `agent/`) and pushes to ECR
3. Creates/updates IAM execution role with Bedrock invoke + ECR pull + logs permissions
4. Creates or updates AgentCore Runtime (HTTP protocol, PUBLIC network mode)
5. Saves deployment info to `deploy-in-agentcore/deployment_info.json`

## Environment Overrides for deploy.py

| Variable | Default | Purpose |
|----------|---------|---------|
| `AWS_REGION` | `ap-south-1` | Deployment region |
| `AGENT_RUNTIME_NAME` | `txn_analysis_agent` | AgentCore runtime name |
| `ECR_REPO_NAME` | `txn_analysis_agent` | ECR repository name |
| `IMAGE_TAG` | `latest` | Container image tag |
| `AGENTCORE_EXECUTION_ROLE_ARN` | (auto-created) | Use existing IAM role |
| `BEDROCK_MODEL_ID` | (from properties) | Override model in container |
| `BEDROCK_REGION` | `AWS_REGION` | Region where agent calls Bedrock |

## HTTP Invocation Contract (non-streaming fallback)

Request (`POST /invocations`):
```json
{"transaction_id": "txn_001", "log_data": "...full log content...", "model_id": "optional-override"}
```

Response:
```json
{"transaction_id": "...", "response": "...", "model_id": "...", "latency_ms": ..., "input_tokens": ..., "output_tokens": ...}
```

## Running the Client

```bash
cd agentcore-client/python
pip install -r requirements.txt
python agentcore_client.py
```

Environment overrides:
- `AGENT_RUNTIME_ARN` — override the ARN (default: from `deploy-in-agentcore/deployment_info.json`)
- `AWS_REGION` — override region
- `WORKDIR` — path to workdir with evaluation-dataset/ (default: `../../workdir`)

## IAM Role

The auto-created role (`BedrockAgentCoreExecutionRole-java-bedrock-agent`) grants:
- `bedrock:InvokeModel` / `bedrock:InvokeModelWithResponseStream`
- ECR pull permissions
- CloudWatch Logs + X-Ray telemetry
