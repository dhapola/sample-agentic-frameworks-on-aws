# Permission Set: RedshiftQueryAccess — Managed Policies

Screenshot reference: `permission-set-managed-policies.png`  
(Save the screenshot from the Kiro chat into this folder as `permission-set-managed-policies.png`)

## AWS Managed Policies (4)

| Policy name | Type | Description |
|---|---|---|
| `AmazonRedshiftFederatedAuthorization` | AWS managed | Ease-of-use policy for running federated authorization with Amazon Redshift |
| `AmazonRedshiftQueryEditor` | AWS managed | Provides full access to the Amazon Redshift Query Editor |
| `AmazonRedshiftQueryEditorV2FullAccess` | AWS managed | Grants full access to the Amazon Redshift Query Editor V2 |
| `SignInLocalDevelopmentAccess` | AWS managed | Provides permissions for programmatic/local development access |

These policies are attached to the `RedshiftQueryAccess` permission set in AWS IAM Identity Center.

## Inline Policy

In addition to the managed policies above, the following inline policy is attached to the permission set:

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
