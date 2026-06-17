---
title: Project Structure
inclusion: always
---

# Project Structure

```
txn-analysis-agent/
├── agent/                         # Java application (Maven project root)
│   ├── pom.xml                    # Maven build config (shade plugin produces fat jar)
│   ├── Dockerfile                 # Multi-stage ARM64 build for AgentCore
│   ├── run.sh                     # Convenience script for local runs
│   ├── src/main/java/com/demo/txnanalysisagent/
│   │   ├── Application.java      # Local batch evaluation entry point (mvn exec:java)
│   │   ├── AgentConfig.java      # Config loader (properties + env var overrides)
│   │   ├── BedrockInvoker.java   # AWS SDK Bedrock Converse API wrapper
│   │   ├── TransactionAgent.java # Core agent: stateless, takes log content as input
│   │   ├── CsvWriter.java        # Appends evaluation results to CSV
│   │   └── RuntimeServer.java    # Jetty server: HTTP + WebSocket on port 8080
│   └── src/main/resources/
│       ├── application.properties # Default configuration
│       ├── logback.xml            # Logging configuration
│       └── system_prompt.md       # System prompt (baked into jar)
│
├── agentcore-client/              # Client for invoking deployed agent
│   └── python/                    # Python batch evaluation client
│       ├── agentcore_client.py   # Batch evaluation via WebSocket streaming
│       └── requirements.txt      # Python deps (boto3, bedrock-agentcore, websockets)
│
├── workdir/                       # Runtime data (not shipped in jar)
│   ├── evaluation_results.csv     # Output CSV from batch evaluation runs
│   └── evaluation-dataset/        # Transaction log files (txn_001.log, etc.)
│
└── deploy-in-agentcore/           # Deployment tooling (Python + boto3)
    ├── deploy.py                  # Build, push, create/update AgentCore runtime
    ├── deployment_info.json       # Saved ARN/region after deployment
    └── requirements.txt           # Python deps for deploy scripts
```

## Entry Points

| Entry Point | Location | Purpose |
|-------------|----------|---------|
| Local dev (direct) | `agent/Application.java` | Batch evaluates models × transactions locally, writes CSV |
| AgentCore server | `agent/RuntimeServer.java` | Jetty server — HTTP + WebSocket, receives log content, returns streaming analysis |
| AgentCore client (Python) | `agentcore-client/python/agentcore_client.py` | Batch evaluation via deployed agent — WebSocket streaming, writes CSV |

## Key Conventions

- All Java source lives in `com.demo.txnanalysisagent` (flat package, no sub-packages)
- No DI framework — classes are wired manually in `Application.main()` or as static fields in `RuntimeServer`
- `TransactionAgent` is stateless — callers read log files and pass content as Strings
- Transaction log files are plain text, named `{txnId}.log`, stored in `workdir/evaluation-dataset/`
- The fat jar's `Main-Class` is `RuntimeServer` (for container deployment); local runs use `exec-maven-plugin` pointing to `Application`
- Maven commands must be run from `agent/` directory
