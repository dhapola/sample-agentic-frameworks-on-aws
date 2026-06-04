# Deployment — Redshift MCP Server (CloudFront + public ALB, NON-PROD)

CloudFormation deploys **CloudFront → public ALB → private EC2** in your chosen region. Client
TLS terminates at **CloudFront** using its free, trusted `*.cloudfront.net` certificate —
**no domain or ACM cert to manage**. The EC2 instance (Amazon Linux 2023 **arm64**,
`t4g.xlarge`) self-bootstraps from S3, runs the server under `systemd`, and ships logs to
CloudWatch Logs.

```
MCP client (public internet)
  │  HTTPS  (trusted *.cloudfront.net cert; HTTP auto-redirects to HTTPS)
  ▼
CloudFront distribution            caching disabled, AllViewer (forwards X-Redshift-* headers)
  │  HTTP 80  (origin fetch; see NON-PROD note)
  ▼
Public ALB  (internet-facing, SG locked to CloudFront IP prefix list)
  │  HTTP 8080
  ▼
EC2  (private subnet, no public IP)   systemd: uvicorn server:app (FastMCP)
  │  TCP 5439                          logs -> /var/log/redshift-mcp/app.log -> CW Logs
  ▼
Amazon Redshift                       authZ via SQL user GRANTs
```

## ⚠️ NON-PROD security note (Option B)

CloudFront's cert only secures the **client → CloudFront** leg. The **CloudFront → ALB**
origin fetch is **HTTP over the public internet**, so the end-user Redshift credentials
(`X-Redshift-*` headers) traverse that hop **in cleartext**. Accepted here because this is
a non-prod setup. The ALB SG is locked to CloudFront's `origin-facing` managed prefix list
so the ALB isn't a wide-open HTTP endpoint, but that does not encrypt the hop. For
production, use a custom domain + ACM (end-to-end HTTPS) or a CloudFront VPC origin.

## Files

| File | Role |
|------|------|
| `deploy/infra.yaml` | CloudFormation: SGs, IAM, EC2 (+user-data), target group, public ALB (HTTP), **CloudFront distribution (default cert)**. |
| `deploy/deploy.env` | Deployment config sourced by the wrapper. |
| `deploy/deploy-cfn.sh` | Uploads app to S3, resolves the CloudFront prefix list, `aws cloudformation deploy`. |

## Prerequisites

- **Public subnets** (`PUBLIC_SUBNET_IDS`, ≥2 AZs) for the internet-facing ALB.
- **NAT egress** from the private EC2 subnet — user-data downloads Python 3.11, the
  CloudWatch agent, and PyPI packages. Without NAT (or VPC endpoints) bootstrap fails.
- `REDSHIFT_SG_ID` set — the stack adds inbound 5439 from the EC2 SG to it.
- The S3 bucket specified in `deploy.env` must exist in your region before deploying.
  Create it once if needed:
  ```bash
  aws s3api create-bucket --bucket <your-bucket> --region <your-region> \
    --create-bucket-configuration LocationConstraint=<your-region>
  ```

## Deploy

```bash
./deploy/deploy-cfn.sh        # uploads the app, then deploys the stack; prints outputs
```

The instance runs steps 3.1–3.5 via user-data: install **python3.11** (FastMCP needs
≥3.10) → **arm64 CloudWatch agent** → `pip install` deps → download app from S3 + run
under `systemd` → configure the CloudWatch agent to push `/var/log/redshift-mcp/app.log`
to log group `/redshift-mcp/app`. The ALB target is unhealthy until bootstrap finishes
(~2–4 min) and `/healthz` responds; the CloudFront distribution also takes a few minutes
to deploy.

Outputs: `CloudFrontDomain`, `McpEndpoint`, `AlbDnsName`.

## Stack outputs

After deployment, the stack prints:

| Output | Description |
|--------|-------------|
| `McpEndpoint` | The HTTPS URL for MCP clients (e.g. `https://<id>.cloudfront.net/mcp`) |
| `CloudFrontDomain` | The CloudFront distribution domain |
| `AlbDnsName` | The ALB DNS name (used as CloudFront origin) |

### Client config

```json
{
  "mcpServers": {
    "redshift": {
      "url": "https://<your-cloudfront-domain>/mcp",
      "headers": {
        "X-Redshift-User": "your_sql_user",
        "X-Redshift-Password": "your_password"
      }
    }
  }
}
```

## Verify

```bash
curl https://<your-cloudfront-domain>/healthz     # -> {"status":"ok"}

curl -sS https://<your-cloudfront-domain>/mcp \
  -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' \
  -H 'MCP-Protocol-Version: 2025-06-18' \
  -H 'X-Redshift-User: analyst_jdoe' -H 'X-Redshift-Password: ********' \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18"}}'
```

Instance access via SSM Session Manager: `journalctl -u redshift-mcp -f`. CloudWatch Logs Insights:
`fields @timestamp, tool, user, status, duration_ms | filter event="tool_call"`.

> Browser-based clients send an `Origin` header (the CloudFront domain). The app's
> `ALLOWED_ORIGINS` is empty (it allows header-less, non-browser MCP clients and rejects
> unknown Origins). If you use a browser client, add the CloudFront domain to
> `ALLOWED_ORIGINS` in `/etc/redshift-mcp.env`.

## Update the app

```bash
tar -czf redshift-mcp.tar.gz server.py redshift.py requirements.txt
aws s3 cp redshift-mcp.tar.gz s3://<your-bucket>/redshift-mcp.tar.gz --region <your-region>
# On the instance (SSM Run Command):
aws s3 cp s3://<your-bucket>/redshift-mcp.tar.gz /tmp/app.tar.gz --region <your-region>
sudo tar -xzf /tmp/app.tar.gz -C /opt/redshift-mcp
sudo /opt/redshift-mcp/.venv/bin/pip install -r /opt/redshift-mcp/requirements.txt
sudo systemctl restart redshift-mcp
```

## Teardown

```bash
aws cloudformation delete-stack --region <your-region> --stack-name <your-stack-name>
```
