"""Pi-mono agent — CUSTOMIZE THIS FILE.

Dual-process agent harness for Amazon Bedrock AgentCore Runtime.
PID1 (root): this module — lifecycle, credentials, S3 persistence, observability.
PID2 (agent user): pi subprocess — Bedrock-only IAM, restricted filesystem.

Look for sections marked with:
    # ══════════════════════════════════════════════════════════════════════════
    # CUSTOMIZE: ...
    # ══════════════════════════════════════════════════════════════════════════
"""

import json
import logging
import os
import pwd
import subprocess
import threading

import boto3
import botocore.session

log = logging.getLogger("pi-agent")

# ── Configuration ────────────────────────────────────────────────────────────

SNAPSHOT_BUCKET = os.environ.get("SNAPSHOT_BUCKET", "")
PI_HOME = "/home/agent/.pi"
WORKSPACE = "/workspace"
SNAPSHOT_DIRS = [PI_HOME, WORKSPACE]
ALLOWED_RESTORE = (PI_HOME + "/", WORKSPACE + "/")

# ══════════════════════════════════════════════════════════════════════════════
# CUSTOMIZE: Model configuration
# Change the model ID to use a different Bedrock model.
# ══════════════════════════════════════════════════════════════════════════════
MODEL_PROVIDER = "amazon-bedrock"
MODEL_ID = "us.anthropic.claude-sonnet-4-6"

# ══════════════════════════════════════════════════════════════════════════════
# CUSTOMIZE: AgentCore Memory configuration
# Set MEMORY_ID to enable persistent memory across sessions.
# When set, conversation turns are stored as events and relevant long-term
# memories are retrieved before each prompt (replacing S3 for history).
# ══════════════════════════════════════════════════════════════════════════════
MEMORY_ID = os.environ.get("MEMORY_ID", "")

# ══════════════════════════════════════════════════════════════════════════════
# CUSTOMIZE: AgentCore Gateway configuration
# Set GATEWAY_URL to enable external tool discovery and invocation via MCP.
# The agent will list available tools from the gateway and can invoke them
# to enrich context before responding.
# ══════════════════════════════════════════════════════════════════════════════
GATEWAY_URL = os.environ.get("GATEWAY_URL", "")

# Resolve agent user IDs for privilege drop
try:
    _pw = pwd.getpwnam("agent")
    AGENT_UID, AGENT_GID = _pw.pw_uid, _pw.pw_gid
except KeyError:
    AGENT_UID = AGENT_GID = None
    log.warning("'agent' user not found — pi will run as current user")


# ── Observability (OpenTelemetry) ────────────────────────────────────────────

OTEL_ENABLED = os.environ.get("OTEL_ENABLED", "false").lower() == "true"

if OTEL_ENABLED:
    from opentelemetry import trace
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.trace import StatusCode

    resource = Resource.create({"service.name": "pi-mono-agent"})
    provider = TracerProvider(resource=resource)
    # AgentCore provides an OTLP-compatible collector sidecar on localhost:4317
    exporter = OTLPSpanExporter(endpoint=os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317"), insecure=True)
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)
    tracer = trace.get_tracer("pi-mono-agent")
    log.info("OpenTelemetry tracing enabled → OTLP exporter")
else:
    # No-op tracer — zero overhead when disabled
    from contextlib import contextmanager

    class _NoOpSpan:
        def set_attribute(self, *a, **kw): pass
        def set_status(self, *a, **kw): pass
        def record_exception(self, *a, **kw): pass

    @contextmanager
    def _noop_span(*a, **kw):
        yield _NoOpSpan()

    class _NoOpTracer:
        def start_as_current_span(self, *a, **kw): return _noop_span()

    tracer = _NoOpTracer()


# ── AWS Credentials ──────────────────────────────────────────────────────────

PI_ROLE_ARN = os.environ.get("PI_ROLE_ARN", "")
AGENT_NAME = os.environ.get("AGENT_NAME", "pi-mono")


def get_scoped_credentials_env(session_id: str = "") -> dict:
    """Assume a dedicated bedrock-only role for the pi subprocess.

    The RoleSessionName encodes agent name + session for CloudTrail traceability:
        pi-mono--abc123  →  visible in CloudTrail as the caller identity

    ══════════════════════════════════════════════════════════════════════════════
    CUSTOMIZE: If your agent needs additional AWS permissions beyond Bedrock,
    either create a dedicated role (set PI_ROLE_ARN env var) or modify the
    inline policy in _self_assume_scoped() below.
    ══════════════════════════════════════════════════════════════════════════════
    """
    if not PI_ROLE_ARN:
        log.warning("PI_ROLE_ARN not set, falling back to self-assume with inline policy")
        return _self_assume_scoped()
    try:
        sts = boto3.client("sts")
        tag = f"{AGENT_NAME}--{session_id[:40]}".replace("/", "-")[:64]
        resp = sts.assume_role(RoleArn=PI_ROLE_ARN, RoleSessionName=tag, DurationSeconds=3600)
        c = resp["Credentials"]
        log.info("Assumed pi role: %s (session: %s)", PI_ROLE_ARN, tag)
        return {
            "AWS_ACCESS_KEY_ID": c["AccessKeyId"],
            "AWS_SECRET_ACCESS_KEY": c["SecretAccessKey"],
            "AWS_SESSION_TOKEN": c["SessionToken"],
        }
    except Exception as e:
        log.warning("Failed to assume pi role, falling back to self-assume: %s", e)
        return _self_assume_scoped()


def _self_assume_scoped() -> dict:
    """Fallback: self-assume the execution role with an inline policy restricting to bedrock only."""
    try:
        sts = boto3.client("sts")
        arn = sts.get_caller_identity()["Arn"]
        parts = arn.split(":")
        role_name = parts[5].split("/")[1]
        role_arn = f"arn:aws:iam::{parts[4]}:role/{role_name}"
        resp = sts.assume_role(
            RoleArn=role_arn,
            RoleSessionName=f"{AGENT_NAME}-fallback"[:64],
            DurationSeconds=3600,
            Policy=json.dumps({
                "Version": "2012-10-17",
                "Statement": [{
                    "Effect": "Allow",
                    "Action": ["bedrock:InvokeModel", "bedrock:InvokeModelWithResponseStream"],
                    "Resource": "*",
                }],
            }),
        )
        c = resp["Credentials"]
        log.info("Self-assumed with inline policy (bedrock-only fallback)")
        return {
            "AWS_ACCESS_KEY_ID": c["AccessKeyId"],
            "AWS_SECRET_ACCESS_KEY": c["SecretAccessKey"],
            "AWS_SESSION_TOKEN": c["SessionToken"],
        }
    except Exception as e:
        log.warning("Self-assume failed, falling back to inherited creds: %s", e)
        return _get_inherited_credentials_env()


def _get_inherited_credentials_env() -> dict:
    """Fallback: resolve credentials from boto3 chain (local dev)."""
    session = botocore.session.get_session()
    creds = session.get_credentials()
    if not creds:
        log.warning("No AWS credentials found via boto3")
        return {}
    resolved = creds.get_frozen_credentials()
    env = {"AWS_ACCESS_KEY_ID": resolved.access_key, "AWS_SECRET_ACCESS_KEY": resolved.secret_key}
    if resolved.token:
        env["AWS_SESSION_TOKEN"] = resolved.token
    return env


# ── Pi RPC Client ────────────────────────────────────────────────────────────
# ══════════════════════════════════════════════════════════════════════════════
# CUSTOMIZE: Replace this class entirely if you're using a different agent.
# The only requirement is that your agent has a method that takes a string
# prompt and returns a string response.
# ══════════════════════════════════════════════════════════════════════════════

class PiRpc:
    """Manages a long-running pi RPC subprocess."""

    def __init__(self):
        self.proc: subprocess.Popen | None = None
        self._lock = threading.Lock()

    @property
    def alive(self) -> bool:
        return self.proc is not None and self.proc.poll() is None

    def start(self, continue_session: bool = False, session_id: str = ""):
        if self.alive:
            return
        env = {
            "HOME": "/home/agent",
            "USER": "agent",
            "PATH": os.environ.get("PATH", "/usr/local/bin:/usr/bin:/bin"),
            "AWS_REGION": os.environ.get("AWS_REGION", "us-east-1"),
        }
        env.update(get_scoped_credentials_env(session_id))
        cmd = ["pi", "--mode", "rpc", "--provider", MODEL_PROVIDER, "--model", MODEL_ID]
        if continue_session:
            cmd.append("--continue")

        def _demote():
            if AGENT_UID is not None:
                os.setgid(AGENT_GID)
                os.setuid(AGENT_UID)

        log.info("Starting pi RPC process (continue=%s)", continue_session)
        self.proc = subprocess.Popen(
            cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            env=env, cwd=WORKSPACE, text=True, bufsize=1,
            preexec_fn=_demote,
        )
        log.info("pi RPC started (pid=%s, uid=agent)", self.proc.pid)

    def send(self, cmd: dict):
        self.proc.stdin.write(json.dumps(cmd, separators=(",", ":")) + "\n")
        self.proc.stdin.flush()

    def read_line(self) -> dict | None:
        line = self.proc.stdout.readline()
        if not line:
            return None
        line = line.strip()
        if not line:
            return None
        try:
            return json.loads(line)
        except json.JSONDecodeError:
            log.warning("Non-JSON line from pi: %s", line[:200])
            return {"_raw": line}

    def prompt(self, message: str) -> str:
        """Send a prompt to pi and return the assistant's response text."""
        with self._lock:
            with tracer.start_as_current_span("pi.prompt") as span:
                span.set_attribute("prompt.length", len(message))
                self.send({"type": "prompt", "message": message})
                while True:
                    msg = self.read_line()
                    if msg is None:
                        raise RuntimeError("pi process closed stdout unexpectedly")
                    msg_type = msg.get("type", "")
                    if msg_type == "extension_ui_request":
                        self._handle_ui_request(msg)
                        continue
                    if msg_type == "agent_end":
                        break
                    if msg_type == "response" and msg.get("success") is False:
                        raise RuntimeError(f"pi RPC error: {msg.get('error', 'unknown')}")

                self.send({"type": "get_last_assistant_text"})
                while True:
                    msg = self.read_line()
                    if msg is None:
                        raise RuntimeError("pi closed stdout while reading assistant text")
                    if msg.get("type") == "response" and msg.get("command") == "get_last_assistant_text":
                        text = msg.get("data", {}).get("text") or ""
                        span.set_attribute("response.length", len(text))
                        return text

    def _handle_ui_request(self, req: dict):
        """Auto-accept all UI confirmation requests from pi."""
        req_id = req.get("id", "")
        if not req_id:
            return
        method = req.get("method", "")
        if method == "confirm":
            self.send({"type": "extension_ui_response", "id": req_id, "confirmed": True})
        elif method == "select":
            options = req.get("options", [])
            self.send({"type": "extension_ui_response", "id": req_id, "value": options[0] if options else ""})
        elif method == "input":
            self.send({"type": "extension_ui_response", "id": req_id, "value": ""})


# ── AgentCore Memory ─────────────────────────────────────────────────────────

_memory_client = None


def _get_memory_client():
    global _memory_client
    if _memory_client is None:
        _memory_client = boto3.client("bedrock-agentcore", region_name=os.environ.get("AWS_REGION", "us-east-1"))
    return _memory_client


def memory_store_turn(session_id: str, user_msg: str, assistant_msg: str):
    """Store a conversation turn as a Memory event (short-term)."""
    if not MEMORY_ID:
        return
    try:
        import time as _time
        _get_memory_client().create_event(
            memoryId=MEMORY_ID,
            actorId=session_id,
            sessionId=session_id,
            eventTimestamp=int(_time.time()),
            payload=[
                {"conversational": {"role": "USER", "content": {"text": user_msg}}},
                {"conversational": {"role": "ASSISTANT", "content": {"text": assistant_msg}}},
            ],
        )
        log.info("Memory: stored turn for session %s", session_id)
    except Exception as e:
        log.warning("Memory: failed to store turn: %s", e)


def memory_retrieve_context(session_id: str, query: str) -> str:
    """Retrieve relevant long-term memories as context prefix."""
    if not MEMORY_ID:
        return ""
    try:
        resp = _get_memory_client().retrieve_memory_records(
            memoryId=MEMORY_ID,
            namespace=f"users/{session_id}/facts",
            searchCriteria={"searchQuery": query, "topK": 5},
        )
        records = resp.get("memoryRecordSummaries", [])
        if not records:
            return ""
        context = "\n".join(r.get("content", {}).get("text", "") for r in records if r.get("content"))
        log.info("Memory: retrieved %d records for context", len(records))
        return f"[Relevant memories]\n{context}\n\n"
    except Exception as e:
        log.warning("Memory: failed to retrieve context: %s", e)
        return ""


# ── AgentCore Gateway ────────────────────────────────────────────────────────

_gateway_tools_cache: list | None = None


def gateway_list_tools() -> list:
    """List available tools from the AgentCore Gateway (cached)."""
    global _gateway_tools_cache
    if not GATEWAY_URL:
        return []
    if _gateway_tools_cache is not None:
        return _gateway_tools_cache
    try:
        client = boto3.client("bedrock-agentcore", region_name=os.environ.get("AWS_REGION", "us-east-1"))
        resp = client.invoke_gateway(
            gatewayUrl=GATEWAY_URL,
            method="tools/list",
            body="{}",
        )
        tools = json.loads(resp.get("body", "{}")).get("tools", [])
        _gateway_tools_cache = tools
        log.info("Gateway: discovered %d tools", len(tools))
        return tools
    except Exception as e:
        log.warning("Gateway: failed to list tools: %s", e)
        return []


def gateway_invoke_tool(tool_name: str, arguments: dict) -> str:
    """Invoke a tool via the AgentCore Gateway."""
    if not GATEWAY_URL:
        return ""
    try:
        client = boto3.client("bedrock-agentcore", region_name=os.environ.get("AWS_REGION", "us-east-1"))
        resp = client.invoke_gateway(
            gatewayUrl=GATEWAY_URL,
            method="tools/call",
            body=json.dumps({"name": tool_name, "arguments": arguments}),
        )
        return json.loads(resp.get("body", "{}")).get("content", [{}])[0].get("text", "")
    except Exception as e:
        log.warning("Gateway: tool invocation failed (%s): %s", tool_name, e)
        return f"[Tool error: {e}]"


# ── S3 Snapshot / Restore ────────────────────────────────────────────────────

s3 = boto3.client("s3") if SNAPSHOT_BUCKET else None


def snapshot_to_s3(session_id: str):
    """Upload session state to S3 for persistence across container recycling."""
    if not s3:
        return
    with tracer.start_as_current_span("s3.snapshot") as span:
        span.set_attribute("session_id", session_id)
        prefix = f"{session_id}/"
        count = 0
        for base_dir in SNAPSHOT_DIRS:
            for root, _, files in os.walk(base_dir, followlinks=False):
                for fname in files:
                    local = os.path.join(root, fname)
                    if os.path.islink(local):
                        continue
                    key = prefix + os.path.relpath(local, "/")
                    try:
                        s3.upload_file(local, SNAPSHOT_BUCKET, key)
                        count += 1
                    except Exception as e:
                        log.error("Failed to upload %s: %s", key, e)
        span.set_attribute("files_uploaded", count)
        log.info("Snapshot: uploaded %d files to s3://%s/%s", count, SNAPSHOT_BUCKET, prefix)


def restore_from_s3(session_id: str) -> bool:
    """Restore session state from S3 on cold start."""
    if not s3:
        return False
    with tracer.start_as_current_span("s3.restore") as span:
        span.set_attribute("session_id", session_id)
        try:
            resp = s3.list_objects_v2(Bucket=SNAPSHOT_BUCKET, Prefix=f"{session_id}/", MaxKeys=1)
            if resp.get("KeyCount", 0) == 0:
                return False
        except Exception:
            return False

        log.info("Restoring snapshot for session %s", session_id)
        prefix = f"{session_id}/"
        paginator = s3.get_paginator("list_objects_v2")
        count = 0
        for page in paginator.paginate(Bucket=SNAPSHOT_BUCKET, Prefix=prefix):
            for obj in page.get("Contents", []):
                key = obj["Key"]
                rel = key[len(prefix):]
                local = os.path.realpath("/" + rel)
                # Security: only restore to allowed directories
                if not any(local.startswith(p) for p in ALLOWED_RESTORE):
                    log.warning("Blocked restore outside allowed dirs: %s -> %s", key, local)
                    continue
                os.makedirs(os.path.dirname(local), exist_ok=True)
                try:
                    s3.download_file(SNAPSHOT_BUCKET, key, local)
                    count += 1
                except Exception as e:
                    log.error("Failed to download %s: %s", key, e)
        span.set_attribute("files_restored", count)
        log.info("Restored %d files from snapshot", count)
        # Fix ownership so agent user can access restored files
        if AGENT_UID is not None:
            for d in SNAPSHOT_DIRS:
                if os.path.isdir(d):
                    os.system(f"chown -R {AGENT_UID}:{AGENT_GID} {d}")
        return True


# ── Agent Entrypoint ─────────────────────────────────────────────────────────
# ══════════════════════════════════════════════════════════════════════════════
# CUSTOMIZE: This is the main function called by server.py for every request.
# Modify this to add pre/post processing, context enrichment, RAG, guardrails,
# or replace the pi RPC entirely with your own agent logic.
# ══════════════════════════════════════════════════════════════════════════════

pi = PiRpc()


def handle(session_id: str, prompt: str) -> dict:
    """Called by server.py for every /invocations request.

    Args:
        session_id: The runtime session ID (from AgentCore header).
        prompt: The user's prompt string.

    Returns:
        {"result": "..."} on success, {"error": "..."} on failure.
    """
    with tracer.start_as_current_span("agent.handle") as span:
        span.set_attribute("session_id", session_id)
        span.set_attribute("prompt.length", len(prompt))

        try:
            # Start pi subprocess if not already running (cold start)
            if not pi.alive:
                restored = restore_from_s3(session_id)
                pi.start(continue_session=restored, session_id=session_id)

            # ── PRE-PROCESSING: Memory retrieval + Gateway tool context ───────
            enriched_prompt = prompt
            # Retrieve relevant long-term memories
            mem_context = memory_retrieve_context(session_id, prompt)
            if mem_context:
                enriched_prompt = mem_context + prompt
            # Inject available gateway tools as context (first turn only)
            if GATEWAY_URL and not hasattr(pi, '_tools_injected'):
                tools = gateway_list_tools()
                if tools:
                    tool_names = [t.get("name", "") for t in tools]
                    enriched_prompt = (
                        f"[Available external tools via Gateway: {', '.join(tool_names)}]\n\n"
                        + enriched_prompt
                    )
                    pi._tools_injected = True

            result = pi.prompt(enriched_prompt)

            # ── POST-PROCESSING: Store turn in Memory ─────────────────────────
            memory_store_turn(session_id, prompt, result)

            # Snapshot session state to S3 (async, non-blocking)
            t = threading.Thread(target=snapshot_to_s3, args=(session_id,))
            t.start()
            t.join(timeout=120)
            if t.is_alive():
                log.warning("Snapshot still running after 120s, proceeding")

            span.set_attribute("response.length", len(result))
            return {"result": result}

        except Exception as e:
            span.record_exception(e)
            if OTEL_ENABLED:
                from opentelemetry.trace import StatusCode
                span.set_status(StatusCode.ERROR, str(e))
            log.error("Agent error: %s", e)
            return {"error": str(e)}
