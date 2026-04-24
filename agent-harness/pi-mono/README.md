# Deploy a Custom Agent to Amazon Bedrock AgentCore Runtime via ECR

This guide deploys a coding agent (pi-mono) to AgentCore Runtime using a custom Docker container pushed to ECR — no `bedrock-agentcore` SDK required. The agent implements the AgentCore HTTP contract directly with FastAPI.

## What This Project Does

- Wraps the `pi` coding agent in a FastAPI server that implements AgentCore's HTTP contract (`POST /invocations`, `GET /ping`)
- Manages a long-running pi subprocess via JSON-line RPC (stdin/stdout)
- Snapshots the full session state (conversation history + workspace files) to S3 after every response
- Restores from S3 on cold start so the agent survives container recycling
- One container = one session = one pi process

## Architecture

```
User → InvokeAgentRuntime API → AgentCore Runtime → Container (FastAPI :8080)
                                                        ├── POST /invocations → agent.handle() → PiRpc → Bedrock (Claude)
                                                        ├── GET /ping → Healthy / HealthyBusy
                                                        └── S3 snapshot/restore (async after each response)
```

## Prerequisites

- AWS account with Bedrock model access enabled for `us.anthropic.claude-sonnet-4-6`
- Docker with buildx (for ARM64 cross-compilation)
- AWS CLI v2 configured with credentials that can create IAM roles, ECR repos, and AgentCore runtimes
- Python 3.10+ with boto3 installed locally (for deploy/invoke scripts)

## File Overview

| File | Description | Modify? |
|------|-------------|---------|
| `server.py` | AgentCore HTTP boilerplate — `/invocations` and `/ping` endpoints. Calls `agent.handle()` | **No** — this is the boilerplate |
| `agent.py` | Agent logic — pi RPC, S3 snapshots, `handle(session_id, prompt)` entrypoint | **Yes** — customize this |
| `Dockerfile` | ARM64 container: ubuntu 22.04 + Node.js 20 + pi (npm) + Python + FastAPI/uvicorn | As needed |
| `requirements.txt` | Python dependencies: `fastapi`, `uvicorn[standard]`, `boto3` | As needed |
| `.dockerignore` | Excludes dev artifacts from Docker build context | Rarely |

### How the split works

```
server.py (DON'T TOUCH)          agent.py (CUSTOMIZE THIS)
┌─────────────────────┐          ┌──────────────────────────┐
│ POST /invocations    │──calls──▶│ handle(session_id, prompt)│
│ GET  /ping           │          │   → your agent logic      │
│ HealthyBusy tracking │          │   → returns {"result":..} │
└─────────────────────┘          └──────────────────────────┘
```

The `handle()` function is the only contract between the two files:
- Input: `session_id` (str), `prompt` (str)
- Output: `{"result": "..."}` on success, `{"error": "..."}` on failure
- It runs in a thread pool so it can be blocking (no async needed)

## Step-by-Step Deployment

### 1. Create the S3 Snapshot Bucket

```bash
aws s3 mb s3://pi-mono-agent-snapshots-<ACCOUNT_ID> --region us-east-1
```

### 2. Create the IAM Execution Role

Create a role named `AgentCoreRuntime-pi-mono-ecr` with:

**Trust policy** — allows AgentCore to assume the role:
```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Sid": "AssumeRolePolicy",
    "Effect": "Allow",
    "Principal": { "Service": "bedrock-agentcore.amazonaws.com" },
    "Action": "sts:AssumeRole",
    "Condition": {
      "StringEquals": { "aws:SourceAccount": "<ACCOUNT_ID>" },
      "ArnLike": { "aws:SourceArn": "arn:aws:bedrock-agentcore:us-east-1:<ACCOUNT_ID>:*" }
    }
  }]
}
```

**Permissions policy** — the role needs these actions:

| Permission | Purpose |
|-----------|---------|
| `ecr:BatchGetImage`, `ecr:GetDownloadUrlForLayer` | Pull container image from ECR |
| `ecr:GetAuthorizationToken` | Authenticate to ECR |
| `logs:CreateLogGroup`, `logs:CreateLogStream`, `logs:PutLogEvents`, `logs:DescribeLogStreams`, `logs:DescribeLogGroups` | CloudWatch logging |
| `xray:PutTraceSegments`, `xray:PutTelemetryRecords`, `xray:GetSamplingRules`, `xray:GetSamplingTargets` | X-Ray tracing |
| `cloudwatch:PutMetricData` (condition: namespace=bedrock-agentcore) | CloudWatch metrics |
| `bedrock:InvokeModel`, `bedrock:InvokeModelWithResponseStream` | Call Claude via Bedrock |
| `s3:GetObject`, `s3:PutObject`, `s3:ListBucket` on the snapshot bucket | Session snapshot/restore |
| `bedrock-agentcore:GetWorkloadAccessToken*` | Workload identity tokens |

See the [official IAM docs](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-permissions.html) for the full policy template.

### 3. Create ECR Repository

```bash
aws ecr create-repository --repository-name pi-mono-agent-ecr --region us-east-1
```

### 4. Build ARM64 Image and Push to ECR

```bash
# Authenticate Docker to ECR
aws ecr get-login-password --region us-east-1 | \
  docker login --username AWS --password-stdin <ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com

# Build and push (ARM64 required — AgentCore runs on Graviton)
docker buildx create --use
docker buildx build --platform linux/arm64 \
  -t <ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com/pi-mono-agent-ecr:latest --push .

# Verify
aws ecr describe-images --repository-name pi-mono-agent-ecr --region us-east-1
```

### 5. Deploy to AgentCore Runtime

Use the AWS CLI to create the runtime:

```bash
aws bedrock-agentcore-control create-agent-runtime \
  --agent-runtime-name pi-mono \
  --container-uri <ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com/pi-mono-agent-ecr:latest \
  --role-arn arn:aws:iam::<ACCOUNT_ID>:role/AgentCoreRuntime-pi-mono-ecr \
  --network-mode PUBLIC \
  --environment-variables SNAPSHOT_BUCKET=pi-mono-agent-snapshots-<ACCOUNT_ID> \
  --idle-session-timeout-in-seconds 900 \
  --max-session-lifetime-in-seconds 28800 \
  --region us-east-1
```

Wait for status to become `READY`:
```bash
aws bedrock-agentcore-control get-agent-runtime \
  --agent-runtime-id <RUNTIME_ID> --region us-east-1
```

### 6. Invoke the Agent

```bash
aws bedrock-agentcore invoke-agent-runtime \
  --agent-runtime-arn arn:aws:bedrock-agentcore:us-east-1:<ACCOUNT_ID>:runtime/pi-mono \
  --runtime-session-id $(python3 -c "import uuid; print(str(uuid.uuid4()) + '-extra-chars-for-length')") \
  --payload '{"prompt": "What files are in /workspace?"}' \
  --region us-east-1
```

The `runtimeSessionId` must be 33+ characters. Same session ID = same container (stateful). Different session ID = fresh container.

### 7. Stop a Session (Optional)

```bash
aws bedrock-agentcore stop-runtime-session \
  --agent-runtime-arn <ARN> \
  --runtime-session-id <SESSION_ID> \
  --region us-east-1
```

## How the Agent Works

### HTTP Contract (server.py)

AgentCore requires two endpoints on port 8080:

- `POST /invocations` — receives `{"prompt": "..."}`, extracts session ID from the `X-Amzn-Bedrock-AgentCore-Runtime-Session-Id` header, calls `agent.handle()`, returns the result as JSON.
- `GET /ping` — returns `{"status": "Healthy"}` or `{"status": "HealthyBusy"}` while processing. Returning `HealthyBusy` prevents AgentCore from killing the container during long-running prompts.

### Pi RPC Protocol (agent.py)

The agent starts a `pi --mode rpc` subprocess and communicates via JSON lines on stdin/stdout:
1. Send `{"type": "prompt", "message": "..."}` on stdin
2. Read stdout lines until `{"type": "agent_end"}` appears
3. Send `{"type": "get_last_assistant_text"}` to get the final response
4. UI confirmation requests (tool approvals) are auto-accepted

### S3 Snapshot/Restore (agent.py)

- **Snapshot**: After every `handle()` call, a background thread uploads all files from `/home/agent/.pi/` (conversation history) and `/workspace/` (user files) to S3 under `<session_id>/`.
- **Restore**: On cold start (container recycled), before starting pi, the agent checks S3 for an existing snapshot and downloads it. Pi is then started with `--continue` to resume the conversation.

### Async Design

Pi's RPC is blocking (synchronous stdin/stdout). `server.py` uses `asyncio.to_thread()` to run `agent.handle()` in a thread pool, keeping the FastAPI event loop free for `/ping` health checks during long-running prompts.

## Validation Tests

| # | Test | How to verify |
|---|------|--------------|
| 1 | Tool invocation | Ask pi to create a file — it should use bash/write tools |
| 2 | Filesystem ops | Write, read, list files in /workspace |
| 3 | Session isolation | Use two different session IDs — each gets an independent empty /workspace |
| 4 | S3 snapshot | After an invocation, check `s3://<bucket>/<session_id>/` for uploaded files |
| 5 | Cold-start restore | Stop the session, invoke again with the same session ID — agent should remember conversation and files |

## Key Configuration

| Setting | Value | Notes |
|---------|-------|-------|
| Port | 8080 | Required by AgentCore |
| Architecture | linux/arm64 | AgentCore runs on Graviton only |
| Model | `us.anthropic.claude-sonnet-4-6` | Via Amazon Bedrock |
| Idle timeout | 900s (15 min) | Configurable at deploy time |
| Max lifetime | 28800s (8 hrs) | Hard cap per container |
| Session ID min length | 33 characters | AgentCore requirement |

## Cleanup

```bash
# Delete the agent runtime
aws bedrock-agentcore-control delete-agent-runtime \
  --agent-runtime-id <RUNTIME_ID> --region us-east-1

# Delete ECR repository
aws ecr delete-repository --repository-name pi-mono-agent-ecr --force --region us-east-1

# Delete S3 snapshot bucket (empty it first)
aws s3 rb s3://pi-mono-agent-snapshots-<ACCOUNT_ID> --force

# Delete IAM role (detach policies first)
aws iam delete-role-policy --role-name AgentCoreRuntime-pi-mono-ecr \
  --policy-name AgentCoreExecutionPolicy-pi-mono-ecr
aws iam delete-role --role-name AgentCoreRuntime-pi-mono-ecr
```
