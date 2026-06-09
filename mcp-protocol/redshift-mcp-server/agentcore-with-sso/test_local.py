"""
Local integration test for the Redshift MCP server.

Usage (before deploying to AgentCore):
    1. Set environment variables:
         export REDSHIFT_CLUSTER_ID=sample-redshift-cluster-mcp
         export REDSHIFT_DATABASE=dev
         export AWS_REGION=ap-south-1
         export REDSHIFT_DEFAULT_DB_USER=db_user   # native user for local testing

    2. In terminal 1, start the server:
         python mcp_server.py

    3. In terminal 2, run this script:
         python test_local.py

The server runs on http://localhost:8000/mcp by default.
"""

import asyncio
import json

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client


MCP_URL = "http://localhost:8000/mcp"


async def run_tests():
    print(f"Connecting to {MCP_URL} ...\n")

    async with streamablehttp_client(MCP_URL, {}, timeout=60, terminate_on_close=False) as (
        read_stream,
        write_stream,
        _,
    ):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()

            # ── List available tools ──────────────────────────────────────────
            tools = await session.list_tools()
            print("Available tools:")
            for t in tools.tools:
                print(f"  • {t.name}: {t.description.splitlines()[0]}")
            print()

            # ── list_schemas ─────────────────────────────────────────────────
            print("─── list_schemas ───")
            result = await session.call_tool("list_schemas", {})
            data = json.loads(result.content[0].text)
            print(f"Schemas: {data.get('schemas', [])}\n")

            # ── list_tables ──────────────────────────────────────────────────
            print("─── list_tables(schema='public') ───")
            result = await session.call_tool("list_tables", {"schema": "public"})
            data = json.loads(result.content[0].text)
            print(f"Tables: {data.get('tables', [])}\n")

            # ── describe_table ───────────────────────────────────────────────
            tables = data.get("tables", [])
            if tables:
                first_table = tables[0]
                print(f"─── describe_table(schema='public', table='{first_table}') ───")
                result = await session.call_tool(
                    "describe_table", {"schema": "public", "table": first_table}
                )
                data = json.loads(result.content[0].text)
                print(f"Columns ({len(data.get('columns', []))} total):")
                for col in data.get("columns", [])[:5]:
                    print(f"  {col['column_name']:30s}  {col['data_type']}")
                print()

            # ── execute_query ─────────────────────────────────────────────────
            print("─── execute_query ───")
            result = await session.call_tool(
                "execute_query",
                {"sql": "SELECT current_user, current_date, version()"},
            )
            data = json.loads(result.content[0].text)
            print(f"Columns: {data.get('columns')}")
            print(f"Row count: {data.get('row_count')}")
            for row in data.get("rows", []):
                print(f"  {row}")
            print()

            # ── Reject non-SELECT ─────────────────────────────────────────────
            print("─── Verify DDL is rejected ───")
            result = await session.call_tool(
                "execute_query",
                {"sql": "DROP TABLE public.sales"},
            )
            # FastMCP surfaces errors in isError=True content
            if result.isError:
                print(f"Correctly rejected: {result.content[0].text}\n")
            else:
                print("ERROR: DDL was not rejected — check _is_select() logic\n")


if __name__ == "__main__":
    asyncio.run(run_tests())
