#!/usr/bin/env python3
"""
Deploy the Java transaction analysis agent to Amazon Bedrock AgentCore Runtime.

What it does:
  1. Creates an ECR repository (if missing).
  2. Builds the ARM64 container image (Dockerfile in agent/) and pushes it to ECR.
     AgentCore Runtime requires linux/arm64 images, so we use `docker buildx`.
  3. Ensures an IAM execution role that AgentCore Runtime can assume.
  4. Calls CreateAgentRuntime (or UpdateAgentRuntime if one already exists with
     the same name), using the HTTP protocol + PUBLIC network mode.
  5. Saves the resulting agent runtime ARN to deploy-in-agentcore/deployment_info.json.

Prereqs:
  - AWS credentials configured (the same ones the AWS CLI uses).
  - docker with buildx available locally.
  - boto3 (see requirements.txt). Needs a boto3 new enough to expose the
    'bedrock-agentcore-control' service.

Usage:
  python deploy.py
Environment overrides (all optional):
  AWS_REGION                 deploy region                 (default: ap-south-1)
  AGENT_RUNTIME_NAME         AgentCore runtime name        (default: txn_analysis_agent)
  ECR_REPO_NAME              ECR repo name                 (default: txn_analysis_agent)
  IMAGE_TAG                  container image tag           (default: latest)
  AGENTCORE_EXECUTION_ROLE_ARN   use an existing role instead of creating one
  BEDROCK_MODEL_ID           model id passed to the agent  (default: from application.properties)
  BEDROCK_REGION             region the agent calls Bedrock in (default: AWS_REGION)
"""

import json
import os
import subprocess
import sys
import time
from pathlib import Path

import boto3
from botocore.exceptions import ClientError

# --------------------------------------------------------------------------- #
# Configuration
# --------------------------------------------------------------------------- #
REGION = os.environ.get("AWS_REGION", "ap-south-1")
AGENT_RUNTIME_NAME = os.environ.get("AGENT_RUNTIME_NAME", "txn_analysis_agent")
ECR_REPO_NAME = os.environ.get("ECR_REPO_NAME", "txn_analysis_agent")
IMAGE_TAG = os.environ.get("IMAGE_TAG", "latest")
ROLE_NAME = "BedrockAgentCoreExecutionRole-java-bedrock-agent"

PROJECT_ROOT = Path(__file__).resolve().parent.parent
AGENT_DIR = PROJECT_ROOT / "agent"
INFO_FILE = Path(__file__).resolve().parent / "deployment_info.json"

# Model config forwarded to the container as environment variables. The Java
# AgentConfig reads these env vars (they take precedence over the bundled
# application.properties).
BEDROCK_MODEL_ID = os.environ.get("BEDROCK_MODEL_ID")  # None -> use jar default
BEDROCK_REGION = os.environ.get("BEDROCK_REGION", REGION)

session = boto3.Session(region_name=REGION)
sts = session.client("sts")
ecr = session.client("ecr")
iam = session.client("iam")
agentcore_control = session.client("bedrock-agentcore-control")

ACCOUNT_ID = sts.get_caller_identity()["Account"]
ECR_URI = f"{ACCOUNT_ID}.dkr.ecr.{REGION}.amazonaws.com/{ECR_REPO_NAME}"
IMAGE_URI = f"{ECR_URI}:{IMAGE_TAG}"


def run(cmd, **kwargs):
    """Run a shell command, streaming output, raising on failure."""
    print(f"  $ {' '.join(cmd)}")
    subprocess.run(cmd, check=True, **kwargs)


# --------------------------------------------------------------------------- #
# Step 1 + 2: ECR repo and image build/push
# --------------------------------------------------------------------------- #
def ensure_ecr_repo():
    try:
        ecr.describe_repositories(repositoryNames=[ECR_REPO_NAME])
        print(f"[ecr] repository '{ECR_REPO_NAME}' already exists")
    except ecr.exceptions.RepositoryNotFoundException:
        ecr.create_repository(repositoryName=ECR_REPO_NAME)
        print(f"[ecr] created repository '{ECR_REPO_NAME}'")


def docker_login():
    print("[docker] logging in to ECR")
    pwd = subprocess.check_output(
        ["aws", "ecr", "get-login-password", "--region", REGION]
    ).decode().strip()
    registry = f"{ACCOUNT_ID}.dkr.ecr.{REGION}.amazonaws.com"
    run(["docker", "login", "--username", "AWS", "--password-stdin", registry],
        input=pwd.encode())


def build_and_push_image():
    print(f"[docker] building ARM64 image {IMAGE_URI}")
    run([
        "docker", "build",
        "--platform", "linux/arm64",
        "-t", IMAGE_URI,
        str(AGENT_DIR),
    ])
    print(f"[docker] pushing {IMAGE_URI}")
    run(["docker", "push", IMAGE_URI])
    print(f"[docker] pushed {IMAGE_URI}")


# --------------------------------------------------------------------------- #
# Step 3: IAM execution role
# --------------------------------------------------------------------------- #
def ensure_execution_role():
    override = os.environ.get("AGENTCORE_EXECUTION_ROLE_ARN")
    if override:
        print(f"[iam] using provided execution role: {override}")
        return override

    trust_policy = {
        "Version": "2012-10-17",
        "Statement": [{
            "Effect": "Allow",
            "Principal": {"Service": "bedrock-agentcore.amazonaws.com"},
            "Action": "sts:AssumeRole",
            "Condition": {
                "StringEquals": {"aws:SourceAccount": ACCOUNT_ID},
                "ArnLike": {
                    "aws:SourceArn":
                        f"arn:aws:bedrock-agentcore:{REGION}:{ACCOUNT_ID}:*"
                },
            },
        }],
    }

    permissions = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "BedrockModelInvocation",
                "Effect": "Allow",
                "Action": [
                    "bedrock:InvokeModel",
                    "bedrock:InvokeModelWithResponseStream",
                ],
                "Resource": [
                    "arn:aws:bedrock:*::foundation-model/*",
                    f"arn:aws:bedrock:*:{ACCOUNT_ID}:inference-profile/*",
                ],
            },
            {
                "Sid": "EcrPull",
                "Effect": "Allow",
                "Action": [
                    "ecr:GetAuthorizationToken",
                    "ecr:BatchGetImage",
                    "ecr:GetDownloadUrlForLayer",
                ],
                "Resource": "*",
            },
            {
                "Sid": "Logs",
                "Effect": "Allow",
                "Action": [
                    "logs:CreateLogGroup",
                    "logs:CreateLogStream",
                    "logs:PutLogEvents",
                    "logs:DescribeLogStreams",
                ],
                "Resource": "*",
            },
            {
                "Sid": "Observability",
                "Effect": "Allow",
                "Action": [
                    "cloudwatch:PutMetricData",
                    "xray:PutTraceSegments",
                    "xray:PutTelemetryRecords",
                ],
                "Resource": "*",
            },
        ],
    }

    try:
        resp = iam.create_role(
            RoleName=ROLE_NAME,
            AssumeRolePolicyDocument=json.dumps(trust_policy),
            Description="Execution role for the Java agent in AgentCore Runtime",
        )
        role_arn = resp["Role"]["Arn"]
        print(f"[iam] created role {ROLE_NAME}")
    except iam.exceptions.EntityAlreadyExistsException:
        role_arn = iam.get_role(RoleName=ROLE_NAME)["Role"]["Arn"]
        # keep trust policy current
        iam.update_assume_role_policy(
            RoleName=ROLE_NAME, PolicyDocument=json.dumps(trust_policy)
        )
        print(f"[iam] role {ROLE_NAME} already exists")

    iam.put_role_policy(
        RoleName=ROLE_NAME,
        PolicyName="agentcore-runtime-permissions",
        PolicyDocument=json.dumps(permissions),
    )
    # IAM role propagation can lag; give it a moment before AgentCore validates it.
    time.sleep(10)
    return role_arn


# --------------------------------------------------------------------------- #
# Step 4: create / update the agent runtime
# --------------------------------------------------------------------------- #
def env_vars():
    env = {"BEDROCK_REGION": BEDROCK_REGION}
    if BEDROCK_MODEL_ID:
        env["BEDROCK_MODEL_ID"] = BEDROCK_MODEL_ID
    return env


def find_existing_runtime():
    paginator = agentcore_control.get_paginator("list_agent_runtimes") \
        if agentcore_control.can_paginate("list_agent_runtimes") else None
    runtimes = []
    if paginator:
        for page in paginator.paginate():
            runtimes.extend(page.get("agentRuntimes", []))
    else:
        runtimes = agentcore_control.list_agent_runtimes().get("agentRuntimes", [])
    for rt in runtimes:
        if rt.get("agentRuntimeName") == AGENT_RUNTIME_NAME:
            return rt
    return None


def deploy_runtime(role_arn):
    artifact = {"containerConfiguration": {"containerUri": IMAGE_URI}}
    network = {"networkMode": "PUBLIC"}
    protocol = {"serverProtocol": "HTTP"}

    existing = find_existing_runtime()
    if existing:
        runtime_id = existing["agentRuntimeId"]
        print(f"[agentcore] updating existing runtime {runtime_id}")
        resp = agentcore_control.update_agent_runtime(
            agentRuntimeId=runtime_id,
            agentRuntimeArtifact=artifact,
            roleArn=role_arn,
            networkConfiguration=network,
            protocolConfiguration=protocol,
            environmentVariables=env_vars(),
        )
    else:
        print(f"[agentcore] creating runtime '{AGENT_RUNTIME_NAME}'")
        resp = agentcore_control.create_agent_runtime(
            agentRuntimeName=AGENT_RUNTIME_NAME,
            agentRuntimeArtifact=artifact,
            roleArn=role_arn,
            networkConfiguration=network,
            protocolConfiguration=protocol,
            environmentVariables=env_vars(),
        )

    arn = resp["agentRuntimeArn"]
    print(f"[agentcore] agentRuntimeArn = {arn}")
    return arn


def main():
    print(f"Region={REGION} Account={ACCOUNT_ID}")
    print(f"Image={IMAGE_URI}")
    ensure_ecr_repo()
    docker_login()
    build_and_push_image()
    role_arn = ensure_execution_role()
    arn = deploy_runtime(role_arn)

    INFO_FILE.write_text(json.dumps({
        "agentRuntimeArn": arn,
        "region": REGION,
        "imageUri": IMAGE_URI,
        "executionRoleArn": role_arn,
    }, indent=2))
    print(f"\nSaved deployment info to {INFO_FILE}")
    print("Deployment complete. Invoke with:")
    print("  cd ../agentcore-client && python agentcore_client.py")


if __name__ == "__main__":
    try:
        main()
    except (ClientError, subprocess.CalledProcessError) as e:
        print(f"\nERROR: {e}", file=sys.stderr)
        sys.exit(1)
