"""FastMCP Redshift server — stateless Streamable HTTP (MCP 2025-06-18).

End-user Redshift SQL credentials arrive per request in the
X-Redshift-User / X-Redshift-Password headers. The server is stateless
(stateless_http=True) and delegates all authorization to Redshift's native RBAC.
Run with:  uvicorn server:app --host 0.0.0.0 --port 8080
"""
from __future__ import annotations

import json
import logging
import logging.handlers
import os
import time
from datetime import datetime, timezone

import anyio
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from fastmcp.server.dependencies import get_http_headers
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse, Response

import redshift as rs

RS_HOST = os.environ["RS_HOST"]
RS_PORT = int(os.getenv("RS_PORT", "5439"))
RS_DB = os.environ["RS_DB"]
ROW_CAP = int(os.getenv("QUERY_ROW_CAP", "1000"))
ALLOWED_ORIGINS = {o for o in os.getenv("ALLOWED_ORIGINS", "").split(",") if o}
LOG_FILE = os.getenv("LOG_FILE", "/var/log/redshift-mcp/app.log")


class _JsonFormatter(logging.Formatter):
    """One JSON object per line — parsed automatically by CloudWatch Logs Insights."""
    def format(self, record):
        entry = {
            "time": datetime.fromtimestamp(record.created, timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "event": record.getMessage(),
        }
        entry.update(getattr(record, "fields", {}))
        if record.exc_info:
            entry["exception"] = self.formatException(record.exc_info)
        return json.dumps(entry, default=str)


def _setup_logging():
    d = os.path.dirname(LOG_FILE)
    if d:
        os.makedirs(d, exist_ok=True)
    handler = logging.handlers.WatchedFileHandler(LOG_FILE)  # reopens after logrotate
    handler.setFormatter(_JsonFormatter())
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.handlers = [handler]
    # Send uvicorn's own logs to the same JSON file (no split to stderr/journald).
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        lg = logging.getLogger(name)
        lg.handlers = [handler]
        lg.propagate = False


_setup_logging()
log = logging.getLogger("redshift_mcp")

MGR = rs.ConnectionManager(
    host=RS_HOST, port=RS_PORT, db=RS_DB,
    max_idle=int(os.getenv("POOL_MAX_IDLE", "4")),
    idle_ttl=int(os.getenv("POOL_IDLE_TTL", "300")),
    stmt_timeout_ms=int(os.getenv("STATEMENT_TIMEOUT_MS", "30000")),
)

mcp = FastMCP("redshift-mcp")
log.info("startup", extra={"fields": {
    "rs_host": RS_HOST, "rs_db": RS_DB, "rs_port": RS_PORT,
    "row_cap": ROW_CAP, "log_file": LOG_FILE}})


def _creds():
    h = get_http_headers()  # lowercase keys; includes custom headers by default
    user, pwd = h.get("x-redshift-user"), h.get("x-redshift-password")
    if not (user and pwd):
        raise ToolError("missing Redshift credentials "
                        "(X-Redshift-User / X-Redshift-Password headers)")
    return user, pwd


def _blocking(user, pwd, fn):
    try:
        key, conn = MGR.acquire(user, pwd)
    except rs.AuthError as e:
        raise ToolError(str(e))
    broken = False
    try:
        return fn(conn)
    except rs.QueryRejected as e:
        raise ToolError(str(e))
    except Exception as e:  # SQL / permission error from Redshift
        broken = True
        raise ToolError(str(e))
    finally:
        MGR.release(key, conn, broken=broken)


async def _run(label, fn):
    """Resolve credentials, run blocking DB work off the loop, log the outcome.

    The SQL username is logged for audit; the password is never logged.
    """
    t0 = time.monotonic()
    try:
        user, pwd = _creds()
    except ToolError:
        log.warning("tool_call", extra={"fields": {"tool": label, "status": "missing_credentials"}})
        raise
    try:
        result = await anyio.to_thread.run_sync(_blocking, user, pwd, fn)
    except ToolError as e:
        log.warning("tool_call", extra={"fields": {
            "tool": label, "user": user, "status": "error", "error": str(e),
            "duration_ms": round((time.monotonic() - t0) * 1000)}})
        raise
    log.info("tool_call", extra={"fields": {
        "tool": label, "user": user, "status": "ok",
        "duration_ms": round((time.monotonic() - t0) * 1000)}})
    return result


@mcp.tool
async def list_schemas() -> dict:
    """List schemas visible to the calling user."""
    cols, rows = await _run("list_schemas", rs.list_schemas)
    return {"columns": cols, "rows": rows}


@mcp.tool
async def list_tables(schema: str) -> dict:
    """List tables in a schema."""
    cols, rows = await _run("list_tables", lambda c: rs.list_tables(c, schema))
    return {"columns": cols, "rows": rows}


@mcp.tool
async def describe_table(schema: str, table: str) -> dict:
    """List columns of a table."""
    cols, rows = await _run("describe_table", lambda c: rs.describe_table(c, schema, table))
    return {"columns": cols, "rows": rows}


@mcp.tool
async def run_query(sql: str) -> dict:
    """Run a read-only SQL query (SELECT/WITH/SHOW/EXPLAIN)."""
    cols, rows, truncated = await _run("run_query", lambda c: rs.run_query(c, sql, ROW_CAP))
    return {"columns": cols, "rows": rows, "truncated": truncated}


@mcp.custom_route("/healthz", methods=["GET"])
async def healthz(request):
    return JSONResponse({"status": "ok"})


class _OriginCheck(BaseHTTPMiddleware):
    """Validate Origin to defend against DNS-rebinding (MCP transport requirement)."""
    async def dispatch(self, request, call_next):
        origin = request.headers.get("origin")
        if origin is not None and origin not in ALLOWED_ORIGINS:
            return Response(status_code=403)
        return await call_next(request)


# Stateless ASGI app: any replica/worker serves any request (no Mcp-Session-Id).
app = mcp.http_app(path="/mcp", stateless_http=True,
                   middleware=[Middleware(_OriginCheck)])
