# Deployment Scripts

Bash scripts to deploy, manage, and tear down the Redshift MCP server on Amazon Bedrock AgentCore Runtime.

## Prerequisites

| Tool | Purpose |
|------|---------|
| `aws` (v2.x) | AWS CLI, authenticated as a principal with permissions to create IAM roles, ECR repos, and AgentCore runtimes |
| `docker` (with `buildx`) | Build the linux/arm64 container image |
| `jq` | JSON parsing in scripts |
| `uvx` | Required only by `invoke_test.sh` to run `mcp-proxy-for-aws` |

## Files

| Script | Purpose |
|--------|---------|
| `config.sh` | Shared variables sourced by all other scripts. Edit here to change defaults. |
| `deploy.sh` | Full deployment — IAM role, ECR repo, image build & push, AgentCore runtime |
| `destroy.sh` | Remove all created resources |
| `get_client_config.sh` | Print the analyst MCP client config snippet (with the live runtime ARN) |
| `tail_logs.sh` | Stream CloudWatch logs from the running runtime |
| `invoke_test.sh` | Smoke-test the deployed runtime via `mcp-proxy-for-aws` |

## Quick Start

From the project root:

```bash
# Deploy everything
./scripts/deploy.sh

# Get the MCP client config for analysts
./scripts/get_client_config.sh

# Watch logs while testing
./scripts/tail_logs.sh

# Smoke-test the runtime
./scripts/invoke_test.sh

# Tear down when finished
./scripts/destroy.sh
```

## Configuration

All defaults live in `config.sh`. Override any value via environment variable:

```bash
AWS_REGION=us-west-2 ./scripts/deploy.sh
IMAGE_TAG=v1.2 ./scripts/deploy.sh
AGENT_NAME=redshift_mcp_dev ./scripts/deploy.sh
```

| Variable | Default | Description |
|----------|---------|-------------|
| `AWS_REGION` | `ap-south-1` | AWS region for all resources |
| `AGENT_NAME` | `redshift_mcp_server` | AgentCore runtime name |
| `IAM_ROLE_NAME` | `redshift-mcp-execution-role` | Execution IAM role |
| `IAM_POLICY_NAME` | `redshift-mcp-policy` | Inline policy name |
| `ECR_REPO_NAME` | `redshift-mcp-server` | ECR repository name |
| `REDSHIFT_CLUSTER_ID` | `sample-redshift-cluster-mcp` | Redshift cluster identifier |
| `REDSHIFT_DATABASE` | `dev` | Redshift database name |
| `IMAGE_TAG` | `latest` | Docker image tag |

## Idempotency

All scripts are idempotent:

- `deploy.sh` — creates resources on first run; updates on subsequent runs (new image version, refreshed IAM policy, runtime version bump)
- `destroy.sh` — deletes only what exists; missing resources are warned about, not errored

## Updating the Server

After changing `mcp_server.py`:

```bash
./scripts/deploy.sh        # rebuilds image, pushes new version, updates runtime
```

The DEFAULT endpoint automatically points to the new runtime version.
