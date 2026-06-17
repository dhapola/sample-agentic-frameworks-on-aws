#!/usr/bin/env python3
"""
Batch evaluation client for the Java agent deployed in AgentCore.
Uses WebSocket streaming via bedrock-agentcore SDK for real-time output.

Mirrors the logic of Application.java:
- Reads transaction logs from workdir/evaluation-dataset/
- Connects to deployed agent via AgentCore WebSocket (/ws)
- Streams response text to console as it arrives
- Calculates cost and writes results to workdir/evaluation_results.csv

Usage:
  python agentcore_client.py

Environment variables:
  AGENT_RUNTIME_ARN  - override the agent runtime ARN (default: from deployment_info.json)
  AWS_REGION         - override region (default: from deployment_info.json)
  WORKDIR            - path to workdir (default: ../workdir)
"""

import asyncio
import csv
import json
import os
import sys
import time
from pathlib import Path

import websockets
from bedrock_agentcore.runtime import AgentCoreRuntimeClient

# --- Configuration ---

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent  # txn-analysis-agent/
DEPLOYMENT_INFO_FILE = PROJECT_ROOT / "deploy-in-agentcore" / "deployment_info.json"
WORKDIR = Path(os.environ.get("WORKDIR", PROJECT_ROOT / "workdir"))
EVALUATION_DATASET_DIR = WORKDIR / "evaluation-dataset"
OUTPUT_CSV = WORKDIR / "evaluation_results.csv"

TRANSACTION_IDS = ["txn_001", "txn_002", "txn_003", "txn_004", "txn_005"]

# Model pricing for ap-south-1 (USD per 1M tokens): {model_id: (input_price, output_price)}
MODEL_PRICING = {
    "global.anthropic.claude-haiku-4-5-20251001-v1:0": (1.00, 5.00),
    "apac.anthropic.claude-sonnet-4-20250514-v1:0": (3.00, 15.00),
    "global.anthropic.claude-sonnet-4-6": (3.00, 15.00),
    "global.anthropic.claude-opus-4-8": (5.00, 25.00),
    "apac.amazon.nova-pro-v1:0": (1.48, 1.48),
    "deepseek.v3-v1:0": (0.682424, 1.976678),
    "deepseek.v3.2": (0.74, 2.22),
    "minimax.minimax-m2.5": (0.36, 1.44),
    "moonshotai.kimi-k2.5": (0.72, 3.60),
    "qwen.qwen3-next-80b-a3b": (0.18, 1.41),
    "zai.glm-5": (1.20, 3.84),
}


def load_deployment():
    arn = os.environ.get("AGENT_RUNTIME_ARN")
    region = os.environ.get("AWS_REGION")
    if arn:
        return arn, region or "ap-south-1"
    if DEPLOYMENT_INFO_FILE.exists():
        info = json.loads(DEPLOYMENT_INFO_FILE.read_text())
        return info["agentRuntimeArn"], region or info.get("region", "ap-south-1")
    sys.exit(
        "No agent runtime ARN found. Run deploy.py first, or set AGENT_RUNTIME_ARN."
    )


def calculate_cost(model_id, input_tokens, output_tokens):
    pricing = MODEL_PRICING.get(model_id)
    if not pricing:
        return 0.0
    return (input_tokens / 1_000_000) * pricing[0] + (output_tokens / 1_000_000) * pricing[1]


async def invoke_agent_streaming(runtime_client, arn, transaction_id, log_data, model_id):
    """
    Connect via WebSocket to the deployed agent, send payload, stream response.
    Returns (response_text, metadata).
    """
    ws_url, headers = runtime_client.generate_ws_connection(
        runtime_arn=arn,
        endpoint_name="DEFAULT",
    )

    payload = json.dumps({
        "transaction_id": transaction_id,
        "log_data": log_data,
        "model_id": model_id,
    })

    response_chunks = []
    metadata = {}

    async with websockets.connect(ws_url, additional_headers=headers) as ws:
        await ws.send(payload)

        async for message in ws:
            try:
                data = json.loads(message)
                if data.get("done"):
                    metadata = data
                elif "text" in data:
                    chunk = data["text"]
                    print(chunk, end="", flush=True)
                    response_chunks.append(chunk)
                elif "error" in data:
                    print(f"\n  [ERROR from agent] {data['error']}", flush=True)
                    break
                else:
                    # Unknown frame, print raw
                    print(message, end="", flush=True)
                    response_chunks.append(message)
            except json.JSONDecodeError:
                print(message, end="", flush=True)
                response_chunks.append(message)

    print()  # newline after streaming
    return "".join(response_chunks), metadata


def write_csv_header_if_needed():
    if not OUTPUT_CSV.exists():
        with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                "transaction_id", "input_log", "output_response",
                "model_id", "latency", "input_tokens", "output_tokens", "total_cost"
            ])


def append_csv_row(transaction_id, input_log, output_response, model_id, latency_ms, input_tokens, output_tokens, total_cost):
    with open(OUTPUT_CSV, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            transaction_id, input_log, output_response,
            model_id, latency_ms, input_tokens, output_tokens, f"{total_cost:.6f}"
        ])


async def main():
    arn, region = load_deployment()
    runtime_client = AgentCoreRuntimeClient(region=region)

    print(f"Agent ARN: {arn}")
    print(f"Region: {region}")
    print(f"Workdir: {WORKDIR}")
    print(f"Models: {len(MODEL_PRICING)}")
    print(f"Transactions: {len(TRANSACTION_IDS)}")
    print(f"Output CSV: {OUTPUT_CSV}")
    print()

    write_csv_header_if_needed()

    for model_id in MODEL_PRICING:
        print(f"--- Evaluating model: {model_id} ---")
        for txn_id in TRANSACTION_IDS:
            log_file = EVALUATION_DATASET_DIR / f"{txn_id}.log"
            if not log_file.exists():
                print(f"  [SKIP] Log file not found: {log_file}")
                continue

            log_data = log_file.read_text(encoding="utf-8")

            try:
                print(f"\n  [{model_id} | {txn_id}] ", end="", flush=True)
                start = time.time()

                response_text, metadata = await invoke_agent_streaming(
                    runtime_client, arn, txn_id, log_data, model_id
                )

                elapsed_ms = int((time.time() - start) * 1000)
                latency_ms = metadata.get("latency_ms", elapsed_ms)
                input_tokens = metadata.get("input_tokens", 0)
                output_tokens = metadata.get("output_tokens", 0)
                returned_model = metadata.get("model_id", model_id)

                total_cost = calculate_cost(returned_model, input_tokens, output_tokens)

                print(f"  => {latency_ms}ms, {input_tokens}+{output_tokens} tokens, ${total_cost:.6f}")

                append_csv_row(
                    txn_id, log_data, response_text,
                    returned_model, latency_ms, input_tokens, output_tokens, total_cost
                )

            except Exception as e:
                print(f"FAILED: {e}")

    print(f"\nAll evaluations complete. Results written to: {OUTPUT_CSV}")


if __name__ == "__main__":
    asyncio.run(main())
