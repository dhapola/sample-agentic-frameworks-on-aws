# Redshift MCP Server container for Amazon Bedrock AgentCore Runtime
# AgentCore requires linux/arm64 images.

FROM public.ecr.aws/docker/library/python:3.12-slim

WORKDIR /app

# Install dependencies first (better layer caching)
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Non-root user (AgentCore best practice)
RUN useradd -m -u 1000 bedrock_agentcore
USER bedrock_agentcore

# AgentCore expects MCP servers on port 8000 at path /mcp
EXPOSE 8000

COPY --chown=bedrock_agentcore:bedrock_agentcore mcp_server.py ./

CMD ["python", "mcp_server.py"]
