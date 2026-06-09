#!/usr/bin/env bash
#
# Print the MCP client config snippet for analysts.
# Looks up the deployed runtime ARN and URL-encodes it for the endpoint.
#
# Usage:
#   ./scripts/get_client_config.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=config.sh
source "${SCRIPT_DIR}/config.sh"

require aws
require jq

RUNTIME_ARN="$(aws bedrock-agentcore-control list-agent-runtimes \
  --region "${AWS_REGION}" \
  --query "agentRuntimes[?agentRuntimeName=='${AGENT_NAME}'].agentRuntimeArn | [0]" \
  --output text 2>/dev/null || echo "None")"

if [ "${RUNTIME_ARN}" = "None" ] || [ -z "${RUNTIME_ARN}" ]; then
  err "No deployed runtime named ${AGENT_NAME} found in ${AWS_REGION}."
  err "Run ./scripts/deploy.sh first."
  exit 1
fi

# URL-encode the ARN for use in the invocation URL
ENCODED_ARN="$(printf '%s' "${RUNTIME_ARN}" | jq -sRr @uri)"
ENDPOINT_URL="https://bedrock-agentcore.${AWS_REGION}.amazonaws.com/runtimes/${ENCODED_ARN}/invocations"

cat <<EOF

Runtime ARN:    ${RUNTIME_ARN}
Endpoint URL:   ${ENDPOINT_URL}

Add the following to your MCP client config:

  • Kiro              ~/.kiro/settings/mcp.json
  • Claude Desktop    ~/Library/Application Support/Claude/claude_desktop_config.json
  • Claude Code       ~/.config/claude-code/mcp.json (or per-project)

────────────────────────────── snip ──────────────────────────────
{
  "mcpServers": {
    "redshift": {
      "command": "sh",
      "args": [
        "-c",
        "DB_USER=\$(aws sts get-caller-identity --query Arn --output text | cut -d'/' -f3) && uvx mcp-proxy-for-aws@latest ${ENDPOINT_URL} --metadata DbUser=\$DB_USER"
      ]
    }
  }
}
────────────────────────────── snip ──────────────────────────────

Analyst daily workflow:
  1. aws login            # opens browser, authenticate via Identity Center
  2. Open MCP client      # tools become available automatically

EOF
