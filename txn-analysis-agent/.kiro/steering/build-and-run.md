---
title: Build and Run
inclusion: always
---

# Build and Run

All Maven commands are run from the `agent/` directory.

## Build Commands

```bash
cd agent

# Compile only
mvn clean compile

# Full package (produces shaded fat jar for container deployment)
mvn clean package -DskipTests

# Run locally (batch evaluation, direct Bedrock invocation)
mvn exec:java

# Or use the convenience script
./run.sh          # runs without rebuilding
./run.sh --build  # recompiles then runs
```

## Important: Rebuild After Config Changes

`application.properties` is read from the classpath (`target/classes/`), not directly from `src/`. After editing `agent/src/main/resources/application.properties`, always rebuild:

```bash
cd agent
mvn clean compile && mvn exec:java
# or
./run.sh --build
```

## AWS Credentials

The agent uses the standard AWS credential chain. If Java SDK cannot resolve credentials (e.g. SSO login_session profiles), export them:

```bash
set -a; eval "$(aws configure export-credentials --format env)"; set +a
cd agent && ./run.sh --build
```

## Docker Build (AgentCore Deployment)

AgentCore requires ARM64 containers:

```bash
cd agent
docker build --platform linux/arm64 -t bedrock-agent .
```

Or use the deployment script which handles ECR + AgentCore:

```bash
cd deploy-in-agentcore
pip install -r requirements.txt
python deploy.py
```

## Batch Evaluation via Deployed Agent (WebSocket Streaming)

After deploying, run the client to evaluate all models × transactions with real-time streaming:

```bash
cd agentcore-client/python
pip install -r requirements.txt
python agentcore_client.py
```

This connects via WebSocket to the deployed agent, streams responses to console as they arrive, and writes results to `workdir/evaluation_results.csv`.
