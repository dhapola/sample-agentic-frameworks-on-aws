"""
Redshift MCP Server — Amazon Bedrock AgentCore Runtime

Provides MCP tools for internal business analysts to query Redshift using
natural language via standard MCP clients (Kiro, Claude Desktop, Claude Code).

Authentication:
  - Inbound:  AWS SigV4 (IAM auth via mcp-proxy-for-aws on client laptop)
  - Per-user: DbUser injected by mcp-proxy-for-aws into the MCP request's
              `_meta.DbUser` field (via the proxy's --metadata flag).
              The MCP server reads it and passes it to Redshift Data API.

Access pattern:
  MCP client → AgentCore Runtime (this server) → Redshift Data API → Redshift cluster
"""

import logging
import os
import re
import time

import boto3
from mcp.server.fastmcp import Context, FastMCP

# ── Logging ────────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
)
logger = logging.getLogger("redshift_mcp")

# ── Configuration (from environment — set in agentcore.json) ──────────────────

CLUSTER_ID  = os.environ.get("REDSHIFT_CLUSTER_ID", "sample-redshift-cluster-mcp")
DATABASE    = os.environ.get("REDSHIFT_DATABASE",   "dev")
REGION      = os.environ.get("AWS_REGION",          "ap-south-1")

# Key inside MCP request `_meta` that carries the per-user Redshift username.
# Set on the client side via:  mcp-proxy-for-aws --metadata DbUser=<username>
DB_USER_META_KEY = "DbUser"

# Data API polling config
POLL_INTERVAL_S   = 0.5   # seconds between DescribeStatement calls
POLL_TIMEOUT_S    = 120   # give up after 2 minutes
MAX_ROWS_PER_PAGE = 500   # GetStatementResult page size

# ── FastMCP app ────────────────────────────────────────────────────────────────

mcp = FastMCP(
    name="redshift",
    host="0.0.0.0",
    stateless_http=True,
)

# ── Helpers ───────────────────────────────────────────────────────────────────


def _get_db_user(ctx: Context) -> str:
    """
    Extract the DbUser from the MCP request `_meta` field.

    The value is injected on the client side by mcp-proxy-for-aws via:
        --metadata DbUser=<username>

    The username is derived from the user's IAM session name, which equals
    their Identity Center login (e.g. 'ddredshift').

    Falls back to REDSHIFT_DEFAULT_DB_USER env var only for local development.
    """
    meta = ctx.request_context.meta if ctx.request_context else None

    db_user = None
    if meta is not None:
        # Pydantic v2 with extra="allow" stores unknown keys; access via dump
        meta_dict = meta.model_dump(exclude_none=True)
        db_user = (meta_dict.get(DB_USER_META_KEY) or "").strip() or None

    if not db_user:
        db_user = os.environ.get("REDSHIFT_DEFAULT_DB_USER", "").strip() or None
        if not db_user:
            raise ValueError(
                f"'{DB_USER_META_KEY}' is missing from MCP request _meta. "
                "Ensure the MCP client config passes "
                f"--metadata {DB_USER_META_KEY}=<username>."
            )
        logger.warning(
            "DbUser meta absent — using fallback '%s' (local dev only)", db_user
        )

    return db_user


def _redshift_data_client():
    """Return a boto3 redshift-data client for the configured region."""
    return boto3.client("redshift-data", region_name=REGION)


def _execute_and_wait(
    client, sql: str, db_user: str, parameters: list[dict] | None = None
) -> dict:
    """
    Submit a SQL statement to the Redshift Data API and poll until complete.

    Returns the DescribeStatement response when status reaches FINISHED.
    Raises RuntimeError on FAILED / ABORTED or TimeoutError on poll timeout.

    Args:
        client:     boto3 redshift-data client.
        sql:        SQL statement (use :name placeholders for parameters).
        db_user:    Redshift database user to execute as.
        parameters: Optional list of {"name": ..., "value": ...} dicts for
                    parameterized queries (prevents SQL injection).
    """
    logger.info("Executing SQL for user '%s': %.200s", db_user, sql)

    kwargs = dict(
        ClusterIdentifier=CLUSTER_ID,
        Database=DATABASE,
        DbUser=db_user,
        Sql=sql,
        WithEvent=False,
    )
    if parameters:
        kwargs["Parameters"] = [
            {"name": p["name"], "value": p["value"]} for p in parameters
        ]

    response = client.execute_statement(**kwargs)
    statement_id = response["Id"]
    logger.info("Statement submitted: %s", statement_id)

    deadline = time.monotonic() + POLL_TIMEOUT_S
    while True:
        desc = client.describe_statement(Id=statement_id)
        status = desc["Status"]
        logger.debug("Statement %s status: %s", statement_id, status)

        if status == "FINISHED":
            logger.info("Statement %s finished. Rows: %s", statement_id, desc.get("ResultRows"))
            return desc

        if status in ("FAILED", "ABORTED"):
            error = desc.get("Error", "No error detail available")
            logger.error("Statement %s %s: %s", statement_id, status, error)
            raise RuntimeError(f"Query {status.lower()}: {error}")

        if time.monotonic() > deadline:
            client.cancel_statement(Id=statement_id)
            raise TimeoutError(
                f"Query timed out after {POLL_TIMEOUT_S}s (statement {statement_id})"
            )

        time.sleep(POLL_INTERVAL_S)


def _fetch_all_rows(client, statement_id: str) -> tuple[list[str], list[dict]]:
    """
    Paginate through GetStatementResult and return (column_names, rows).

    Each row is a dict mapping column name → value (None for SQL NULLs).
    """
    columns: list[str] = []
    rows: list[dict] = []
    next_token = None
    first_page = True

    while True:
        kwargs = {"Id": statement_id}
        if next_token:
            kwargs["NextToken"] = next_token

        page = client.get_statement_result(**kwargs)

        if first_page:
            columns = [col["name"] for col in page.get("ColumnMetadata", [])]
            first_page = False

        for record in page.get("Records", []):
            row = {}
            for col_name, field in zip(columns, record):
                # Each field is a dict with one key indicating the type
                # e.g. {"stringValue": "foo"} or {"isNull": True}
                if field.get("isNull"):
                    row[col_name] = None
                elif "stringValue" in field:
                    row[col_name] = field["stringValue"]
                elif "longValue" in field:
                    row[col_name] = field["longValue"]
                elif "doubleValue" in field:
                    row[col_name] = field["doubleValue"]
                elif "booleanValue" in field:
                    row[col_name] = field["booleanValue"]
                else:
                    # Blob or unknown — convert to string representation
                    row[col_name] = str(field)
            rows.append(row)

        next_token = page.get("NextToken")
        if not next_token:
            break

    return columns, rows


def _is_select(sql: str) -> bool:
    """
    Return True only if sql is a safe, read-only SELECT statement.

    Rejects:
      - Multiple statements (semicolons)
      - DML/DDL keywords (INSERT, UPDATE, DELETE, DROP, ALTER, CREATE, TRUNCATE,
        GRANT, REVOKE, COPY, UNLOAD)
      - Statements that don't start with SELECT or WITH ... SELECT
    """
    # Reject multiple statements
    if ";" in sql:
        return False

    # Strip SQL comments (block and line) to prevent comment-based bypasses
    stripped = re.sub(r"/\*.*?\*/", " ", sql, flags=re.DOTALL)  # block comments
    stripped = re.sub(r"--[^\n]*", " ", stripped)                # line comments
    normalized = stripped.strip().upper()

    if not normalized:
        return False

    # Must start with SELECT or WITH (for CTEs)
    if not (normalized.startswith("SELECT") or normalized.startswith("WITH")):
        return False

    # Reject DML/DDL keywords anywhere in the statement (word-boundary match)
    # These should never appear in a read-only query
    forbidden = (
        r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|TRUNCATE|"
        r"GRANT|REVOKE|COPY|UNLOAD|CALL|EXEC|EXECUTE)\b"
    )
    if re.search(forbidden, normalized):
        return False

    return True


# ── MCP Tools ─────────────────────────────────────────────────────────────────


@mcp.tool()
def execute_query(sql: str, ctx: Context) -> dict:
    """
    Execute a SELECT SQL query against the Redshift cluster and return results.

    The query runs as the authenticated user's Redshift identity, ensuring
    per-user access controls and audit trail.

    Only SELECT statements are permitted. DDL and DML are rejected.

    Args:
        sql: A valid SQL SELECT statement to execute against Redshift.

    Returns:
        A dict with:
          - columns:    list of column names
          - rows:       list of row dicts (column_name → value)
          - row_count:  number of rows returned
    """
    if not _is_select(sql):
        raise ValueError(
            "Only SELECT statements are permitted. "
            "DDL and DML operations are not supported."
        )

    db_user = _get_db_user(ctx)
    client = _redshift_data_client()
    desc = _execute_and_wait(client, sql, db_user)

    if not desc.get("HasResultSet", False):
        return {"columns": [], "rows": [], "row_count": 0}

    columns, rows = _fetch_all_rows(client, desc["Id"])
    return {
        "columns": columns,
        "rows": rows,
        "row_count": len(rows),
    }


@mcp.tool()
def list_schemas(ctx: Context) -> dict:
    """
    List all user-visible schemas in the Redshift database.

    Returns:
        A dict with:
          - schemas: list of schema name strings
    """
    db_user = _get_db_user(ctx)

    sql = """
        SELECT schema_name
        FROM information_schema.schemata
        WHERE schema_name NOT IN ('information_schema', 'pg_catalog', 'pg_toast',
                                   'pg_temp_1', 'pg_toast_temp_1')
        ORDER BY schema_name
    """

    client = _redshift_data_client()
    desc = _execute_and_wait(client, sql.strip(), db_user)

    if not desc.get("HasResultSet", False):
        return {"schemas": []}

    _, rows = _fetch_all_rows(client, desc["Id"])
    return {"schemas": [row["schema_name"] for row in rows]}


@mcp.tool()
def list_tables(schema: str, ctx: Context) -> dict:
    """
    List all tables in the specified schema.

    Args:
        schema: The schema name to list tables from (e.g. 'public').

    Returns:
        A dict with:
          - schema: the schema name queried
          - tables: list of table name strings
    """
    if not schema or not schema.replace("_", "").isalnum():
        raise ValueError(f"Invalid schema name: '{schema}'")

    db_user = _get_db_user(ctx)

    sql = """
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = :schema
          AND table_type IN ('BASE TABLE', 'VIEW')
        ORDER BY table_name
    """

    client = _redshift_data_client()
    desc = _execute_and_wait(
        client,
        sql.strip(),
        db_user,
        parameters=[{"name": "schema", "value": schema}],
    )

    if not desc.get("HasResultSet", False):
        return {"schema": schema, "tables": []}

    _, rows = _fetch_all_rows(client, desc["Id"])
    return {
        "schema": schema,
        "tables": [row["table_name"] for row in rows],
    }


@mcp.tool()
def describe_table(schema: str, table: str, ctx: Context) -> dict:
    """
    Return the column names, data types, and nullability for a table.

    Args:
        schema: The schema name (e.g. 'public').
        table:  The table name (e.g. 'sales').

    Returns:
        A dict with:
          - schema:  schema name
          - table:   table name
          - columns: list of dicts, each with 'column_name', 'data_type',
                     'character_maximum_length', 'is_nullable'
    """
    # Identifier validation as defense-in-depth alongside parameterized queries
    for name, value in (("schema", schema), ("table", table)):
        if not value or not value.replace("_", "").isalnum():
            raise ValueError(f"Invalid {name} name: '{value}'")

    db_user = _get_db_user(ctx)

    sql = """
        SELECT
            column_name,
            data_type,
            character_maximum_length,
            is_nullable
        FROM information_schema.columns
        WHERE table_schema = :schema
          AND table_name   = :table
        ORDER BY ordinal_position
    """

    client = _redshift_data_client()
    desc = _execute_and_wait(
        client,
        sql.strip(),
        db_user,
        parameters=[
            {"name": "schema", "value": schema},
            {"name": "table", "value": table},
        ],
    )

    if not desc.get("HasResultSet", False):
        return {"schema": schema, "table": table, "columns": []}

    _, rows = _fetch_all_rows(client, desc["Id"])
    return {
        "schema": schema,
        "table": table,
        "columns": rows,
    }


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    logger.info(
        "Starting Redshift MCP Server | cluster=%s database=%s region=%s",
        CLUSTER_ID, DATABASE, REGION,
    )
    mcp.run(transport="streamable-http")
