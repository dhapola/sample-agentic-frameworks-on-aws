#!/usr/bin/env bash
#
# Deploy the Redshift MCP server to Amazon Bedrock AgentCore Runtime.
#
# Idempotent — safe to run multiple times. Will create or update each resource:
#   1. IAM execution role + inline policy
#   2. ECR repository
#   3. Docker image (linux/arm64) build & push
#   4. AgentCore Runtime (create or update with new image version)
#
# Usage:
#   ./scripts/deploy.sh
#
# Override defaults with env vars:
#   AWS_REGION=us-west-2 ./scripts/deploy.sh
#   IMAGE_TAG=v1.2 ./scripts/deploy.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=config.sh
source "${SCRIPT_DIR}/config.sh"

# ── Pre-flight checks ─────────────────────────────────────────────────────────

require aws
require jq

# Detect container CLI: prefer real docker with buildx, fall back to finch
if command -v docker >/dev/null 2>&1 && docker buildx version >/dev/null 2>&1 && docker info >/dev/null 2>&1; then
  CONTAINER_CLI="docker"
  USE_BUILDX="yes"
elif command -v finch >/dev/null 2>&1 && [ "$(finch vm status 2>/dev/null)" = "Running" ]; then
  CONTAINER_CLI="finch"
  USE_BUILDX="no"
elif command -v docker >/dev/null 2>&1 && docker info >/dev/null 2>&1; then
  CONTAINER_CLI="docker"
  USE_BUILDX="no"
else
  err "No working container runtime found. Install Docker (running) or Finch (with VM started)."
  exit 1
fi

log "Container CLI: ${CONTAINER_CLI} (buildx=${USE_BUILDX})"

ACCOUNT_ID="$(get_account_id)"
ECR_URI="${ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_REPO_NAME}"

log "Account:    ${ACCOUNT_ID}"
log "Region:     ${AWS_REGION}"
log "Agent:      ${AGENT_NAME}"
log "Role:       ${IAM_ROLE_NAME}"
log "ECR repo:   ${ECR_REPO_NAME}"
log "Image tag:  ${IMAGE_TAG}"
echo

# ── Step 1: IAM execution role ────────────────────────────────────────────────

log "Step 1/4 — IAM execution role"

# Render IAM JSON files with the actual account ID
TRUST_POLICY="$(sed "s/__ACCOUNT_ID__/${ACCOUNT_ID}/g" "${IAM_DIR}/execution-role-trust-policy.json")"
ROLE_POLICY="$(sed "s/__ACCOUNT_ID__/${ACCOUNT_ID}/g" "${IAM_DIR}/execution-role-policy.json")"

if aws iam get-role --role-name "${IAM_ROLE_NAME}" >/dev/null 2>&1; then
  ok "Role already exists, updating trust policy"
  aws iam update-assume-role-policy \
    --role-name "${IAM_ROLE_NAME}" \
    --policy-document "${TRUST_POLICY}" \
    >/dev/null
else
  log "Creating role ${IAM_ROLE_NAME}"
  aws iam create-role \
    --role-name "${IAM_ROLE_NAME}" \
    --assume-role-policy-document "${TRUST_POLICY}" \
    --description "Execution role for Redshift MCP server on AgentCore Runtime" \
    --query 'Role.Arn' --output text
  ok "Role created"
fi

log "Attaching inline policy ${IAM_POLICY_NAME}"
aws iam put-role-policy \
  --role-name "${IAM_ROLE_NAME}" \
  --policy-name "${IAM_POLICY_NAME}" \
  --policy-document "${ROLE_POLICY}"

ROLE_ARN="$(aws iam get-role --role-name "${IAM_ROLE_NAME}" --query 'Role.Arn' --output text)"
ok "Role ARN: ${ROLE_ARN}"
echo

# ── Step 2: ECR repository ────────────────────────────────────────────────────

log "Step 2/4 — ECR repository"

if aws ecr describe-repositories --repository-names "${ECR_REPO_NAME}" --region "${AWS_REGION}" >/dev/null 2>&1; then
  ok "Repository ${ECR_REPO_NAME} already exists"
else
  log "Creating repository ${ECR_REPO_NAME}"
  aws ecr create-repository \
    --repository-name "${ECR_REPO_NAME}" \
    --region "${AWS_REGION}" \
    --image-scanning-configuration scanOnPush=true \
    --encryption-configuration encryptionType=AES256 \
    --query 'repository.repositoryUri' --output text
  ok "Repository created"
fi
echo

# ── Step 3: Build & push Docker image ─────────────────────────────────────────

log "Step 3/4 — Build & push Docker image (linux/arm64)"

log "Logging in to ECR"
aws ecr get-login-password --region "${AWS_REGION}" | \
  ${CONTAINER_CLI} login --username AWS --password-stdin "${ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"

log "Building image (this may take a few minutes on first run)"
cd "${PROJECT_ROOT}"
if [ "${USE_BUILDX}" = "yes" ]; then
  ${CONTAINER_CLI} buildx build \
    --platform linux/arm64 \
    --provenance=false \
    -t "${ECR_URI}:${IMAGE_TAG}" \
    --push \
    .
  ok "Image built and pushed: ${ECR_URI}:${IMAGE_TAG}"
else
  ${CONTAINER_CLI} build \
    --platform linux/arm64 \
    -t "${ECR_URI}:${IMAGE_TAG}" \
    .
  log "Pushing image to ECR"
  ${CONTAINER_CLI} push "${ECR_URI}:${IMAGE_TAG}"
  ok "Image pushed: ${ECR_URI}:${IMAGE_TAG}"
fi
echo

# ── Step 4: Create or update AgentCore Runtime ────────────────────────────────

log "Step 4/4 — AgentCore Runtime"

# Check if runtime exists by listing and matching name
EXISTING_RUNTIME_ID="$(aws bedrock-agentcore-control list-agent-runtimes \
  --region "${AWS_REGION}" \
  --query "agentRuntimes[?agentRuntimeName=='${AGENT_NAME}'].agentRuntimeId | [0]" \
  --output text 2>/dev/null || echo "None")"

# Build the request body as JSON files for clarity
ARTIFACT_JSON=$(cat <<EOF
{
  "containerConfiguration": {
    "containerUri": "${ECR_URI}:${IMAGE_TAG}"
  }
}
EOF
)

NETWORK_JSON='{"networkMode": "PUBLIC"}'

PROTOCOL_JSON='{"serverProtocol": "MCP"}'

ENV_VARS_JSON=$(cat <<EOF
{
  "REDSHIFT_CLUSTER_ID": "${REDSHIFT_CLUSTER_ID}",
  "REDSHIFT_DATABASE": "${REDSHIFT_DATABASE}",
  "AWS_REGION": "${AWS_REGION}"
}
EOF
)

if [ "${EXISTING_RUNTIME_ID}" != "None" ] && [ -n "${EXISTING_RUNTIME_ID}" ]; then
  log "Updating existing runtime ${EXISTING_RUNTIME_ID}"
  aws bedrock-agentcore-control update-agent-runtime \
    --region "${AWS_REGION}" \
    --agent-runtime-id "${EXISTING_RUNTIME_ID}" \
    --role-arn "${ROLE_ARN}" \
    --agent-runtime-artifact "${ARTIFACT_JSON}" \
    --network-configuration "${NETWORK_JSON}" \
    --protocol-configuration "${PROTOCOL_JSON}" \
    --environment-variables "${ENV_VARS_JSON}" \
    --output json >/dev/null
  RUNTIME_ID="${EXISTING_RUNTIME_ID}"
  ok "Runtime updated"
else
  log "Creating new runtime ${AGENT_NAME}"
  aws bedrock-agentcore-control create-agent-runtime \
    --region "${AWS_REGION}" \
    --agent-runtime-name "${AGENT_NAME}" \
    --description "Redshift MCP server with per-user IAM Identity Center auth" \
    --role-arn "${ROLE_ARN}" \
    --agent-runtime-artifact "${ARTIFACT_JSON}" \
    --network-configuration "${NETWORK_JSON}" \
    --protocol-configuration "${PROTOCOL_JSON}" \
    --environment-variables "${ENV_VARS_JSON}" \
    --output json >/dev/null
  RUNTIME_ID="$(aws bedrock-agentcore-control list-agent-runtimes \
    --region "${AWS_REGION}" \
    --query "agentRuntimes[?agentRuntimeName=='${AGENT_NAME}'].agentRuntimeId | [0]" \
    --output text)"
  ok "Runtime created"
fi

# Fetch authoritative details
RUNTIME_DETAILS="$(aws bedrock-agentcore-control get-agent-runtime \
  --region "${AWS_REGION}" \
  --agent-runtime-id "${RUNTIME_ID}" \
  --output json)"

RUNTIME_ARN="$(echo "${RUNTIME_DETAILS}" | jq -r '.agentRuntimeArn')"
RUNTIME_VERSION="$(echo "${RUNTIME_DETAILS}" | jq -r '.agentRuntimeVersion')"

echo
ok "Deployment complete!"
echo
echo "  Runtime ARN:     ${RUNTIME_ARN}"
echo "  Runtime ID:      ${RUNTIME_ID}"
echo "  Runtime version: ${RUNTIME_VERSION}"
echo

# Wait for runtime to become READY
log "Waiting for runtime to reach READY status (this can take 1-3 minutes)..."
for i in {1..36}; do
  STATUS="$(aws bedrock-agentcore-control get-agent-runtime \
    --region "${AWS_REGION}" \
    --agent-runtime-id "${RUNTIME_ID}" \
    --query 'status' --output text 2>/dev/null || echo "UNKNOWN")"
  if [ "${STATUS}" = "READY" ]; then
    ok "Runtime is READY"
    break
  fi
  if [ "${STATUS}" = "CREATE_FAILED" ] || [ "${STATUS}" = "UPDATE_FAILED" ]; then
    err "Runtime entered ${STATUS} state. Check CloudWatch logs."
    exit 1
  fi
  printf "  status=%s (%d/36)\r" "${STATUS}" "${i}"
  sleep 5
done

echo
log "Run ./scripts/get_client_config.sh to print the analyst MCP client config."
