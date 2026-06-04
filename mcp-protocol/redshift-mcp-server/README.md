# Redshift MCP Server

A centrally hosted [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) server that exposes Amazon Redshift to AI applications as MCP tools. End users authenticate with native Redshift SQL credentials supplied via HTTP headers — the server is a thin, stateless proxy that delegates all authorization to Redshift's native RBAC.

## Architecture

```
MCP Client (AI App)
  │  HTTPS (trusted *.cloudfront.net cert)
  ▼
CloudFront distribution          caching disabled, forwards all headers
  │  HTTP 80
  ▼
Public ALB                       SG locked to CloudFront prefix list
  │  HTTP 8080
  ▼
EC2 (private subnet)             FastMCP + uvicorn, systemd managed
  │  TCP 5439
  ▼
Amazon Redshift                  authorization via SQL user GRANTs
```

## MCP Tools

| Tool | Description |
|------|-------------|
| `list_schemas` | Enumerate schemas visible to the calling user |
| `list_tables` | List tables in a given schema |
| `describe_table` | Show columns and types for a table |
| `run_query` | Execute a read-only SQL query (SELECT/WITH/SHOW/EXPLAIN) |

All queries are constrained by the authenticated user's Redshift GRANTs. Write operations are rejected at the application layer.

## Client Configuration

Point any MCP-compatible client at the server endpoint with your Redshift SQL credentials:

```json
{
  "mcpServers": {
    "redshift": {
      "url": "https://<cloudfront-domain>/mcp",
      "headers": {
        "X-Redshift-User": "your_sql_user",
        "X-Redshift-Password": "your_password"
      }
    }
  }
}
```

## Project Structure

```
redshift-mcp-server/
├── redshift-mcp/              # Application source
│   ├── server.py              # FastMCP server (tools, middleware, logging)
│   ├── redshift.py            # Connection pooling, read-only enforcement, queries
│   ├── requirements.txt       # Python dependencies
│   └── Dockerfile             # Container image (for EKS/ECS deployments)
├── deploy/                    # CloudFormation deployment
│   ├── infra.yaml             # Stack: SGs, IAM, EC2, ALB, CloudFront
│   ├── deploy-cfn.sh          # Upload artifact + deploy stack
│   └── deploy.env             # Deployment configuration variables
├── deploy.md                  # Deployment runbook
└── redshift-mcp-server-design.md  # Design specification
```

## Key Design Decisions

- **Credential pass-through via custom headers** — uses native Redshift SQL credentials; avoids the MCP OAuth framework which forbids token passthrough.
- **Stateless server** — no session affinity required; enables horizontal scaling.
- **Per-identity connection pooling** — reuses connections for the same user while bounding total connections.
- **Read-only enforcement** — regex-based statement validation plus `statement_timeout` and row caps.
- **Streamable HTTP transport** — MCP spec `2025-06-18`; POST returns `application/json` (no SSE).

## Prerequisites

- AWS account with a VPC containing public subnets (≥2 AZs) and a private subnet with NAT egress
- An existing Amazon Redshift cluster
- AWS CLI configured with appropriate permissions
- S3 bucket for the application artifact

## Deployment

```bash
# Deploy the full stack (uploads app to S3 + deploys CloudFormation)
./deploy/deploy-cfn.sh
```

The stack provisions CloudFront, a public ALB, and an EC2 instance (Amazon Linux 2023, arm64 `t4g.xlarge`) that self-bootstraps Python 3.11, the CloudWatch agent, and the MCP server under systemd. See [deploy.md](deploy.md) for the full runbook.

## Verify

```bash
# Health check
curl https://<cloudfront-domain>/healthz

# MCP initialize
curl -sS https://<cloudfront-domain>/mcp \
  -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' \
  -H 'MCP-Protocol-Version: 2025-06-18' \
  -H 'X-Redshift-User: analyst_jdoe' \
  -H 'X-Redshift-Password: ********' \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18"}}'
```

## Local Development

```bash
cd redshift-mcp
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Set required environment variables
export RS_HOST=your-cluster.region.redshift.amazonaws.com
export RS_DB=dev

uvicorn server:app --host 0.0.0.0 --port 8080
```

## Security Notes

- **Non-production TLS:** Client → CloudFront is HTTPS. CloudFront → ALB is HTTP (credentials in cleartext on that hop). For production, use a custom domain + ACM cert or CloudFront VPC origin.
- **ALB access restricted** to CloudFront origin-facing IPs via managed prefix list.
- **Origin header validation** defends against DNS-rebinding attacks.
- **Credentials are never logged** — only the SQL username is emitted for audit.

## Teardown

```bash
aws cloudformation delete-stack --region ap-south-1 --stack-name d2-redshift-mcp
```

## License

See the repository root for license information.
