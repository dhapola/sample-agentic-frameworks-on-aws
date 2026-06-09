#!/usr/bin/env bash
#
# Smoke-test the deployed runtime by listing tools through mcp-proxy-for-aws.
# Useful right after deploy.sh to verify the runtime is reachable and auth works.
#
# Usage:
#   ./scripts/invoke_test.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=config.sh
source "${SCRIPT_DIR}/config.sh"

require aws
require jq
require uvx

RUNTIME_ARN="$(aws bedrock-agentcore-control list-agent-runtimes \
  --region "${AWS_REGION}" \
  --query "agentRuntimes[?agentRuntimeName=='${AGENT_NAME}'].agentRuntimeArn | [0]" \
  --output text 2>/dev/null || echo "None")"

if [ "${RUNTIME_ARN}" = "None" ] || [ -z "${RUNTIME_ARN}" ]; then
  err "No deployed runtime named ${AGENT_NAME} found."
  exit 1
fi

ENCODED_ARN="$(printf '%s' "${RUNTIME_ARN}" | jq -sRr @uri)"
ENDPOINT_URL="https://bedrock-agentcore.${AWS_REGION}.amazonaws.com/runtimes/${ENCODED_ARN}/invocations"

DB_USER="$(aws sts get-caller-identity --query Arn --output text | awk -F'/' '{print $NF}')"

log "Endpoint:  ${ENDPOINT_URL}"
log "DbUser:    ${DB_USER}"
echo
log "Listing tools via mcp-proxy-for-aws..."
echo

# Send a tools/list request through mcp-proxy-for-aws via stdin
printf '%s\n' \
  '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"invoke_test","version":"1.0"}}}' \
  '{"jsonrpc":"2.0","method":"notifications/initialized"}' \
  '{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}' \
  | uvx mcp-proxy-for-aws@latest \
      "${ENDPOINT_URL}" \
      --metadata "DbUser=${DB_USER}" \
  | tee /dev/stderr \
  | grep -m1 '"id":2' \
  | jq -r '.result.tools[]?.name | "  • " + .'
