#!/usr/bin/env bash
#
# Tail CloudWatch logs for the deployed AgentCore runtime.
#
# Usage:
#   ./scripts/tail_logs.sh             # follow last 5 minutes onward
#   ./scripts/tail_logs.sh 1h          # follow last 1 hour onward

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=config.sh
source "${SCRIPT_DIR}/config.sh"

require aws

SINCE="${1:-5m}"

RUNTIME_ID="$(aws bedrock-agentcore-control list-agent-runtimes \
  --region "${AWS_REGION}" \
  --query "agentRuntimes[?agentRuntimeName=='${AGENT_NAME}'].agentRuntimeId | [0]" \
  --output text 2>/dev/null || echo "None")"

if [ "${RUNTIME_ID}" = "None" ] || [ -z "${RUNTIME_ID}" ]; then
  err "No deployed runtime named ${AGENT_NAME} found."
  exit 1
fi

LOG_GROUP="/aws/bedrock-agentcore/runtimes/${RUNTIME_ID}-DEFAULT"

log "Tailing log group: ${LOG_GROUP}"
log "Since: ${SINCE}    (Ctrl+C to stop)"
echo

aws logs tail "${LOG_GROUP}" \
  --region "${AWS_REGION}" \
  --since "${SINCE}" \
  --follow \
  --format short
