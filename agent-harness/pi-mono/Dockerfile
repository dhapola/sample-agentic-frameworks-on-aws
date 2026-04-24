FROM ubuntu:22.04

RUN apt-get update && apt-get install -y \
    curl python3 python3-pip git ripgrep \
    && rm -rf /var/lib/apt/lists/*

# Node.js 20 + pi via npm (POC path; production uses Bun binary)
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && npm install -g @mariozechner/pi-coding-agent

# Create restricted agent user for pi subprocess
RUN useradd -m -s /bin/bash -d /home/agent agent

# Pre-create directories owned by agent
RUN mkdir -p /workspace /home/agent/.pi/agent \
    && chown -R agent:agent /workspace /home/agent/.pi

WORKDIR /app
COPY requirements.txt .
RUN pip3 install -r requirements.txt
COPY server.py agent.py ./

# Lock /app — root-owned, no read/exec for others
RUN chmod 700 /app

ENV AWS_REGION=us-east-1
ENV SNAPSHOT_BUCKET=""
ENV PI_ROLE_ARN=""

EXPOSE 8080
CMD ["python3", "-m", "uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8080"]
