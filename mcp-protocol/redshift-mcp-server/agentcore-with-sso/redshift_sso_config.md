# Redshift IAM Identity Center (IdC) — Setup & Configuration Guide

This guide documents all the steps required to configure Amazon Redshift with AWS IAM Identity Center federated authentication, including IdC application setup, Redshift role/user configuration, and per-user access permissions. It reflects the actual working configuration of this project.

---

## Architecture Overview

```
User (aws login) → IAM session (assumed-role/IdCRole/<username>)
    → MCP client extracts username from ARN
    → Calls AgentCore Runtime with DbUser=<username>
    → AgentCore calls Redshift Data API with DbUser=<username>
    → Data API calls redshift:GetClusterCredentials internally
    → Query runs as IAM:ddredshift in Redshift
```

Redshift authenticates users via the **IAM** path (not native IdC database integration). Each IdC user maps to a Redshift database user prefixed with `IAM:`.

---

## Step 1: AWS IAM Identity Center Setup

### 1.1 Create Users and Groups

1. Open **IAM Identity Center** in the AWS Console (region: `ap-south-1`)
2. Go to **Users** → **Add user**
   - Create users who need Redshift access (e.g., `ddredshift`)
3. Go to **Groups** → **Create group**
   - Create a group: `redshift-users`
   - Add the relevant users to this group

### 1.2 Create a Redshift IdC Application

1. In IAM Identity Center, go to **Applications** → **Add application**
2. Select **AWS managed application** → search for **Amazon Redshift**
3. Application name: `d2-redshift-sso-app`
4. Complete the wizard — this creates a trusted application link between IdC and Redshift
5. **Assign the `redshift-users` group** to this application
   - Go to the application → **Assign users and groups** → add `redshift-users`

### 1.3 Create an IAM Identity Center Permission Set for Redshift

1. Go to **Permission sets** → **Create permission set**
2. Select **Custom permission set**
3. Name it: `RedshiftQueryAccess`
4. Attach the following **4 AWS managed policies** (see `iam/permission-set-managed-policies.png`):

| Policy name | Type | Description |
|---|---|---|
| `AmazonRedshiftFederatedAuthorization` | AWS managed | Ease-of-use policy for running federated authorization with Amazon Redshift |
| `AmazonRedshiftQueryEditor` | AWS managed | Provides full access to the Amazon Redshift Query Editor |
| `AmazonRedshiftQueryEditorV2FullAccess` | AWS managed | Grants full access to the Amazon Redshift Query Editor V2 |
| `SignInLocalDevelopmentAccess` | AWS managed | Provides permissions for programmatic/local development access |

5. Add the following **inline policy** to the permission set:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "InvokeBedrockAgentCore",
      "Effect": "Allow",
      "Action": [
        "bedrock-agentcore:InvokeAgentRuntime"
      ],
      "Resource": "arn:aws:bedrock-agentcore:ap-south-1:__ACCOUNT_ID__:runtime/*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "redshift:DescribeClusters",
        "redshift:GetClusterCredentialsWithIAM",
        "redshift-serverless:ListWorkgroups",
        "redshift-serverless:ListNamespaces",
        "redshift-serverless:GetWorkgroup",
        "redshift-serverless:GetNamespace",
        "tag:GetResources",
        "redshift-data:ExecuteStatement",
        "redshift-data:BatchExecuteStatement",
        "redshift-data:DescribeStatement",
        "redshift-data:GetStatementResult",
        "redshift-data:ListStatements",
        "redshift-data:ListDatabases",
        "redshift-data:ListSchemas",
        "redshift-data:ListTables",
        "redshift-data:DescribeTable",
        "redshift-data:CancelStatement",
        "sqlworkbench:*"
      ],
      "Resource": "*"
    }
  ]
}
```

The inline policy grants two groups of permissions:
- **AgentCore invocation** (`InvokeBedrockAgentCore`): allows calling any AgentCore runtime in `ap-south-1` under your account
- **Redshift access**: covers cluster/serverless discovery, Data API operations (execute, describe, list, cancel), and full SQL Workbench access

6. Assign this permission set to the AWS account for the `redshift-users` group
   - Go to **AWS accounts** → select the account → **Assign users or groups**
   - Select group: `redshift-users`, permission set: `RedshiftQueryAccess`

> This creates an IAM role in the account named `AWSReservedSSO_RedshiftQueryAccess_<suffix>`. When a user logs in via `aws login`, their session ARN looks like:
> `arn:aws:sts::<account_id>:assumed-role/AWSReservedSSO_RedshiftQueryAccess_<suffix>/<idc_username>`

---

## Step 2: IAM Role Permissions

The IAM role `AWSReservedSSO_RedshiftQueryAccess_<suffix>` is created automatically when the permission set is assigned to an account. Its permissions come entirely from the permission set defined in Step 1 — no additional inline/attached policies are needed on the role itself.

The inline policy on the permission set (added in Step 1.3) already covers:

| Permission group | Actions |
|---|---|
| AgentCore invocation | `bedrock-agentcore:InvokeAgentRuntime` |
| Redshift cluster discovery | `redshift:DescribeClusters`, `redshift:GetClusterCredentialsWithIAM` |
| Redshift Serverless discovery | `redshift-serverless:ListWorkgroups/Namespaces`, `GetWorkgroup/Namespace` |
| Redshift Data API | `ExecuteStatement`, `BatchExecuteStatement`, `DescribeStatement`, `GetStatementResult`, `ListStatements`, `ListDatabases`, `ListSchemas`, `ListTables`, `DescribeTable`, `CancelStatement` |
| Tag discovery | `tag:GetResources` |
| SQL Workbench | `sqlworkbench:*` |

---

## Step 3: Redshift Cluster Configuration

### 3.1 Enable IdC Integration on the Cluster

1. Open **Amazon Redshift** in the AWS Console
2. Select your cluster: `sample-redshift-cluster-mcp`
3. Go to **Properties** → **Database configurations**
4. Under **IAM Identity Center integration**, click **Edit**
5. Enable IdC integration and select your Identity Center instance
6. Select the IdC application: `d2-redshift-sso-app`
7. Save changes

> This step creates the `D2IDC:` role namespace in Redshift, which maps IdC groups to Redshift roles.

### 3.2 Verify IdC Role Mapping

Once IdC integration is enabled, Redshift automatically creates a role corresponding to the IdC application. Verify by connecting as `awsuser` in the Query Editor and running:

```sql
SELECT role_name FROM svv_roles WHERE role_name LIKE 'D2IDC:%';
```

You should see `D2IDC:redshift-users` (maps to the `redshift-users` IdC group).

---

## Step 4: Redshift Database Users and Permissions

### 4.1 Why IAM Users Must Be Created Manually

When users connect via the Redshift Data API with `DbUser=<username>`, Redshift looks for a database user named `IAM:<username>`. This user is **not** auto-created — it must be provisioned explicitly by an admin.

> Note: The `D2IDC:redshift-users` role is governed by the unified governance policy and **cannot be granted to users via SQL**. Permissions must be granted directly to the `IAM:` user instead.

### 4.2 Create the IAM Database User

Connect to Redshift as `awsuser` (admin) using the Query Editor and run:

```sql
-- Create the IAM-federated user (no password — authenticated via IAM)
CREATE USER "IAM:" PASSWORD DISABLE;
```

Repeat this for every IdC user who needs access. The username must exactly match the IdC username (the session name portion of their IAM ARN).

### 4.3 Grant Schema Access

```sql
-- Grant access to the schema
GRANT USAGE ON SCHEMA public TO "IAM:ddredshift";
```

### 4.4 Grant Table Permissions

```sql
-- Grant SELECT on all current tables
GRANT SELECT ON ALL TABLES IN SCHEMA public TO "IAM:ddredshift";

-- Grant SELECT on all future tables automatically
ALTER DEFAULT PRIVILEGES IN SCHEMA public
  GRANT SELECT ON TABLES TO "IAM:ddredshift";
```

### 4.5 Verify User and Permissions

```sql
-- Check user exists
SELECT usename, usecreatedb, usesuper FROM pg_user WHERE usename = 'IAM:ddredshift';

-- Check role assignments (if any)
SELECT * FROM svv_user_grants WHERE user_name = 'IAM:ddredshift';

-- Check table privileges
SELECT * FROM information_schema.role_table_grants
WHERE grantee = 'IAM:ddredshift';
```

---

## Step 5: Redshift Data API Configuration

The MCP server uses the Redshift Data API to execute queries — no direct TCP connection to the cluster is needed. The Data API internally calls `redshift:GetClusterCredentials` to authenticate.

Key parameters used in `ExecuteStatement`:

| Parameter | Value |
|-----------|-------|
| `ClusterIdentifier` | `sample-redshift-cluster-mcp` |
| `Database` | `dev` |
| `DbUser` | `IAM:ddredshift` (prefixed by the server) |
| `Region` | `ap-south-1` |

The MCP server (`mcp_server.py`) receives the plain username (e.g., `ddredshift`) from the request header and prepends `IAM:` when calling the Data API.

---

## Step 6: Client Setup (Per Analyst)

### 6.1 One-Time Setup

```bash
# Install AWS CLI v2 (if not already installed)
# https://docs.aws.amazon.com/cli/latest/userguide/install-cliv2.html

# Configure SSO profile
aws configure sso
# Prompts:
#   SSO session name: redshift-sso
#   SSO start URL: <your Identity Center portal URL>
#   SSO region: ap-south-1
#   SSO registration scopes: sso:account:access
# Then select: account, role (RedshiftQueryAccess), output format

# Install uv (required to run mcp-proxy-for-aws)
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 6.2 Daily Login

```bash
aws login
# Opens browser → authenticate with your IdC credentials on the portal
# Credentials cached in ~/.aws/sso/cache for ~8 hours
```

### 6.3 MCP Client Configuration

Add to `~/.kiro/settings/mcp.json` (or equivalent for Claude Desktop/Code):

```json
{
  "mcpServers": {
    "redshift-idc": {
      "command": "sh",
      "args": [
        "-c",
        "DB_USER=$(aws sts get-caller-identity --query Arn --output text | cut -d'/' -f3) && uvx mcp-proxy-for-aws@latest https://bedrock-agentcore.ap-south-1.amazonaws.com/runtimes/<RUNTIME_ARN_ENCODED>/invocations --metadata DbUser=$DB_USER"
      ]
    }
  }
}
```

- `DB_USER` is automatically extracted from the IAM session ARN — no manual input
- `<RUNTIME_ARN_ENCODED>` is the AgentCore Runtime ARN with `:` → `%3A` and `/` → `%2F`
- The `--metadata DbUser=` flag sets the `X-Amzn-Bedrock-AgentCore-Runtime-Custom-DbUser` header

---

## Step 7: Adding New Users (Ongoing Admin Task)

For each new analyst, repeat the following:

**In IAM Identity Center:**
1. Create the user (or confirm they exist)
2. Add them to the `redshift-users` group
3. Assign the `RedshiftQueryAccess` permission set to their account (if not inherited via group)

**In Redshift (as awsuser):**
```sql
CREATE USER "IAM:<new_username>" PASSWORD DISABLE;
GRANT USAGE ON SCHEMA public TO "IAM:<new_username>";
GRANT SELECT ON ALL TABLES IN SCHEMA public TO "IAM:<new_username>";
ALTER DEFAULT PRIVILEGES IN SCHEMA public
  GRANT SELECT ON TABLES TO "IAM:<new_username>";
```

**Send the analyst:**
- The MCP client config snippet with the encoded Runtime ARN
- Instructions to run `aws configure sso` and `aws login`

---

## Troubleshooting

### `FATAL: user "IAM:<username>" does not exist`

The Redshift database user has not been created. Run:
```sql
CREATE USER "IAM:<username>" PASSWORD DISABLE;
GRANT USAGE ON SCHEMA public TO "IAM:<username>";
GRANT SELECT ON ALL TABLES IN SCHEMA public TO "IAM:<username>";
```

### `ERROR: permission denied for relation <table>`

The user exists but lacks table-level SELECT grants. Run:
```sql
GRANT SELECT ON ALL TABLES IN SCHEMA public TO "IAM:<username>";
```

### `ERROR: cannot grant role due to unified governance policy`

The `D2IDC:` roles are managed by Lake Formation/unified governance and cannot be manually granted via SQL. Grant permissions directly to the `IAM:` user instead (as above).

### MCP server resolves wrong username (e.g., `dhapola-Isengard` instead of IdC username)

The shell command `cut -d'/' -f3` extracts the session name from the IAM ARN. If the user is logged in with a non-IdC profile (e.g., Isengard), it picks up the wrong identity. The analyst must run `aws login` with the IdC SSO profile before starting the MCP client.

### `list_schemas` returns empty but queries work

This is a known quirk — the `list_schemas` tool queries system catalog views that may not be visible to IAM-federated users. Use `execute_query` with:
```sql
SELECT schemaname, tablename FROM pg_tables
WHERE schemaname NOT IN ('pg_catalog', 'information_schema')
ORDER BY schemaname, tablename;
```

---

## Reference: Key AWS Resource Names

| Resource | Value |
|----------|-------|
| AWS Region | `ap-south-1` |
| Identity Center URL | `https://<IDENTITY_CENTER_SUBDOMAIN>.portal.ap-south-1.app.aws/` |
| IdC Application | `d2-redshift-sso-app` |
| IdC Group | `redshift-users` |
| Redshift Cluster | `sample-redshift-cluster-mcp` |
| Redshift Database | `dev` |
| Redshift Admin User | `awsuser` |
| Redshift IAM Role (IdC) | `D2IDC:redshift-users` |
| IAM Permission Set | `RedshiftQueryAccess` |
| IAM Permission Set Policies | `AmazonRedshiftFederatedAuthorization`, `AmazonRedshiftQueryEditor`, `AmazonRedshiftQueryEditorV2FullAccess`, `SignInLocalDevelopmentAccess` |
| IAM Role (assumed by users) | `AWSReservedSSO_RedshiftQueryAccess_<suffix>` |
