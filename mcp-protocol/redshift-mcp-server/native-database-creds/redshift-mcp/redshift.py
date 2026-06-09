"""Redshift connection pooling, read-only enforcement, and tool queries.

All DB calls here are blocking; the server runs them in a worker thread.
Authorization is delegated entirely to Redshift: each connection authenticates
as the end user's SQL account, so every query is constrained by that user's
GRANTs and group membership.
"""
from __future__ import annotations

import hashlib
import re
import threading
import time
from collections import deque

import redshift_connector


class AuthError(Exception):
    """Connection/authentication failure -> maps to HTTP 401."""


class QueryRejected(Exception):
    """Query failed read-only policy -> surfaced as a tool error."""


_READ_ONLY = re.compile(r"^\s*(with|select|show|explain)\b", re.IGNORECASE)


def assert_read_only(sql: str) -> str:
    """Allow a single read-only statement only."""
    stmt = sql.strip().rstrip(";").strip()
    if not stmt:
        raise QueryRejected("empty statement")
    if ";" in stmt:
        raise QueryRejected("multiple statements are not allowed")
    if not _READ_ONLY.match(stmt):
        raise QueryRejected("only SELECT/WITH/SHOW/EXPLAIN queries are allowed")
    return stmt


class ConnectionManager:
    """Per-identity pool of idle connections keyed by hash(user:password)."""

    def __init__(self, host, port, db, max_idle=4, idle_ttl=300, stmt_timeout_ms=30000):
        self._host, self._port, self._db = host, port, db
        self._max_idle, self._idle_ttl, self._timeout = max_idle, idle_ttl, stmt_timeout_ms
        self._pools: dict[str, deque] = {}
        self._lock = threading.Lock()

    @staticmethod
    def _key(user: str, pwd: str) -> str:
        return hashlib.sha256(f"{user}:{pwd}".encode()).hexdigest()

    def acquire(self, user: str, pwd: str):
        key = self._key(user, pwd)
        now = time.monotonic()
        with self._lock:
            dq = self._pools.get(key)
            while dq:
                conn, last = dq.pop()
                if now - last <= self._idle_ttl:
                    return key, conn
                _close(conn)
        return key, self._connect(user, pwd)

    def _connect(self, user: str, pwd: str):
        try:
            conn = redshift_connector.connect(
                host=self._host, port=self._port, database=self._db,
                user=user, password=pwd,
            )
        except Exception as e:  # driver error hierarchy varies; classify by message
            msg = str(e).lower()
            if "auth" in msg or "password" in msg or "denied" in msg:
                raise AuthError("invalid Redshift credentials") from e
            raise AuthError(f"could not connect to Redshift: {e}") from e
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute(f"set statement_timeout to {int(self._timeout)}")
        return conn

    def release(self, key: str, conn, broken: bool = False):
        if broken:
            _close(conn)
            return
        with self._lock:
            dq = self._pools.setdefault(key, deque())
            if len(dq) < self._max_idle:
                dq.append((conn, time.monotonic()))
            else:
                _close(conn)


def _close(conn):
    try:
        conn.close()
    except Exception:
        pass


# --- Tool queries -----------------------------------------------------------
# Each returns (columns, rows). Identifiers are passed as parameters where
# possible; psql-style %s params are bound by the driver (no string concat).

def list_schemas(conn):
    return _fetch(conn,
        "select schema_name from information_schema.schemata order by 1")


def list_tables(conn, schema: str):
    return _fetch(conn,
        "select table_name, table_type from information_schema.tables "
        "where table_schema = %s order by 1", (schema,))


def describe_table(conn, schema: str, table: str):
    return _fetch(conn,
        "select column_name, data_type, is_nullable, character_maximum_length "
        "from information_schema.columns "
        "where table_schema = %s and table_name = %s order by ordinal_position",
        (schema, table))


def run_query(conn, sql: str, row_cap: int):
    stmt = assert_read_only(sql)
    return _fetch(conn, stmt, cap=row_cap)


def _fetch(conn, sql, params=None, cap=None):
    with conn.cursor() as cur:
        cur.execute(sql, params) if params else cur.execute(sql)
        cols = [d[0] for d in cur.description] if cur.description else []
        if cap is None:
            return cols, cur.fetchall()
        rows = cur.fetchmany(cap + 1)
        return cols, rows[:cap], len(rows) > cap
