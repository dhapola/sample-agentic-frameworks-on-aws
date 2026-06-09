#!/usr/bin/env bash
#
# Tear down all resources created by deploy.sh:
#   1. AgentCore Runtime (and its endpoints)
#   2. ECR repository (and all images)
#   3. IAM role + inline policy
#
# Usage:
#   ./scripts/destroy.sh           # asks for confirmation
#   ./scripts/destroy.sh --yes     # skip prompt

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=config.sh
source "${SCRIPT_DIR}/config.sh"

require aws

ACCOUNT_ID="$(get_account_id)"

log "Account:    ${ACCOUNT_ID}"
log "Region:     ${AWS_REGION}"
log "Agent:      ${AGENT_NAME}"
log "Role:       ${IAM_ROLE_NAME}"
log "ECR repo:   ${ECR_REPO_NAME}"
echo

if [ "${1:-}" != "--yes" ]; then
  read -r -p "Delete all resources listed above? (y/N) " confirm
  case "${confirm}" in
    [yY]|[yY][eE][sS]) ;;
    *) log "Aborted"; exit 0 ;;
  esac
fi

# ── Step 1: AgentCore Runtime ─────────────────────────────────────────────────

log "Step 1/3 — AgentCore Runtime"

RUNTIME_ID="$(aws bedrock-agentcore-control list-agent-runtimes \
  --region "${AWS_REGION}" \
  --query "agentRuntimes[?agentRuntimeName=='${AGENT_NAME}'].agentRuntimeId | [0]" \
  --output text 2>/dev/null || echo "None")"

if [ "${RUNTIME_ID}" != "None" ] && [ -n "${RUNTIME_ID}" ]; then
  # Delete any non-DEFAULT endpoints first
  ENDPOINTS="$(aws bedrock-agentcore-control list-agent-runtime-endpoints \
    --region "${AWS_REGION}" \
    --agent-runtime-id "${RUNTIME_ID}" \
    --query "runtimeEndpoints[?name!='DEFAULT'].name" \
    --output text 2>/dev/null || echo "")"

  for endpoint in ${ENDPOINTS}; do
    log "Deleting endpoint ${endpoint}"
    aws bedrock-agentcore-control delete-agent-runtime-endpoint \
      --region "${AWS_REGION}" \
      --agent-runtime-id "${RUNTIME_ID}" \
      --endpoint-name "${endpoint}" >/dev/null
  done

  log "Deleting runtime ${RUNTIME_ID}"
  aws bedrock-agentcore-control delete-agent-runtime \
    --region "${AWS_REGION}" \
    --agent-runtime-id "${RUNTIME_ID}" >/dev/null
  ok "Runtime deleted"
else
  warn "No runtime named ${AGENT_NAME} found"
fi
echo

# ── Step 2: ECR repository ────────────────────────────────────────────────────

log "Step 2/3 — ECR repository"

if aws ecr describe-repositories --repository-names "${ECR_REPO_NAME}" --region "${AWS_REGION}" >/dev/null 2>&1; then
  log "Deleting repository ${ECR_REPO_NAME} (with all images)"
  aws ecr delete-repository \
    --repository-name "${ECR_REPO_NAME}" \
    --region "${AWS_REGION}" \
    --force >/dev/null
  ok "Repository deleted"
else
  warn "Repository ${ECR_REPO_NAME} not found"
fi
echo

# ── Step 3: IAM role + policy ─────────────────────────────────────────────────

log "Step 3/3 — IAM role"

if aws iam get-role --role-name "${IAM_ROLE_NAME}" >/dev/null 2>&1; then
  # Detach inline policies
  for policy in $(aws iam list-role-policies --role-name "${IAM_ROLE_NAME}" --query 'PolicyNames' --output text); do
    log "Removing inline policy ${policy}"
    aws iam delete-role-policy --role-name "${IAM_ROLE_NAME}" --policy-name "${policy}"
  done

  # Detach managed policies (in case any were attached manually)
  for policy_arn in $(aws iam list-attached-role-policies --role-name "${IAM_ROLE_NAME}" --query 'AttachedPolicies[].PolicyArn' --output text); do
    log "Detaching managed policy ${policy_arn}"
    aws iam detach-role-policy --role-name "${IAM_ROLE_NAME}" --policy-arn "${policy_arn}"
  done

  log "Deleting role ${IAM_ROLE_NAME}"
  aws iam delete-role --role-name "${IAM_ROLE_NAME}"
  ok "Role deleted"
else
  warn "Role ${IAM_ROLE_NAME} not found"
fi

echo
ok "Cleanup complete"
