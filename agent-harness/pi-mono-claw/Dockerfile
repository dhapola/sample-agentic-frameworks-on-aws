FROM node:20-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 python3-pip git ripgrep ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install pi coding agent globally
RUN npm install -g @mariozechner/pi-coding-agent

# Create restricted agent user for pi subprocess
RUN useradd -m -s /bin/bash -d /home/agent agent

# Pre-create directories owned by agent
RUN mkdir -p /workspace /home/agent/.pi/agent \
    && chown -R agent:agent /workspace /home/agent/.pi

WORKDIR /app
COPY requirements.txt .
RUN pip3 install --no-cache-dir --break-system-packages -r requirements.txt
COPY server.py agent.py ./

# Lock /app — root-owned, no read/exec for others
RUN chmod 700 /app

ENV AWS_REGION=us-east-1
ENV SNAPSHOT_BUCKET=""
ENV PI_ROLE_ARN=""
ENV OTEL_ENABLED="false"
ENV MEMORY_ID=""
ENV GATEWAY_URL=""

EXPOSE 8080
CMD ["python3", "-m", "uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8080"]
