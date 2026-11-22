"""
Layali Analytics - Database Connection & Execution Utilities
Reads credentials strictly from environment variables (.env).
"""

import os
import re
from typing import Optional
import pyodbc
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()


def get_connection_string(include_db: bool = True) -> str:
    """Build pyodbc connection string strictly from environment variables."""
    server = os.getenv("DB_SERVER", "localhost")
    driver = os.getenv("DB_DRIVER", "ODBC Driver 18 for SQL Server")
    db_name = os.getenv("DB_NAME", "LayaliAnalytics")
    trusted = os.getenv("DB_TRUSTED_CONNECTION", "yes").lower() in ("yes", "true", "1")
    user = os.getenv("DB_USER", "").strip()
    password = os.getenv("DB_PASSWORD", "").strip()
    encrypt = os.getenv("DB_ENCRYPT", "yes")
    trust_cert = os.getenv("DB_TRUST_SERVER_CERTIFICATE", "yes")

    parts = [
        f"DRIVER={{{driver}}}",
        f"SERVER={server}",
    ]

    if include_db and db_name:
        parts.append(f"DATABASE={db_name}")

    if trusted:
        parts.append("Trusted_Connection=yes")
    else:
        parts.append(f"UID={user}")
        parts.append(f"PWD={password}")

    parts.append(f"Encrypt={encrypt}")
    parts.append(f"TrustServerCertificate={trust_cert}")

    return ";".join(parts) + ";"


def get_connection(include_db: bool = True, autocommit: bool = False) -> pyodbc.Connection:
    """Establish and return an active pyodbc Connection."""
    conn_str = get_connection_string(include_db=include_db)
    conn = pyodbc.connect(conn_str, autocommit=autocommit)
    return conn


def execute_tsql_script(script_path: str, conn: Optional[pyodbc.Connection] = None):
    """Execute a T-SQL script containing multiple GO-separated batches."""
    close_conn = False
    if conn is None:
        conn = get_connection(include_db=True, autocommit=True)
        close_conn = True

    with open(script_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Split batches on T-SQL 'GO' keyword on its own line
    batches = re.split(r"^\s*GO\s*$", content, flags=re.MULTILINE | re.IGNORECASE)

    cursor = conn.cursor()
    for batch in batches:
        clean_batch = batch.strip()
        if clean_batch:
            cursor.execute(clean_batch)

    cursor.close()
    if close_conn:
        conn.close()
