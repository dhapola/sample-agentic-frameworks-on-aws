---
title: Product Overview
inclusion: always
---

# Product Overview

This is a **payment transaction log analysis agent** that uses Amazon Bedrock foundation models to analyse transaction log files and produce structured insights.

## What It Does

- Receives payment transaction log content and sends it to a Bedrock model with a domain-specific system prompt
- Extracts insights: transaction flow, outcome assessment, anomaly detection, timing analysis
- Streams responses in real-time via WebSocket when deployed in AgentCore
- In batch mode (local or remote), records results (response text, latency, token usage, cost) to a CSV file for evaluation

## Use Cases

1. **Model evaluation (local)** — `Application.java` batch-runs the same transaction logs against multiple Bedrock models in-process and compares quality, latency, and cost.
2. **Model evaluation (remote)** — `agentcore_client.py` does the same but invokes the deployed agent via AgentCore WebSocket with real-time streaming output.
3. **Deployed agent** — `RuntimeServer` serves single-transaction analysis requests via HTTP or WebSocket, receiving log content in the request body (no file I/O on the server).

## Key Domain Concepts

- Transaction logs live in `workdir/evaluation-dataset/` as `.log` files named by transaction ID (e.g. `txn_001.log`)
- The system prompt is baked into the jar (`agent/src/main/resources/system_prompt.md`)
- Evaluation results are written to `workdir/evaluation_results.csv`
- The core agent (`TransactionAgent`) is stateless and independent of file paths — callers are responsible for reading logs and passing content
