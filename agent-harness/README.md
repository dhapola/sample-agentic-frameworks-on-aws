# Agent Harness

Reference implementations for deploying custom agents to [Amazon Bedrock AgentCore Runtime](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime.html) using the HTTP contract directly — no `bedrock-agentcore` SDK required.

Each subfolder is a self-contained example with its own README, Dockerfile, and deployment instructions.

## Examples

| Example | Description | Framework |
|---------|-------------|-----------|
| [pi-mono](./pi-mono/) | Deploy the `pi` coding agent to AgentCore via ECR with S3 session snapshots | FastAPI + pi RPC |
