"""
Layali Analytics - Database Loader & Production ETL Pipeline
Stack: Python, pyodbc, Microsoft SQL Server (T-SQL)
Credentials loaded strictly from environment variables (.env).
Enforces pre-load validation, transactional idempotent raw loading,
staging verification, quarantine redirection for malformed files,
and promotion to marts only when all checks pass.
"""

import argparse
import csv
import json
import os
import shutil
import sys
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import pyodbc

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.db import execute_tsql_script, get_connection, get_connection_string

RAW_CLEAN_DIR = os.path.join("data", "raw", "clean")
RAW_DIRTY_DIR = os.path.join("data", "raw", "dirty")
QUARANTINE_DIR = os.path.join("data", "quarantine")
SQL_DIR = os.path.join("sql")

ALLOWED_BRANCHES = {"BR01", "BR02", "BR03"}


def init_database():
    """Execute SQL scripts 01-05 to initialize DB, tables, views, and dimensions."""
    print("Initializing Database, Schemas, Tables, and Views...")
    # Step 1: Connect to master to create DB & schemas
    conn_master = pyodbc.connect(get_connection_string(include_db=False), autocommit=True)
    execute_tsql_script(os.path.join(SQL_DIR, "01_init_database.sql"), conn=conn_master)
    conn_master.close()
    print("✓ Initialized database LayaliAnalytics and schemas (raw, staging, marts)")

    # Step 2: Connect to LayaliAnalytics to run remaining DDLs
    conn = get_connection(include_db=True, autocommit=True)
    execute_tsql_script(os.path.join(SQL_DIR, "02_create_raw_tables.sql"), conn=conn)
    print("✓ Created raw tables with clustered indexes")
    execute_tsql_script(os.path.join(SQL_DIR, "03_create_staging_views.sql"), conn=conn)
    print("✓ Created staging views")
    execute_tsql_script(os.path.join(SQL_DIR, "04_create_marts_tables.sql"), conn=conn)
    print("✓ Created marts tables (dimensions & facts)")
    execute_tsql_script(os.path.join(SQL_DIR, "05_populate_dim_date.sql"), conn=conn)
    print("✓ Populated marts.dim_date (Jan 1, 2026 - Jun 30, 2026)")
    conn.close()


def load_master_dimensions():
    """Load master entity catalogs (branches, products, customers, channels)."""
    conn = get_connection(include_db=True, autocommit=False)
    cursor = conn.cursor()
    cursor.fast_executemany = True

    try:
        # 1. Branches
        branches_file = os.path.join(RAW_CLEAN_DIR, "branches.csv")
        with open(branches_file, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            branch_rows = [(r["branch_id"], r["branch_name"], r["opened_date"], "branches.csv") for r in reader]

        cursor.execute("TRUNCATE TABLE raw.branches;")
        cursor.executemany(
            "INSERT INTO raw.branches (branch_id, branch_name, opened_date, source_file) VALUES (?, ?, ?, ?);",
            branch_rows,
        )

        cursor.execute("""
            MERGE INTO marts.dim_branch AS target
            USING staging.stg_branches AS source
            ON target.branch_id = source.branch_id
            WHEN MATCHED THEN
                UPDATE SET target.branch_name = source.branch_name, target.opened_date = source.opened_date
            WHEN NOT MATCHED THEN
                INSERT (branch_id, branch_name, opened_date)
                VALUES (source.branch_id, source.branch_name, source.opened_date);
        """)

        # 2. Products
        products_file = os.path.join(RAW_CLEAN_DIR, "products.csv")
        with open(products_file, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            prod_rows = [
                (r["product_id"], r["product_name"], r["category"], str(r["unit_price_sar"]), str(r["unit_cost_sar"]), "products.csv")
                for r in reader
            ]

        cursor.execute("TRUNCATE TABLE raw.products;")
        cursor.executemany(
            "INSERT INTO raw.products (product_id, product_name, category, unit_price_sar, unit_cost_sar, source_file) VALUES (?, ?, ?, ?, ?, ?);",
            prod_rows,
        )

        cursor.execute("""
            MERGE INTO marts.dim_product AS target
            USING staging.stg_products AS source
            ON target.product_id = source.product_id
            WHEN MATCHED THEN
                UPDATE SET
                    target.product_name   = source.product_name,
                    target.category       = source.category,
                    target.unit_price_sar = source.unit_price_sar,
                    target.unit_cost_sar  = source.unit_cost_sar
            WHEN NOT MATCHED THEN
                INSERT (product_id, product_name, category, unit_price_sar, unit_cost_sar)
                VALUES (source.product_id, source.product_name, source.category, source.unit_price_sar, source.unit_cost_sar);
        """)

        # 3. Customers
        customers_file = os.path.join(RAW_CLEAN_DIR, "customers.csv")
        with open(customers_file, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            cust_rows = [(r["customer_id"], "customers.csv") for r in reader]

        cursor.execute("TRUNCATE TABLE raw.customers;")
        cursor.executemany(
            "INSERT INTO raw.customers (customer_id, source_file) VALUES (?, ?);",
            cust_rows,
        )

        cursor.execute("""
            MERGE INTO marts.dim_customer AS target
            USING staging.stg_customers AS source
            ON target.customer_id = source.customer_id
            WHEN NOT MATCHED THEN
                INSERT (customer_id) VALUES (source.customer_id);
        """)

        # 4. Channels
        channels = [
            ("dine-in", "Dine-In"),
            ("takeaway", "Takeaway"),
            ("delivery", "Delivery"),
        ]
        cursor.executemany("""
            MERGE INTO marts.dim_channel AS target
            USING (SELECT ? AS channel, ? AS channel_name) AS source
            ON target.channel = source.channel
            WHEN NOT MATCHED THEN
                INSERT (channel, channel_name) VALUES (source.channel, source.channel_name);
        """, channels)

        conn.commit()
        print("✓ Loaded master dimensions (branches, products, customers, channels)")
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        cursor.close()
        conn.close()


def validate_source_files(
    orders_path: str,
    lines_path: str,
) -> Tuple[bool, List[Dict]]:
    """
    Pre-load validation gate.
    Asserts schema, FK constraints, and discount integrity.
    Returns (is_valid, list_of_violations).
    """
    violations = []

    # 1. Foreign Key check: branch_id must be in ALLOWED_BRANCHES
    with open(orders_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            branch = row.get("branch_id", "")
            if branch not in ALLOWED_BRANCHES:
                violations.append(
                    {
                        "reason_code": "ERR_UNKNOWN_BRANCH_FK",
                        "table": "orders",
                        "record_id": row.get("order_id", ""),
                        "details": f"Unknown branch_id '{branch}' not in master branch catalog",
                    }
                )

    # 2. Line Discount check: discount cannot exceed gross or be negative
    with open(lines_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                qty = int(row.get("quantity", 0))
                price = float(row.get("unit_price_sar", 0.0))
                discount = float(row.get("discount_sar", 0.0))
                gross = round(qty * price, 2)
            except (ValueError, TypeError):
                violations.append(
                    {
                        "reason_code": "ERR_INVALID_NUMERIC",
                        "table": "order_lines",
                        "record_id": row.get("order_line_id", ""),
                        "details": "Non-numeric quantity or pricing encountered",
                    }
                )
                continue

            if discount > gross:
                violations.append(
                    {
                        "reason_code": "ERR_IMPOSSIBLE_DISCOUNT",
                        "table": "order_lines",
                        "record_id": row.get("order_line_id", ""),
                        "details": f"Discount {discount} SAR exceeds gross {gross} SAR",
                    }
                )
            elif discount < 0:
                violations.append(
                    {
                        "reason_code": "ERR_NEGATIVE_DISCOUNT",
                        "table": "order_lines",
                        "record_id": row.get("order_line_id", ""),
                        "details": f"Negative discount {discount} SAR detected",
                    }
                )

    is_valid = len(violations) == 0
    return is_valid, violations


def quarantine_files(
    orders_path: str,
    lines_path: str,
    violations: List[Dict],
    batch_month: str,
):
    """Quarantine malformed files and log reason codes to data/quarantine."""
    os.makedirs(QUARANTINE_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Copy files
    dest_orders = os.path.join(QUARANTINE_DIR, f"{os.path.basename(orders_path)}_{timestamp}")
    dest_lines = os.path.join(QUARANTINE_DIR, f"{os.path.basename(lines_path)}_{timestamp}")
    shutil.copy2(orders_path, dest_orders)
    shutil.copy2(lines_path, dest_lines)

    # Append to quarantine log
    log_file = os.path.join(QUARANTINE_DIR, "quarantine_log.json")
    existing_log = []
    if os.path.exists(log_file):
        try:
            with open(log_file, "r", encoding="utf-8") as f:
                existing_log = json.load(f)
        except Exception:
            existing_log = []

    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "batch_month": batch_month,
        "source_orders": orders_path,
        "source_lines": lines_path,
        "quarantined_orders": dest_orders,
        "quarantined_lines": dest_lines,
        "violation_count": len(violations),
        "violations": violations,
    }
    existing_log.append(log_entry)

    with open(log_file, "w", encoding="utf-8") as f:
        json.dump(existing_log, f, indent=2)

    # Also save CSV summary
    csv_log = os.path.join(QUARANTINE_DIR, "quarantine_log.csv")
    csv_exists = os.path.exists(csv_log)
    with open(csv_log, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f, fieldnames=["timestamp", "batch_month", "reason_code", "table", "record_id", "details"]
        )
        if not csv_exists:
            writer.writeheader()
        for v in violations:
            writer.writerow(
                {
                    "timestamp": log_entry["timestamp"],
                    "batch_month": batch_month,
                    "reason_code": v["reason_code"],
                    "table": v["table"],
                    "record_id": v["record_id"],
                    "details": v["details"],
                }
            )


def load_monthly_batch(
    batch_month: str,
    orders_path: str,
    lines_path: str,
) -> bool:
    """
    Load a single monthly batch:
    1. Pre-load validation gate.
    2. Idempotent raw loading in a single transaction (deletes prior batch).
    3. Promotion to marts in a transaction after quality verification.
    """
    print(f"\n--- Loading Batch Month: {batch_month} ---")
    print(f"Source files: {orders_path} & {lines_path}")

    # 1. Pre-load validation
    is_valid, violations = validate_source_files(orders_path, lines_path)
    if not is_valid:
        print(f"❌ Pre-load Validation FAILED with {len(violations)} defect(s).")
        quarantine_files(orders_path, lines_path, violations, batch_month)
        print(f"⚠️ Files quarantined to {QUARANTINE_DIR} with reason codes. Aborting before changing marts.")
        return False

    # 2. Raw Ingestion (in Transaction)
    conn = get_connection(include_db=True, autocommit=False)
    cursor = conn.cursor()
    cursor.fast_executemany = True

    try:
        # Delete existing raw records for this batch month (idempotency)
        cursor.execute("DELETE FROM raw.order_lines WHERE batch_month = ?;", (batch_month,))
        cursor.execute("DELETE FROM raw.orders WHERE batch_month = ?;", (batch_month,))

        # Load orders
        order_rows = []
        with open(orders_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for r in reader:
                cust_val = r.get("customer_id", "").strip()
                order_rows.append(
                    (
                        r["order_id"],
                        r["order_timestamp"],
                        r["order_date"],
                        r["branch_id"],
                        r["channel"],
                        cust_val if cust_val else None,
                        r["status"],
                        r["delivery_commission_sar"],
                        os.path.basename(orders_path),
                        batch_month,
                    )
                )

        cursor.executemany(
            """INSERT INTO raw.orders (
                order_id, order_timestamp, order_date, branch_id, channel,
                customer_id, status, delivery_commission_sar, source_file, batch_month
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);""",
            order_rows,
        )

        # Load order lines
        line_rows = []
        with open(lines_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for r in reader:
                line_rows.append(
                    (
                        r["order_line_id"],
                        r["order_id"],
                        r["product_id"],
                        r["quantity"],
                        r["unit_price_sar"],
                        r["unit_cost_sar"],
                        r["discount_sar"],
                        os.path.basename(lines_path),
                        batch_month,
                    )
                )

        cursor.executemany(
            """INSERT INTO raw.order_lines (
                order_line_id, order_id, product_id, quantity, unit_price_sar,
                unit_cost_sar, discount_sar, source_file, batch_month
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);""",
            line_rows,
        )

        conn.commit()
        print(f"✓ Raw ingestion committed: {len(order_rows):,} orders, {len(line_rows):,} lines")

        # 3. Pre-marts Quality Gate (SQL Verification)
        cursor.execute("""
            SELECT COUNT(*) FROM staging.stg_orders
            WHERE batch_month = ? AND is_valid_branch = 0;
        """, (batch_month,))
        invalid_b_count = cursor.fetchone()[0]

        cursor.execute("""
            SELECT COUNT(*) FROM staging.stg_order_lines
            WHERE batch_month = ? AND is_valid_discount = 0;
        """, (batch_month,))
        invalid_d_count = cursor.fetchone()[0]

        if invalid_b_count > 0 or invalid_d_count > 0:
            conn.rollback()
            raise ValueError(f"Staging quality checks failed: {invalid_b_count} invalid branches, {invalid_d_count} invalid discounts.")

        # 4. Marts Promotion (in Transaction)
        cursor.execute("DELETE FROM marts.fact_order_lines WHERE batch_month = ?;", (batch_month,))
        cursor.execute("DELETE FROM marts.fact_orders WHERE batch_month = ?;", (batch_month,))

        # Promote fact_orders (grain: one completed order)
        cursor.execute("""
            INSERT INTO marts.fact_orders (
                order_id, [date], order_timestamp, branch_id, channel, customer_id,
                line_count, net_sales_sar, food_cost_sar, delivery_commission_sar, contribution_sar, batch_month
            )
            SELECT
                o.[order_id],
                o.[order_date],
                o.[order_timestamp],
                o.[branch_id],
                o.[channel],
                o.[customer_id],
                l.[line_count],
                l.[net_sales_sar],
                l.[food_cost_sar],
                o.[delivery_commission_sar],
                l.[net_sales_sar] - l.[food_cost_sar] - o.[delivery_commission_sar] AS [contribution_sar],
                o.[batch_month]
            FROM staging.stg_orders o
            INNER JOIN (
                SELECT
                    [order_id],
                    COUNT([order_line_id]) AS [line_count],
                    SUM([net_sales_sar])   AS [net_sales_sar],
                    SUM([food_cost_sar])   AS [food_cost_sar]
                FROM staging.stg_order_lines
                WHERE [batch_month] = ?
                GROUP BY [order_id]
            ) l ON o.[order_id] = l.[order_id]
            WHERE o.[status] = N'completed' AND o.[batch_month] = ?;
        """, (batch_month, batch_month))
        promoted_orders = cursor.rowcount

        # Promote fact_order_lines (grain: one completed order line)
        cursor.execute("""
            INSERT INTO marts.fact_order_lines (
                order_line_id, order_id, [date], branch_id, product_id, channel, customer_id,
                quantity, unit_price_sar, unit_cost_sar, discount_sar, net_sales_sar, food_cost_sar, batch_month
            )
            SELECT
                l.[order_line_id],
                l.[order_id],
                o.[order_date],
                o.[branch_id],
                l.[product_id],
                o.[channel],
                o.[customer_id],
                l.[quantity],
                l.[unit_price_sar],
                l.[unit_cost_sar],
                l.[discount_sar],
                l.[net_sales_sar],
                l.[food_cost_sar],
                l.[batch_month]
            FROM staging.stg_order_lines l
            INNER JOIN staging.stg_orders o ON l.[order_id] = o.[order_id]
            WHERE o.[status] = N'completed' AND l.[batch_month] = ? AND o.[batch_month] = ?;
        """, (batch_month, batch_month))
        promoted_lines = cursor.rowcount

        conn.commit()
        print(f"✓ Marts promotion committed: {promoted_orders:,} completed orders, {promoted_lines:,} lines")
        return True

    except Exception as e:
        conn.rollback()
        raise e
    finally:
        cursor.close()
        conn.close()


def main():
    parser = argparse.ArgumentParser(description="Layali POS Database Loader & Pipeline")
    parser.add_argument("--init-db", action="store_true", help="Execute scripts 01-05 to setup DB and schemas")
    parser.add_argument("--month", type=str, help="Specify single batch month YYYY-MM to load")
    parser.add_argument("--all", action="store_true", help="Load all available clean monthly batches")
    parser.add_argument("--test-quarantine", action="store_true", help="Test quarantine gate using dirty files")
    args = parser.parse_args()

    # Step 1: Initialize Database & DDL
    if args.init_db:
        init_database()
        load_master_dimensions()

    # Step 2: Handle quarantine test if requested
    if args.test_quarantine:
        print("\n=== Executing Quarantine Gate Test with Dirty Data ===")
        test_orders = os.path.join(RAW_DIRTY_DIR, "orders_2026_01_dirty.csv")
        test_lines = os.path.join(RAW_DIRTY_DIR, "order_lines_2026_01_dirty.csv")
        success = load_monthly_batch("2026-01", test_orders, test_lines)
        if not success:
            print("✓ Quarantine test PASSED: Dirty file successfully rejected and isolated.")
        else:
            print("❌ Quarantine test FAILED: Dirty file was erroneously promoted.")
        return

    # Step 3: Determine months to load
    months_to_load = []
    if args.month:
        months_to_load = [args.month]
    elif args.all:
        months_to_load = ["2026-01", "2026-02", "2026-03", "2026-04", "2026-05"]

    if months_to_load:
        load_master_dimensions()
        for ym in months_to_load:
            ym_clean = ym.replace("-", "_")
            orders_path = os.path.join(RAW_CLEAN_DIR, f"orders_{ym_clean}.csv")
            lines_path = os.path.join(RAW_CLEAN_DIR, f"order_lines_{ym_clean}.csv")
            if not os.path.exists(orders_path) or not os.path.exists(lines_path):
                print(f"Skipping {ym}: source files do not exist.")
                continue
            load_monthly_batch(ym, orders_path, lines_path)

    print("\n✓ Pipeline execution complete.")


if __name__ == "__main__":
    main()
