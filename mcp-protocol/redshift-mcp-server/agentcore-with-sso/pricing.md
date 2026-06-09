# AgentCore Runtime — Cost Estimate

**Service:** Redshift MCP Server on Amazon Bedrock AgentCore Runtime  
**Region:** ap-south-1 (Mumbai)  
**Pricing source:** [AWS AgentCore Pricing](https://aws.amazon.com/bedrock/agentcore/pricing/)  
**Date:** June 2026

---

## Pricing Rates

| Resource | Rate |
|----------|------|
| Runtime CPU | $0.0895 per vCPU-hour |
| Runtime Memory | $0.00945 per GB-hour |
| Observability — Span ingestion | $0.35 per GB |
| Observability — Event log ingestion (CloudWatch) | $0.50 per GB |

> **AgentCore Observability** charges are billed as standard Amazon CloudWatch rates for
> spans, logs, and metrics. Span ingestion is $0.35/GB; event logs (tool input/output
> written to CloudWatch standard logs) are $0.50/GB.

---

## Key Pricing Principle

AgentCore Runtime uses **active consumption-based pricing** — you only pay for CPU
during actual processing. I/O wait time (waiting for Redshift Data API responses, network
calls) is **free for CPU**. Memory is billed for peak usage each second throughout the
session lifetime.

This MCP server is almost entirely I/O-bound: each tool call submits SQL to the Redshift
Data API, then polls for results. The overwhelming majority of wall-clock time is I/O
wait, meaning CPU charges are minimal.

---

## Assumptions

These estimates are based on the deployed server configuration in `agentcore/agentcore.json`
and the tool implementations in `mcp_server.py`.

### Session & workload

| Parameter | Value | Source |
|-----------|-------|--------|
| Idle session timeout | 900 seconds (15 min) | `agentcore.json` lifecycleConfiguration |
| Max session lifetime | 28800 seconds (8 hours) | `agentcore.json` lifecycleConfiguration |
| Session model | 1 microVM session per user per day; tool calls within the 15-min window reuse the warm session | |
| **Tool calls per user query** | **5** | e.g. list_schemas → list_tables → describe_table → execute_query → execute_query |
| Session boot cost | 1× per day per user | microVM boot + Python startup + FastMCP init |

### Per tool call

| Parameter | Value | Notes |
|-----------|-------|-------|
| Active CPU per tool call | ~3 seconds | JSON parsing, SQL validation, Data API submission, polling loop, result serialization |
| I/O wait per tool call | ~10 seconds | Redshift Data API: submit + poll (0.5s intervals) + paginated fetch |
| Total wall-clock per tool call | ~13 seconds | ~77% I/O wait → CPU savings are significant |
| Session boot active CPU | ~5 seconds | microVM boot + Python startup + FastMCP init |
| CPU allocation | 0.25 vCPU | Lightweight single-threaded Python HTTP handler |
| Memory — steady state | 256 MB (0.25 GB) | FastMCP + boto3 + request context |
| Memory — peak (large result) | 512 MB (0.5 GB) | Up to 500 rows buffered in GetStatementResult pages |
| Memory billed | 0.5 GB | AgentCore bills peak memory per second |

### Per tool call — Observability

| Parameter | Value | Notes |
|-----------|-------|-------|
| Spans per tool call | ~5 | Tool invocation span + Data API call spans + polling spans |
| Span size | ~1 KB each | Standard OpenTelemetry span payload |
| Span data per tool call | ~5 KB | |
| Event logs per tool call | ~2 KB | Tool input (SQL) + tool output (row count, columns) logged to CloudWatch |
| Total observability per tool call | ~7 KB | Spans + event logs combined |

---

## Cost Per Tool Call

### Runtime

| Component | Calculation | Cost |
|-----------|-------------|------|
| CPU (active only, I/O wait is free) | 3s × 0.25 vCPU × ($0.0895 / 3600) | $0.0000186 |
| Memory (full wall-clock at peak) | 13s × 0.5 GB × ($0.00945 / 3600) | $0.0000171 |
| **Runtime total per tool call** | | **$0.0000357** |

### Session boot (once per session per user per day)

| Component | Calculation | Cost |
|-----------|-------------|------|
| CPU (boot) | 5s × 0.25 vCPU × ($0.0895 / 3600) | $0.0000310 |
| Memory (boot) | 5s × 0.25 GB × ($0.00945 / 3600) | $0.0000033 |
| **Boot total per session** | | **$0.0000343** |

### Observability

| Component | Calculation | Cost |
|-----------|-------------|------|
| Span ingestion | 5 KB × ($0.35 / 1,048,576 KB) | $0.0000017 |
| Event log ingestion | 2 KB × ($0.50 / 1,048,576 KB) | $0.0000010 |
| **Observability total per tool call** | | **$0.0000027** |

---

## Cost Per User Query (5 tool calls)

| Component | Calculation | Cost per query |
|-----------|-------------|----------------|
| Runtime | 5 × $0.0000357 | $0.0001785 |
| Observability | 5 × $0.0000027 | $0.0000135 |
| **Total per query (excl. boot)** | | **$0.0001920** |

Session boot ($0.0000343) is incurred once per day regardless of how many queries the user runs, so it is tracked separately below.

---

## Monthly Cost Estimates — Single User (30 days)

> 1 session per day. All queries happen within the 15-minute idle timeout window,
> so the microVM boot cost is incurred **once per day**, not once per query.
> Each user query = 5 tool calls.

### 10 queries / day → 50 tool calls / day

| Component | Calculation | Monthly Cost |
|-----------|-------------|-------------|
| Session boot (30 sessions) | 30 × $0.0000343 | $0.001 |
| Runtime (300 queries × 5 tool calls = 1,500 tool calls) | 1,500 × $0.0000357 | $0.054 |
| Observability (1,500 tool calls) | 1,500 × $0.0000027 | $0.004 |
| **Total** | | **~$0.059 / month** |

### 20 queries / day → 100 tool calls / day

| Component | Calculation | Monthly Cost |
|-----------|-------------|-------------|
| Session boot (30 sessions) | 30 × $0.0000343 | $0.001 |
| Runtime (600 queries × 5 tool calls = 3,000 tool calls) | 3,000 × $0.0000357 | $0.107 |
| Observability (3,000 tool calls) | 3,000 × $0.0000027 | $0.008 |
| **Total** | | **~$0.116 / month** |

### 50 queries / day → 250 tool calls / day

| Component | Calculation | Monthly Cost |
|-----------|-------------|-------------|
| Session boot (30 sessions) | 30 × $0.0000343 | $0.001 |
| Runtime (1,500 queries × 5 tool calls = 7,500 tool calls) | 7,500 × $0.0000357 | $0.268 |
| Observability (7,500 tool calls) | 7,500 × $0.0000027 | $0.020 |
| **Total** | | **~$0.289 / month** |

### 100 queries / day → 500 tool calls / day

| Component | Calculation | Monthly Cost |
|-----------|-------------|-------------|
| Session boot (30 sessions) | 30 × $0.0000343 | $0.001 |
| Runtime (3,000 queries × 5 tool calls = 15,000 tool calls) | 15,000 × $0.0000357 | $0.536 |
| Observability (15,000 tool calls) | 15,000 × $0.0000027 | $0.041 |
| **Total** | | **~$0.578 / month** |

---

## Summary Table — Single User

| Queries/day | Tool calls/day | Tool calls/month | Runtime/month | Observability/month | **Total/month** |
|:-----------:|:--------------:|:----------------:|:-------------:|:-------------------:|:---------------:|
| 10 | 50 | 1,500 | $0.055 | $0.004 | **$0.059** |
| 20 | 100 | 3,000 | $0.108 | $0.008 | **$0.116** |
| 50 | 250 | 7,500 | $0.269 | $0.020 | **$0.289** |
| 100 | 500 | 15,000 | $0.537 | $0.041 | **$0.578** |

---

## Multi-User Scaling

Costs scale linearly per user (each analyst gets their own session).

| Queries/user/day | 5 users | 10 users | 25 users | 50 users |
|:----------------:|:-------:|:--------:|:--------:|:--------:|
| 10 | $0.30 | $0.59 | $1.48 | $2.95 |
| 20 | $0.58 | $1.16 | $2.90 | $5.80 |
| 50 | $1.45 | $2.89 | $7.23 | $14.45 |
| 100 | $2.89 | $5.78 | $14.45 | $28.90 |

---

## What Is NOT Included

These costs cover AgentCore Runtime and Observability only, per the scope of this estimate.
The following charges apply separately but are not calculated here:

| Cost Item | Notes |
|-----------|-------|
| Redshift Data API | No per-query charge — free API |
| Redshift cluster | Existing infrastructure cost, separate |
| ECR image storage | ~$0.01/month for the container image (~few hundred MB) |
| CloudWatch Log Storage | $0.03/GB/month for 30-day retention — negligible at this scale |
| CloudWatch metrics | Minimal — standard namespace metrics only |
| Data transfer | Negligible for query result payloads at this scale |

---

## Why Costs Are So Low

This MCP server is a textbook I/O-bound workload — exactly the profile that benefits most
from AgentCore's active-consumption model:

1. **~77% I/O wait per tool call** — The server spends most time waiting for Redshift
   Data API. Zero CPU charges during that time under AgentCore's model.
2. **Lightweight process** — Single-threaded Python with no GPU, minimal CPU when active.
3. **Session reuse** — The 15-minute idle timeout means all 5 tool calls per query, and
   all queries within a session, share the single microVM boot cost.
4. **No idle charges** — When no analyst is querying, you pay nothing. There is no
   "always-on" reserved capacity.
5. **Minimal observability footprint** — Each tool call generates only a handful of small
   spans and a short log entry for tool input/output.

For comparison, a traditional EC2-based deployment (e.g., t3.small at ~$0.023/hour)
running 24×7 would cost ~$16.50/month regardless of whether anyone uses it — over **280×
more expensive** at the 10 queries/day tier.
