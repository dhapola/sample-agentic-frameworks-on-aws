#!/usr/bin/env bash
# Shared configuration sourced by all deployment scripts.
# Override any value by exporting it before running the script.

# ── AWS ───────────────────────────────────────────────────────────────────────
: "${AWS_REGION:=ap-south-1}"
export AWS_REGION
export AWS_DEFAULT_REGION="${AWS_REGION}"

# ── Naming ────────────────────────────────────────────────────────────────────
: "${AGENT_NAME:=redshift_mcp_server}"               # AgentCore runtime name (alphanumeric + underscore)
: "${IAM_ROLE_NAME:=redshift-mcp-execution-role}"
: "${IAM_POLICY_NAME:=redshift-mcp-policy}"
: "${ECR_REPO_NAME:=redshift-mcp-server}"

# ── Redshift ──────────────────────────────────────────────────────────────────
: "${REDSHIFT_CLUSTER_ID:=sample-redshift-cluster-mcp}"
: "${REDSHIFT_DATABASE:=dev}"

# ── Image ─────────────────────────────────────────────────────────────────────
: "${IMAGE_TAG:=latest}"

# ── Paths ─────────────────────────────────────────────────────────────────────
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
IAM_DIR="${PROJECT_ROOT}/iam"

# ── Helpers ───────────────────────────────────────────────────────────────────
log()   { printf "\033[1;34m▶\033[0m %s\n" "$*"; }
ok()    { printf "\033[1;32m✓\033[0m %s\n" "$*"; }
warn()  { printf "\033[1;33m⚠\033[0m %s\n" "$*"; }
err()   { printf "\033[1;31m✗\033[0m %s\n" "$*" >&2; }

require() {
  if ! command -v "$1" >/dev/null 2>&1; then
    err "Required tool not found: $1"
    exit 1
  fi
}

# Resolve account id once and cache
get_account_id() {
  if [ -z "${ACCOUNT_ID:-}" ]; then
    ACCOUNT_ID="$(aws sts get-caller-identity --query Account --output text)"
    export ACCOUNT_ID
  fi
  echo "$ACCOUNT_ID"
}
