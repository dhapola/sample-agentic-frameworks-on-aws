from pathlib import Path
import os
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field, asdict, is_dataclass
import clickhouse_connect
import concurrent.futures
from clickhouse_connect.driver.binding import format_query_value
from clickhouse_env import get_config
import atexit
import json
from utility import Utility


@dataclass
class Column:
    database: str
    table: str
    name: str
    column_type: str
    default_kind: Optional[str]
    default_expression: Optional[str]
    comment: Optional[str]


@dataclass
class Table:
    database: str
    name: str
    engine: str
    create_table_query: str
    dependencies_database: str
    dependencies_table: str
    engine_full: str
    sorting_key: str
    primary_key: str
    
    columns: List[Column] = field(default_factory=list)


QUERY_EXECUTOR = concurrent.futures.ThreadPoolExecutor(max_workers=10)
atexit.register(lambda: QUERY_EXECUTOR.shutdown(wait=True))
SELECT_QUERY_TIMEOUT_SECS = 30

class ClickHouseClient:
    def __init__(self):
        self.util = Utility()

    
    def result_to_table(self, query_columns, result) -> List[Table]:
        return [Table(**dict(zip(query_columns, row))) for row in result]


    def result_to_column(self, query_columns, result) -> List[Column]:
        return [Column(**dict(zip(query_columns, row))) for row in result]


    def to_json(self, obj: Any) -> str:
        if is_dataclass(obj):
            return json.dumps(asdict(obj), default=self.to_json)
        elif isinstance(obj, list):
            return [self.to_json(item) for item in obj]
        elif isinstance(obj, dict):
            return {key: self.to_json(value) for key, value in obj.items()}
        return obj

    def list_databases(self):
        """List available ClickHouse databases"""
        self.util.log_data("Listing all databases")
        client = self.create_clickhouse_client()
        result = client.command("SHOW DATABASES")
        self.util.log_data(f"Found {len(result) if isinstance(result, list) else 1} databases")
        return result


    def list_tables(self, 
        database: str, like: Optional[str] = None, not_like: Optional[str] = None
    ):
        """List available ClickHouse tables in a database, including schema, comment,
        row count, and column count."""

        self.util.log_data(f"Listing tables in database '{database}'")
        client = self.create_clickhouse_client()
        query = f"SELECT database, name, engine, create_table_query, dependencies_database, dependencies_table, engine_full, sorting_key, primary_key FROM system.tables WHERE database = {format_query_value(database)}"
        if like:
            query += f" AND name LIKE {format_query_value(like)}"

        if not_like:
            query += f" AND name NOT LIKE {format_query_value(not_like)}"
 
        
        result = client.query(query)
        

        # Deserialize result as Table dataclass instances
        tables = self.result_to_table(result.column_names, result.result_rows)

        for table in tables:
            column_data_query = f"SELECT database, table, name, type AS column_type, default_kind, default_expression, comment FROM system.columns WHERE database = {format_query_value(database)} AND table = {format_query_value(table.name)}"
            column_data_query_result = client.query(column_data_query)
            table.columns = [
                c
                for c in self.result_to_column(
                    column_data_query_result.column_names,
                    column_data_query_result.result_rows,
                )
            ]

        self.util.log_data(f"Found {len(tables)} tables")
        return [asdict(table) for table in tables]


    def execute_query(self, query: str):
        client = self.create_clickhouse_client()
        try:
            read_only = self.get_readonly_setting(client)
            res = client.query(query, settings={"readonly": read_only})
            column_names = res.column_names
            rows = []
            for row in res.result_rows:
                row_dict = {}
                for i, col_name in enumerate(column_names):
                    row_dict[col_name] = row[i]
                rows.append(row_dict)
            
            # self.util.log_data(f"Result:\n\n {rows}\n\n")
            self.util.log_data(f"Query returned {len(rows)} rows")
            return rows
        except Exception as err:
            self.util.log_error(f"Error executing query: {err}")
            # Return a structured dictionary rather than a string to ensure proper serialization
            # by the MCP protocol. String responses for errors can cause BrokenResourceError.
            return {"error": str(err)}


    def run_select_query(self, query: str):
        """Run a SELECT query in a ClickHouse database"""
        self.util.log_data(f"Executing SELECT query: {query}")
        try:
            future = QUERY_EXECUTOR.submit(self.execute_query, query)
            try:
                result = future.result(timeout=SELECT_QUERY_TIMEOUT_SECS)
                # Check if we received an error structure from execute_query
                if isinstance(result, dict) and "error" in result:
                    self.util.log_data(f"Query failed: {result['error']}")
                    # MCP requires structured responses; string error messages can cause
                    # serialization issues leading to BrokenResourceError
                    return {
                        "status": "error",
                        "message": f"Query failed: {result['error']}",
                    }
                return result
            except concurrent.futures.TimeoutError:
                self.util.log_data(
                    f"Query timed out after {SELECT_QUERY_TIMEOUT_SECS} seconds: {query}"
                )
                future.cancel()
                # Return a properly structured response for timeout errors
                return {
                    "status": "error",
                    "message": f"Query timed out after {SELECT_QUERY_TIMEOUT_SECS} seconds",
                }
        except Exception as e:
            self.util.log_error(f"Unexpected error in run_select_query: {str(e)}")
            # Catch all other exceptions and return them in a structured format
            # to prevent MCP serialization failures
            return {"status": "error", "message": f"Unexpected error: {str(e)}"}


    def create_clickhouse_client(self):
        client_config = get_config().get_client_config()
        self.util.log_data(
            f"Creating ClickHouse client connection to {client_config['host']}:{client_config['port']} "
            f"as {client_config['username']} "
            f"(secure={client_config['secure']}, verify={client_config['verify']}, "
            f"connect_timeout={client_config['connect_timeout']}s, "
            f"send_receive_timeout={client_config['send_receive_timeout']}s)"
        )

        try:
            client = clickhouse_connect.get_client(**client_config)
            # Test the connection
            version = client.server_version
            self.util.log_data(f"Successfully connected to ClickHouse server version {version}")
            return client
        except Exception as e:
            self.util.log_error(f"Failed to connect to ClickHouse: {str(e)}")
            raise


    def get_readonly_setting(self, client) -> str:
        """Get the appropriate readonly setting value to use for queries.

        This function handles potential conflicts between server and client readonly settings:
        - readonly=0: No read-only restrictions
        - readonly=1: Only read queries allowed, settings cannot be changed
        - readonly=2: Only read queries allowed, settings can be changed (except readonly itself)

        If server has readonly=2 and client tries to set readonly=1, it would cause:
        "Setting readonly is unknown or readonly" error

        This function preserves the server's readonly setting unless it's 0, in which case
        we enforce readonly=1 to ensure queries are read-only.

        Args:
            client: ClickHouse client connection

        Returns:
            String value of readonly setting to use
        """
        read_only = client.server_settings.get("readonly")
        if read_only:
            if read_only == "0":
                return "1"  # Force read-only mode if server has it disabled
            else:
                return read_only.value  # Respect server's readonly setting (likely 2)
        else:
            return "1"  # Default to basic read-only mode if setting isn't present
