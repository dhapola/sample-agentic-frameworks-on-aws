"""Pi-mono agent — CUSTOMIZE THIS FILE.

Dual-process agent harness for Amazon Bedrock AgentCore Runtime.
PID1 (root): this module — lifecycle, credentials, S3 persistence.
PID2 (agent user): pi subprocess — Bedrock-only IAM, restricted filesystem.
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

SNAPSHOT_BUCKET = os.environ.get("SNAPSHOT_BUCKET", "")
PI_HOME = "/home/agent/.pi"
WORKSPACE = "/workspace"
SNAPSHOT_DIRS = [PI_HOME, WORKSPACE]
ALLOWED_RESTORE = (PI_HOME + "/", WORKSPACE + "/")
MODEL_PROVIDER = "amazon-bedrock"
MODEL_ID = "us.anthropic.claude-sonnet-4-6"

# Resolve agent user IDs for privilege drop
try:
    _pw = pwd.getpwnam("agent")
    AGENT_UID, AGENT_GID = _pw.pw_uid, _pw.pw_gid
except KeyError:
    AGENT_UID = AGENT_GID = None
    log.warning("'agent' user not found — pi will run as current user")


# ── AWS Credentials ──────────────────────────────────────────────────────────

PI_ROLE_ARN = os.environ.get("PI_ROLE_ARN", "")
AGENT_NAME = os.environ.get("AGENT_NAME", "pi-mono")


def get_scoped_credentials_env(session_id: str = "") -> dict:
    """Assume a dedicated bedrock-only role for the pi subprocess.

    The RoleSessionName encodes agent name + session for CloudTrail traceability:
        pi-mono--abc123  →  visible in CloudTrail as the caller identity
    """
    if not PI_ROLE_ARN:
        log.warning("PI_ROLE_ARN not set, falling back to self-assume with inline policy")
        return _self_assume_scoped()
    try:
        sts = boto3.client("sts")
        # RoleSessionName: max 64 chars, [a-zA-Z0-9=,.@-] only
        tag = f"{AGENT_NAME}--{session_id[:40]}".replace("/", "-")[:64]
        resp = sts.assume_role(
            RoleArn=PI_ROLE_ARN,
            RoleSessionName=tag,
            DurationSeconds=3600,
        )
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
        with self._lock:
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
                    return msg.get("data", {}).get("text") or ""

    def _handle_ui_request(self, req: dict):
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


# ── S3 Snapshot / Restore ────────────────────────────────────────────────────

s3 = boto3.client("s3") if SNAPSHOT_BUCKET else None


def snapshot_to_s3(session_id: str):
    if not s3:
        return
    prefix = f"{session_id}/"
    count = 0
    for base_dir in SNAPSHOT_DIRS:
        for root, _, files in os.walk(base_dir, followlinks=False):
            for fname in files:
                local = os.path.join(root, fname)
                if os.path.islink(local):
                    log.warning("Skipping symlink in snapshot: %s", local)
                    continue
                key = prefix + os.path.relpath(local, "/")
                try:
                    s3.upload_file(local, SNAPSHOT_BUCKET, key)
                    count += 1
                except Exception as e:
                    log.error("Failed to upload %s: %s", key, e)
    log.info("Snapshot: uploaded %d files to s3://%s/%s", count, SNAPSHOT_BUCKET, prefix)


def restore_from_s3(session_id: str) -> bool:
    if not s3:
        return False
    prefix = f"{session_id}/"
    try:
        resp = s3.list_objects_v2(Bucket=SNAPSHOT_BUCKET, Prefix=prefix, MaxKeys=1)
        if resp.get("KeyCount", 0) == 0:
            return False
    except Exception:
        return False

    log.info("Restoring snapshot for session %s", session_id)
    paginator = s3.get_paginator("list_objects_v2")
    count = 0
    for page in paginator.paginate(Bucket=SNAPSHOT_BUCKET, Prefix=prefix):
        for obj in page.get("Contents", []):
            key = obj["Key"]
            rel = key[len(prefix):]
            local = os.path.realpath("/" + rel)
            if not any(local.startswith(p) for p in ALLOWED_RESTORE):
                log.warning("Blocked restore outside allowed dirs: %s -> %s", key, local)
                continue
            os.makedirs(os.path.dirname(local), exist_ok=True)
            try:
                s3.download_file(SNAPSHOT_BUCKET, key, local)
                count += 1
            except Exception as e:
                log.error("Failed to download %s: %s", key, e)
    log.info("Restored %d files from snapshot", count)
    # Fix ownership so agent user can access restored files
    if AGENT_UID is not None:
        for d in SNAPSHOT_DIRS:
            if os.path.isdir(d):
                os.system(f"chown -R {AGENT_UID}:{AGENT_GID} {d}")
    return True


# ── Agent Entrypoint ─────────────────────────────────────────────────────────

pi = PiRpc()


def handle(session_id: str, prompt: str) -> dict:
    """Called by server.py for every /invocations request.

    Args:
        session_id: The runtime session ID (from AgentCore header).
        prompt: The user's prompt string.

    Returns:
        {"result": "..."} on success, {"error": "..."} on failure.
    """
    if not pi.alive:
        restored = restore_from_s3(session_id)
        pi.start(continue_session=restored, session_id=session_id)

    result = pi.prompt(prompt)
    t = threading.Thread(target=snapshot_to_s3, args=(session_id,))
    t.start()
    t.join(timeout=120)
    if t.is_alive():
        log.warning("Snapshot still running after 120s, proceeding")
    return {"result": result}
