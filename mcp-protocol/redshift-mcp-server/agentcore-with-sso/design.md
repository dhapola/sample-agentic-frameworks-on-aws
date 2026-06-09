# Redshift MCP Server on Bedrock AgentCore — Design Document

## Overview

This document describes the design for an MCP (Model Context Protocol) server that enables internal business analysts to query a Redshift database using natural language through standard AI coding assistants (Kiro, Claude Desktop, Claude Code). The server is hosted on Amazon Bedrock AgentCore Runtime and uses AWS IAM Identity Center for federated, per-user authentication. Redshift is accessed via the Redshift Data API — no direct TCP connection to the cluster is required.

---

## Goals

- Enable business analysts to query Redshift from any standard MCP client
- Authenticate each user individually so Redshift audit logs show per-user activity
- Store no credentials on the client machine (only short-lived IAM session tokens)
- Require zero custom client code — analysts use off-the-shelf tools only
- Host the MCP server fully managed on Bedrock AgentCore Runtime
- Avoid any VPC/network configuration changes to access the private Redshift cluster

## Non-Goals

- Exposing the MCP server outside the organisation
- Supporting write operations (INSERT, UPDATE, DELETE, DDL)
- Building a custom MCP client
- Protecting against spoofing by internal trusted users

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│  User's Laptop                                                      │
│                                                                     │
│  Step 1: aws login                                                  │
│    → Browser opens AWS Identity Center login page                  │
│    → User enters IdC credentials                                    │
│    → Short-lived IAM credentials cached in ~/.aws/sso/cache        │
│      (assumed-role/IdCRole/<idc_username>, valid ~8 hours)         │
│                                                                     │
│  Step 2: MCP client (Kiro / Claude Desktop / Claude Code) starts   │
│    → Runs the configured command (see Client Config section)       │
│    → Shell extracts IdC username from IAM session ARN via          │
│        aws sts get-caller-identity                                  │
│    → Launches mcp-proxy-for-aws with username as custom header     │
│                                                                     │
└────────────────────────┬────────────────────────────────────────────┘
                         │
                         │  MCP over HTTPS (Stateless Streamable HTTP)
                         │  Auth: AWS SigV4 (signed with user's IAM credentials)
                         │  Header: X-Amzn-Bedrock-AgentCore-Runtime-Custom-DbUser: <username>
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────────┐
│  Amazon Bedrock AgentCore Runtime (ap-south-1)                      │
│  Network mode: PUBLIC                                               │
│                                                                     │
│  Inbound auth: AWS_IAM (SigV4)                                      │
│  requestHeaderAllowlist:                                            │
│    - X-Amzn-Bedrock-AgentCore-Runtime-Custom-DbUser                │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  FastMCP Server (Python)                                     │  │
│  │                                                              │  │
│  │  Tools:                                                      │  │
│  │    - execute_query(sql)      Run a SELECT query              │  │
│  │    - list_schemas()          List available schemas          │  │
│  │    - list_tables(schema)     List tables in a schema         │  │
│  │    - describe_table(s, t)    Show columns and types          │  │
│  │                                                              │  │
│  │  Per request:                                                │  │
│  │    1. Read DbUser from custom header                         │  │
│  │    2. Call redshift-data:ExecuteStatement(DbUser=<username>) │  │
│  │    3. Poll redshift-data:DescribeStatement until FINISHED    │  │
│  │    4. Fetch results via redshift-data:GetStatementResult     │  │
│  │    5. Return rows to MCP client                              │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                                                     │
└────────────────────────┬────────────────────────────────────────────┘
                         │
                         │  HTTPS to redshift-data.ap-south-1.amazonaws.com
                         │  AWS manages the internal connection to Redshift
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────────┐
│  Redshift Data API (AWS managed)                                    │
│    - Receives ExecuteStatement with DbUser                          │
│    - Calls redshift:GetClusterCredentials internally                │
│    - Opens connection to Redshift on internal AWS network           │
└────────────────────────┬────────────────────────────────────────────┘
                         │
                         │  Internal AWS network (no internet traversal)
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────────┐
│  Amazon Redshift — private subnet (ap-south-1)                      │
│  Cluster: sample-redshift-cluster-mcp                               │
│                                                                     │
│  - No security group changes required                               │
│  - No VPC configuration changes required                            │
│  - Federated authentication via AWS Identity Center                 │
│  - IdC application: d2-redshift-sso-app                            │
│  - Each query runs as the individual user's Redshift identity       │
│  - Audit logs show per-user activity                                │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Authentication Flow (Step by Step)

| Step | Where | What Happens |
|------|--------|--------------|
| 1 | Laptop | `aws login` opens browser → user authenticates with Identity Center |
| 2 | Laptop | IAM credentials for `assumed-role/IdCRole/<username>` cached locally |
| 3 | Laptop | MCP client starts the configured command |
| 4 | Laptop | Shell runs `aws sts get-caller-identity`, extracts session name (= IdC username) |
| 5 | Laptop | `mcp-proxy-for-aws` signs each MCP request with SigV4 using cached IAM credentials |
| 6 | AgentCore | Runtime validates SigV4 signature — request is authenticated |
| 7 | AgentCore | Custom header `X-Amzn-Bedrock-AgentCore-Runtime-Custom-DbUser` is forwarded to MCP server |
| 8 | AgentCore | MCP server reads `DbUser` from the header |
| 9 | AgentCore | MCP server calls `redshift-data:ExecuteStatement` with `DbUser=<username>` |
| 10 | Data API | AWS calls `redshift:GetClusterCredentials` internally and connects to cluster |
| 11 | Redshift | Query executes as that user; audit log records individual identity |
| 12 | AgentCore | MCP server polls `DescribeStatement` until status is `FINISHED` |
| 13 | AgentCore | MCP server fetches rows via `GetStatementResult` and returns to client |

---

## Why Redshift Data API (not direct JDBC)

Redshift runs in a private subnet with no public endpoint. Connecting directly via JDBC (port 5439) would require deploying AgentCore Runtime in VPC mode — adding ENIs, security group rules, VPC endpoints, and subnet configuration. The Redshift Data API eliminates all of that:

| Concern | Direct JDBC | Redshift Data API |
|---------|------------|------------------|
| AgentCore network mode | VPC (complex) | **PUBLIC (simple)** |
| VPC/subnet config | Required | **Not needed** |
| Security group changes | Required | **Not needed** |
| VPC endpoints | Possibly required | **Not needed** |
| Python Redshift driver | `redshift_connector` | **Not needed** |
| Query execution model | Synchronous | Async (poll loop, transparent to user) |
| Per-user identity | `GetClusterCredentials` | `DbUser` param in `ExecuteStatement` |

Trade-off: The Data API is asynchronous — queries are submitted and polled for completion. This is handled transparently inside the MCP server tools. Analysts see no difference.

---

## Components

### Client Side (User's Laptop — Zero Code)

**Pre-requisites for analysts:**
- AWS CLI v2 installed and configured with the Identity Center SSO profile
- `uv` / `uvx` installed (`curl -LsSf https://astral.sh/uv/install.sh | sh`)
- Standard MCP client (Kiro, Claude Desktop, or Claude Code)

**One-time setup:**
```bash
aws configure sso
# Follow prompts: SSO URL, region, account, role
```

**Daily workflow:**
```bash
aws login
# Opens browser once — credentials valid for ~8 hours
```

### MCP Client Configuration

Add the following to the MCP client config (e.g., `~/.kiro/settings/mcp.json` for Kiro, `~/Library/Application Support/Claude/claude_desktop_config.json` for Claude Desktop):

```json
{
  "mcpServers": {
    "redshift": {
      "command": "sh",
      "args": [
        "-c",
        "DB_USER=$(aws sts get-caller-identity --query Arn --output text | cut -d'/' -f3) && uvx mcp-proxy-for-aws@latest https://bedrock-agentcore.ap-south-1.amazonaws.com/runtimes/<RUNTIME_ARN_ENCODED>/invocations --header \"X-Amzn-Bedrock-AgentCore-Runtime-Custom-DbUser: $DB_USER\""
      ]
    }
  }
}
```

> `<RUNTIME_ARN_ENCODED>` is the AgentCore Runtime ARN with `:` replaced by `%3A` and `/` replaced by `%2F`. This value is fixed after first deployment and distributed to analysts by the admin.

### Server Side (AgentCore Runtime)

| File | Purpose |
|------|---------|
| `mcp_server.py` | FastMCP server with Redshift Data API tool implementations |
| `requirements.txt` | Python dependencies |
| `agentcore/agentcore.json` | AgentCore deployment config (auth, header allowlist, protocol, network) |

**Runtime configuration:**
- Protocol: `MCP`
- Inbound auth: `AWS_IAM`
- Network mode: `PUBLIC`
- Header allowlist: `["X-Amzn-Bedrock-AgentCore-Runtime-Custom-DbUser"]`
- Region: `ap-south-1`

### IAM Execution Role Policy

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "RedshiftDataAPI",
      "Effect": "Allow",
      "Action": [
        "redshift-data:ExecuteStatement",
        "redshift-data:DescribeStatement",
        "redshift-data:GetStatementResult",
        "redshift-data:ListStatements",
        "redshift-data:CancelStatement"
      ],
      "Resource": "*"
    },
    {
      "Sid": "RedshiftCredentials",
      "Effect": "Allow",
      "Action": ["redshift:GetClusterCredentials"],
      "Resource": [
        "arn:aws:redshift:ap-south-1:<ACCOUNT_ID>:dbuser:sample-redshift-cluster-mcp/*",
        "arn:aws:redshift:ap-south-1:<ACCOUNT_ID>:dbname:sample-redshift-cluster-mcp/dev"
      ]
    },
    {
      "Sid": "ECRAccess",
      "Effect": "Allow",
      "Action": [
        "ecr:GetAuthorizationToken",
        "ecr:BatchGetImage",
        "ecr:GetDownloadUrlForLayer",
        "ecr:BatchCheckLayerAvailability"
      ],
      "Resource": "*"
    },
    {
      "Sid": "CloudWatchLogs",
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:DescribeLogGroups",
        "logs:DescribeLogStreams",
        "logs:PutLogEvents"
      ],
      "Resource": "arn:aws:logs:ap-south-1:<ACCOUNT_ID>:log-group:/aws/bedrock-agentcore/runtimes/*"
    },
    {
      "Sid": "XRayTracing",
      "Effect": "Allow",
      "Action": [
        "xray:PutTraceSegments",
        "xray:PutTelemetryRecords"
      ],
      "Resource": "*"
    }
  ]
}
```

**Trust policy** (allows AgentCore service to assume this role):
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "bedrock-agentcore.amazonaws.com"
      },
      "Action": "sts:AssumeRole",
      "Condition": {
        "StringEquals": {
          "aws:SourceAccount": "<ACCOUNT_ID>"
        },
        "ArnLike": {
          "aws:SourceArn": "arn:aws:bedrock-agentcore:ap-south-1:<ACCOUNT_ID>:*"
        }
      }
    }
  ]
}
```

---

## MCP Tools

### `execute_query`

Executes a read-only SQL SELECT query against the Redshift cluster as the authenticated user.

- **Input:** `sql` (string) — the SQL query to execute
- **Output:** Query results as a list of row dictionaries, plus row count and column names
- **Restrictions:** Only SELECT statements permitted; any DDL or DML raises an error before submission
- **Execution:** Async via Data API — submits, polls every 0.5s until complete, fetches paginated results

### `list_schemas`

Lists all user-visible schemas in the connected Redshift database.

- **Input:** None
- **Output:** List of schema names

### `list_tables`

Lists all tables within a specified schema.

- **Input:** `schema` (string) — schema name
- **Output:** List of table names

### `describe_table`

Returns column names and data types for a specified table.

- **Input:** `schema` (string), `table` (string)
- **Output:** List of `{column_name, data_type, is_nullable}` objects

---

## AWS Configuration Reference

| Parameter | Value |
|-----------|-------|
| AWS Region | `ap-south-1` (Mumbai) |
| Identity Center URL | `https://<IDENTITY_CENTER_SUBDOMAIN>.portal.ap-south-1.app.aws/` |
| Identity Center IdC App | `d2-redshift-sso-app` |
| Redshift Cluster | `sample-redshift-cluster-mcp` |
| Redshift Database | `dev` |
| Redshift Subnet | Private (no public endpoint) |
| AgentCore Runtime Protocol | `MCP` |
| AgentCore Inbound Auth | `AWS_IAM` |
| AgentCore Network Mode | `PUBLIC` |
| Redshift Access Method | Redshift Data API (HTTPS) |

---

## Security Considerations

| Concern | Mitigation |
|---------|-----------|
| Credential storage on client | None — only short-lived IAM session tokens in `~/.aws/sso/cache`, auto-expired (~8h) |
| Unauthenticated access to AgentCore | AWS SigV4 required on every request; unsigned requests rejected with 403 |
| Cross-user Redshift access | `DbUser` is derived from the authenticated IAM session name; users cannot access a different Redshift user without a different IAM identity |
| Write access to Redshift | MCP server validates that SQL starts with SELECT before submitting to Data API |
| Short-lived Redshift credentials | Data API handles credential lifecycle; credentials are never exposed to MCP server code |
| Redshift cluster exposure | Cluster remains in private subnet; Data API connects internally — no inbound firewall changes needed |
| Header spoofing | Accepted risk — internal trusted users only; IAM SigV4 still proves the caller's authenticated IAM identity |

---

## Deployment Steps

1. **Create IAM execution role** with the policy and trust policy above; note the role ARN
2. **Write server code** — `mcp_server.py`, `requirements.txt`
3. **Configure AgentCore project** — `agentcore/agentcore.json` with MCP protocol, IAM auth, PUBLIC network, header allowlist
4. **Test locally** — `agentcore deploy --local`, test with `agentcore invoke`
5. **Deploy to AWS** — `agentcore deploy`; note the Runtime ARN from output
6. **URL-encode the ARN** — replace `:` with `%3A` and `/` with `%2F`
7. **Distribute client config** — share the MCP client config snippet (with encoded ARN) to analysts
8. **Analyst setup** — each analyst runs `aws configure sso` once, then `aws login` daily

---

## Sequence Diagram

```
Analyst       MCP Client     mcp-proxy-for-aws   AgentCore Runtime   Redshift Data API   Redshift
   │               │                 │                   │                    │                │
   │  aws login    │                 │                   │                    │                │
   │──────────────>│                 │                   │                    │                │
   │  (browser)    │                 │                   │                    │                │
   │<──────────────│                 │                   │                    │                │
   │  IAM creds    │                 │                   │                    │                │
   │               │                 │                   │                    │                │
   │  ask question │                 │                   │                    │                │
   │──────────────>│                 │                   │                    │                │
   │               │ get-caller-id   │                   │                    │                │
   │               │────────────────>│                   │                    │                │
   │               │ ARN → username  │                   │                    │                │
   │               │<────────────────│                   │                    │                │
   │               │                 │                   │                    │                │
   │               │  initialize MCP │                   │                    │                │
   │               │────────────────>│                   │                    │                │
   │               │                 │ SigV4 + DbUser hdr│                    │                │
   │               │                 │──────────────────>│                    │                │
   │               │                 │  validate SigV4   │                    │                │
   │               │                 │  forward header   │                    │                │
   │               │                 │<──────────────────│                    │                │
   │               │                 │                   │                    │                │
   │               │  execute_query  │                   │                    │                │
   │               │────────────────>│                   │                    │                │
   │               │                 │ SigV4 + DbUser hdr│                    │                │
   │               │                 │──────────────────>│                    │                │
   │               │                 │                   │ ExecuteStatement   │                │
   │               │                 │                   │ (DbUser=username)  │                │
   │               │                 │                   │───────────────────>│                │
   │               │                 │                   │                    │ GetCredentials │
   │               │                 │                   │                    │ + execute SQL  │
   │               │                 │                   │                    │───────────────>│
   │               │                 │                   │                    │<───────────────│
   │               │                 │                   │  StatementId       │                │
   │               │                 │                   │<───────────────────│                │
   │               │                 │                   │ DescribeStatement  │                │
   │               │                 │                   │ (poll until DONE)  │                │
   │               │                 │                   │───────────────────>│                │
   │               │                 │                   │<───────────────────│                │
   │               │                 │                   │ GetStatementResult │                │
   │               │                 │                   │───────────────────>│                │
   │               │                 │                   │  rows              │                │
   │               │                 │                   │<───────────────────│                │
   │               │                 │  results          │                    │                │
   │               │<────────────────│                   │                    │                │
   │  answer       │                 │                   │                    │                │
   │<──────────────│                 │                   │                    │                │
```

---

## Project File Structure

```
redshift-mcp-server/
├── mcp_server.py               # FastMCP server — tool implementations
├── requirements.txt            # Python dependencies
└── agentcore/
    └── agentcore.json          # AgentCore deployment configuration
```

---

## Dependencies

### Python (server)
| Package | Version | Purpose |
|---------|---------|---------|
| `mcp[server]` | `>=1.10.0` | FastMCP framework |
| `boto3` | `>=1.34.0` | Redshift Data API + AWS SDK |
| `bedrock-agentcore` | latest | AgentCore Runtime SDK wrapper |

### User's Laptop
| Tool | Version | Purpose |
|------|---------|---------|
| `aws-cli` | v2.x | `aws login` + `aws sts get-caller-identity` |
| `uv` / `uvx` | latest | Run `mcp-proxy-for-aws` without manual install |
| `mcp-proxy-for-aws` | latest | SigV4 signing proxy (fetched at runtime via `uvx`) |

---

*Document version: 1.1 — Updated to use Redshift Data API; VPC mode removed; design finalised for implementation.*
