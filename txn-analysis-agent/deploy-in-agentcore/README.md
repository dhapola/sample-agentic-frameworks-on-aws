# Deploying to Amazon Bedrock AgentCore Runtime

This folder deploys the Java transaction analysis agent into
[Amazon Bedrock AgentCore Runtime][agentcore]. AgentCore hosts any ARM64
container that implements its HTTP/WebSocket service contract.

## How it works

```
agentcore_client.py ──WebSocket──▶ AgentCore Runtime ──▶ container (ARM64)
                                                             │
                                             RuntimeServer (Jetty, port 8080)
                                               GET  /ping         → health
                                               POST /invocations  → non-streaming
                                               WS   /ws           → streaming
                                                             │
                                                     TransactionAgent
                                                             │
                                                       Amazon Bedrock
```

- **`agent/RuntimeServer.java`** — Jetty 11 embedded server implementing the
  AgentCore [HTTP protocol contract][contract]:
  - `GET /ping` → `200 {"status":"Healthy"}`
  - `POST /invocations` with `{"transaction_id", "log_data", "model_id"}` → full JSON response
  - `WS /ws` — streaming: sends `{"text": "chunk"}` frames, final `{"done": true, ...metadata}`
  - Listens on `0.0.0.0:8080`.
  - The agent is stateless — no session memory, no file I/O on the server.

- **`agent/Dockerfile`** — multi-stage ARM64 build, produces shaded fat jar
  (`Main-Class=RuntimeServer`) and runs `java -jar app.jar`.

- **`deploy.py`** — builds + pushes image to ECR, creates/updates AgentCore runtime.

- **`agentcore-client/python/agentcore_client.py`** — batch evaluation client
  that connects via WebSocket, streams responses, writes CSV.

## Prerequisites

- AWS credentials configured (same chain the AWS CLI uses).
- Docker with `buildx` (for the ARM64 image build).
- Python 3.10+ and the deps in `requirements.txt`:
  ```bash
  pip install -r requirements.txt
  ```
- Bedrock model access enabled in your target region.

## Deploy

```bash
cd deploy-in-agentcore
python deploy.py
```

The script:
1. Creates the ECR repository (if missing).
2. Builds the **linux/arm64** image (from `agent/Dockerfile`) and pushes to ECR.
3. Creates an IAM execution role AgentCore can assume (or reuses one via
   `AGENTCORE_EXECUTION_ROLE_ARN`).
4. Calls `CreateAgentRuntime` (or `UpdateAgentRuntime` if the named runtime
   already exists) with `HTTP` protocol + `PUBLIC` network mode.
5. Writes the runtime ARN to `deployment_info.json`.

### Configuration (environment overrides)

| Variable | Default | Purpose |
|---|---|---|
| `AWS_REGION` | `ap-south-1` | Region to deploy the runtime in |
| `AGENT_RUNTIME_NAME` | `txn_analysis_agent` | AgentCore runtime name |
| `ECR_REPO_NAME` | `txn_analysis_agent` | ECR repository name |
| `IMAGE_TAG` | `latest` | Container image tag |
| `AGENTCORE_EXECUTION_ROLE_ARN` | *(auto-created)* | Use an existing execution role |
| `BEDROCK_MODEL_ID` | *(jar default)* | Model id forwarded to the container |
| `BEDROCK_REGION` | = `AWS_REGION` | Region the agent calls Bedrock in |

`BEDROCK_MODEL_ID` / `BEDROCK_REGION` are passed to the container as environment
variables; the Java `AgentConfig` reads them (env vars take precedence over the
bundled `application.properties`).

> **Credentials in the cloud:** inside AgentCore Runtime the agent gets
> AWS credentials automatically from its execution role — no credential
> export needed. The credential-export workaround in the project README
> only applies to running locally.

## Invoke (batch evaluation)

```bash
cd agentcore-client/python
pip install -r requirements.txt
python agentcore_client.py
```

This connects via WebSocket, streams all model × transaction combinations to
console, and writes results to `workdir/evaluation_results.csv`.

Override the ARN directly:
```bash
AGENT_RUNTIME_ARN=arn:aws:bedrock-agentcore:ap-south-1:123456789012:runtime/... \
python agentcore_client.py
```

## Test the container locally (optional)

```bash
cd agent
mvn clean package -DskipTests
java -jar target/txn-analysis-agent-1.0-SNAPSHOT.jar &   # starts on :8080

curl localhost:8080/ping
curl -X POST localhost:8080/invocations \
  -H 'Content-Type: application/json' \
  -d '{"transaction_id":"txn_001","log_data":"...log content..."}'
```

## Clean up

```bash
aws bedrock-agentcore-control delete-agent-runtime \
  --agent-runtime-id <id> --region <region>
```

[agentcore]: https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/what-is-bedrock-agentcore.html
[contract]: https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-service-contract.html
