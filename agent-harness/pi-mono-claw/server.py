"""AgentCore Runtime HTTP server — DO NOT MODIFY.

Implements the AgentCore HTTP contract (POST /invocations, GET /ping) on port 8080.
Delegates all agent logic to agent.handle(). The only coupling is that function signature.
"""

import asyncio
import logging
import sys
import time

logging.basicConfig(level=logging.INFO, stream=sys.stdout, format="%(asctime)s %(name)s %(levelname)s %(message)s")

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import uvicorn

from agent import handle

log = logging.getLogger("agentcore-server")

SESSION_ID_HEADER = "x-amzn-bedrock-agentcore-runtime-session-id"

_last_activity: float = 0.0
_processing: bool = False

app = FastAPI()


def _invoke(session_id: str, prompt: str) -> dict:
    global _processing, _last_activity
    _processing = True
    _last_activity = time.time()
    try:
        return handle(session_id, prompt)
    except Exception as e:
        log.error("Agent error: %s", e)
        return {"error": str(e)}
    finally:
        _processing = False
        _last_activity = time.time()


@app.post("/invocations")
async def invoke(request: Request):
    session_id = request.headers.get(SESSION_ID_HEADER, "default")
    body = await request.json()
    prompt = body.get("prompt", "")
    if not prompt:
        return JSONResponse({"error": "No prompt provided"}, status_code=400)
    log.info("Invocation: session=%s prompt=%s", session_id, prompt[:100])
    result = await asyncio.to_thread(_invoke, session_id, prompt)
    return JSONResponse(result)


@app.get("/ping")
async def ping():
    status = "HealthyBusy" if _processing else "Healthy"
    return {"status": status, "time_of_last_update": int(_last_activity or time.time())}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)
