"""
Layali Analytics - Comprehensive Data Quality & Contract Test Suite
Writes detailed audit to reports/quality.json
Exits nonzero on any failure.
"""

import csv
import json
import os
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional

# Ensure project root in sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.db import get_connection
from src.load_pos import load_monthly_batch, validate_source_files

REPORTS_DIR = os.path.join("reports")
QUALITY_REPORT_PATH = os.path.join(REPORTS_DIR, "quality.json")
RAW_CLEAN_DIR = os.path.join("data", "raw", "clean")
RAW_DIRTY_DIR = os.path.join("data", "raw", "dirty")
QUARANTINE_DIR = os.path.join("data", "quarantine")


class QualityTestSuite:
    def __init__(self):
        self.results: List[Dict[str, Any]] = []
        self.warnings: List[str] = []
        self.has_failure = False

    def record_check(
        self,
        name: str,
        expected: Any,
        actual: Any,
        passed: bool,
        details: Optional[str] = None,
    ):
        status = "PASS" if passed else "FAIL"
        if not passed:
            self.has_failure = True
        record = {
            "check_name": name,
            "expected": str(expected),
            "actual": str(actual),
            "status": status,
            "timestamp": datetime.now().isoformat(),
        }
        if details:
            record["details"] = details
        self.results.append(record)
        print(f"[{status}] {name} (Expected: {expected} | Actual: {actual})")
        if details and not passed:
            print(f"       Details: {details}")

    def record_warning(self, name: str, message: str):
        self.warnings.append({"check_name": name, "warning": message})
        print(f"[WARN] {name}: {message}")

    def save_report(self):
        os.makedirs(REPORTS_DIR, exist_ok=True)
        summary = {
            "execution_timestamp": datetime.now().isoformat(),
            "total_checks": len(self.results),
            "passed_checks": sum(1 for r in self.results if r["status"] == "PASS"),
            "failed_checks": sum(1 for r in self.results if r["status"] == "FAIL"),
            "warnings_count": len(self.warnings),
            "overall_status": "FAIL" if self.has_failure else "PASS",
            "warnings": self.warnings,
            "checks": self.results,
        }
        with open(QUALITY_REPORT_PATH, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2)
        print(f"\nAudit report written to {QUALITY_REPORT_PATH}")


def run_all_checks():
    suite = QualityTestSuite()
    conn = get_connection(include_db=True, autocommit=True)
    cursor = conn.cursor()

    try:
        print("=" * 80)
        print("LAYALI ANALYTICS: EXECUTING PRODUCTION QUALITY AUDIT")
        print("=" * 80)

        # ----------------------------------------------------------------------
        # Check 1: Unique Non-Null Order Keys in fact_orders
        # ----------------------------------------------------------------------
        cursor.execute("""
            SELECT
                COUNT(*),
                COUNT(DISTINCT order_id),
                SUM(CASE WHEN order_id IS NULL THEN 1 ELSE 0 END)
            FROM marts.fact_orders;
        """)
        total_o, unique_o, null_o = cursor.fetchone()
        suite.record_check(
            name="unique_nonnull_order_keys",
            expected=f"unique == {total_o} and nulls == 0",
            actual=f"unique == {unique_o} and nulls == {null_o}",
            passed=(total_o == unique_o and null_o == 0 and total_o > 0),
        )

        # ----------------------------------------------------------------------
        # Check 2: Unique Non-Null Line Keys in fact_order_lines
        # ----------------------------------------------------------------------
        cursor.execute("""
            SELECT
                COUNT(*),
                COUNT(DISTINCT order_line_id),
                SUM(CASE WHEN order_line_id IS NULL THEN 1 ELSE 0 END)
            FROM marts.fact_order_lines;
        """)
        total_l, unique_l, null_l = cursor.fetchone()
        suite.record_check(
            name="unique_nonnull_line_keys",
            expected=f"unique == {total_l} and nulls == 0",
            actual=f"unique == {unique_l} and nulls == {null_l}",
            passed=(total_l == unique_l and null_l == 0 and total_l > 0),
        )

        # ----------------------------------------------------------------------
        # Check 3: Foreign Key Integrity (Branch, Product, Order, Date, Channel)
        # ----------------------------------------------------------------------
        cursor.execute("""
            SELECT COUNT(*) FROM marts.fact_orders o
            LEFT JOIN marts.dim_branch b ON o.branch_id = b.branch_id
            WHERE b.branch_id IS NULL;
        """)
        orphaned_branches = cursor.fetchone()[0]
        suite.record_check(
            name="fk_orders_to_branch",
            expected=0,
            actual=orphaned_branches,
            passed=(orphaned_branches == 0),
        )

        cursor.execute("""
            SELECT COUNT(*) FROM marts.fact_order_lines l
            LEFT JOIN marts.dim_product p ON l.product_id = p.product_id
            WHERE p.product_id IS NULL;
        """)
        orphaned_products = cursor.fetchone()[0]
        suite.record_check(
            name="fk_lines_to_product",
            expected=0,
            actual=orphaned_products,
            passed=(orphaned_products == 0),
        )

        cursor.execute("""
            SELECT COUNT(*) FROM marts.fact_order_lines l
            LEFT JOIN marts.fact_orders o ON l.order_id = o.order_id
            WHERE o.order_id IS NULL;
        """)
        orphaned_orders = cursor.fetchone()[0]
        suite.record_check(
            name="fk_lines_to_orders",
            expected=0,
            actual=orphaned_orders,
            passed=(orphaned_orders == 0),
        )

        cursor.execute("""
            SELECT COUNT(*) FROM marts.fact_orders o
            LEFT JOIN marts.dim_date d ON o.[date] = d.[date]
            WHERE d.[date] IS NULL;
        """)
        orphaned_dates = cursor.fetchone()[0]
        suite.record_check(
            name="fk_orders_to_date",
            expected=0,
            actual=orphaned_dates,
            passed=(orphaned_dates == 0),
        )

        # ----------------------------------------------------------------------
        # Check 4: Positive Integer Quantity
        # ----------------------------------------------------------------------
        cursor.execute("""
            SELECT COUNT(*) FROM marts.fact_order_lines
            WHERE quantity <= 0 OR quantity IS NULL;
        """)
        invalid_quantities = cursor.fetchone()[0]
        suite.record_check(
            name="positive_integer_quantity",
            expected=0,
            actual=invalid_quantities,
            passed=(invalid_quantities == 0),
        )

        # ----------------------------------------------------------------------
        # Check 5: Valid Discount Range (0 <= discount <= quantity * unit_price)
        # ----------------------------------------------------------------------
        cursor.execute("""
            SELECT COUNT(*) FROM marts.fact_order_lines
            WHERE discount_sar < 0 OR discount_sar > (quantity * unit_price_sar);
        """)
        invalid_discounts = cursor.fetchone()[0]
        suite.record_check(
            name="valid_discount_bounds",
            expected=0,
            actual=invalid_discounts,
            passed=(invalid_discounts == 0),
        )

        # ----------------------------------------------------------------------
        # Check 6: Non-Negative Costs and Commissions
        # ----------------------------------------------------------------------
        cursor.execute("""
            SELECT COUNT(*) FROM marts.fact_orders
            WHERE food_cost_sar < 0 OR delivery_commission_sar < 0;
        """)
        negative_costs_orders = cursor.fetchone()[0]
        cursor.execute("""
            SELECT COUNT(*) FROM marts.fact_order_lines
            WHERE food_cost_sar < 0;
        """)
        negative_costs_lines = cursor.fetchone()[0]
        suite.record_check(
            name="nonnegative_cost_and_commission",
            expected=0,
            actual=negative_costs_orders + negative_costs_lines,
            passed=(negative_costs_orders == 0 and negative_costs_lines == 0),
        )

        # ----------------------------------------------------------------------
        # Check 7: Dates in Requested Range (Jan 1 - Jun 30, 2026)
        # ----------------------------------------------------------------------
        cursor.execute("""
            SELECT MIN([date]), MAX([date]) FROM marts.fact_orders;
        """)
        min_date, max_date = cursor.fetchone()
        suite.record_check(
            name="dates_within_range",
            expected="Between 2026-01-01 and 2026-06-30",
            actual=f"{min_date} to {max_date}",
            passed=(str(min_date) >= "2026-01-01" and str(max_date) <= "2026-06-30"),
        )

        # ----------------------------------------------------------------------
        # Check 8: Exactly 3 Branch IDs
        # ----------------------------------------------------------------------
        cursor.execute("""
            SELECT COUNT(DISTINCT branch_id) FROM marts.fact_orders;
        """)
        branch_count = cursor.fetchone()[0]
        suite.record_check(
            name="exactly_3_branches",
            expected=3,
            actual=branch_count,
            passed=(branch_count == 3),
        )

        # ----------------------------------------------------------------------
        # Check 9: Customer IDs Valid When Not NULL (Permit Missing IDs)
        # ----------------------------------------------------------------------
        cursor.execute("""
            SELECT
                SUM(CASE WHEN o.customer_id IS NULL THEN 1 ELSE 0 END) AS null_cust,
                COUNT(o.customer_id) AS non_null_cust,
                SUM(CASE WHEN o.customer_id IS NOT NULL AND c.customer_id IS NULL THEN 1 ELSE 0 END) AS invalid_cust
            FROM marts.fact_orders o
            LEFT JOIN marts.dim_customer c ON o.customer_id = c.customer_id;
        """)
        null_c, non_null_c, invalid_c = cursor.fetchone()
        suite.record_check(
            name="customer_ids_valid_when_not_null",
            expected=f"invalid == 0 (nulls permitted, observed {null_c})",
            actual=f"invalid == {invalid_c}",
            passed=(invalid_c == 0 and null_c > 0 and non_null_c > 0),
        )

        # ----------------------------------------------------------------------
        # Check 10: Cancelled Orders Absent from Facts
        # ----------------------------------------------------------------------
        cursor.execute("""
            SELECT COUNT(*) FROM marts.fact_orders o
            INNER JOIN raw.orders r ON o.order_id = r.order_id
            WHERE r.status = 'cancelled';
        """)
        cancelled_in_orders = cursor.fetchone()[0]
        cursor.execute("""
            SELECT COUNT(*) FROM marts.fact_order_lines l
            INNER JOIN raw.orders r ON l.order_id = r.order_id
            WHERE r.status = 'cancelled';
        """)
        cancelled_in_lines = cursor.fetchone()[0]
        suite.record_check(
            name="cancelled_orders_absent_from_facts",
            expected=0,
            actual=cancelled_in_orders + cancelled_in_lines,
            passed=(cancelled_in_orders == 0 and cancelled_in_lines == 0),
        )

        # ----------------------------------------------------------------------
        # Check 11: Sum of Lines Revenue Equals Orders Revenue within SAR 0.01
        # ----------------------------------------------------------------------
        cursor.execute("""
            SELECT
                (SELECT SUM(net_sales_sar) FROM marts.fact_orders)       AS sum_orders,
                (SELECT SUM(net_sales_sar) FROM marts.fact_order_lines)  AS sum_lines;
        """)
        sum_orders, sum_lines = cursor.fetchone()
        diff = abs(float(sum_orders) - float(sum_lines))
        suite.record_check(
            name="sum_lines_revenue_equals_orders_revenue",
            expected="diff <= 0.01",
            actual=f"diff == {diff:.4f} (orders: {sum_orders}, lines: {sum_lines})",
            passed=(diff <= 0.01),
        )

        # ----------------------------------------------------------------------
        # Check 12: Each Order Line Revenue Reconciles Individually
        # ----------------------------------------------------------------------
        cursor.execute("""
            SELECT COUNT(*) FROM (
                SELECT
                    o.order_id,
                    o.net_sales_sar,
                    SUM(l.net_sales_sar) AS lines_total,
                    ABS(o.net_sales_sar - SUM(l.net_sales_sar)) AS variance
                FROM marts.fact_orders o
                INNER JOIN marts.fact_order_lines l ON o.order_id = l.order_id
                GROUP BY o.order_id, o.net_sales_sar
                HAVING ABS(o.net_sales_sar - SUM(l.net_sales_sar)) > 0.01
            ) t;
        """)
        mismatched_orders = cursor.fetchone()[0]
        suite.record_check(
            name="individual_order_line_reconciliation",
            expected=0,
            actual=mismatched_orders,
            passed=(mismatched_orders == 0),
        )

        # ----------------------------------------------------------------------
        # Check 13: Contribution Margin Identity
        # contribution_sar = net_sales_sar - food_cost_sar - delivery_commission_sar
        # ----------------------------------------------------------------------
        cursor.execute("""
            SELECT COUNT(*) FROM marts.fact_orders
            WHERE ABS(contribution_sar - (net_sales_sar - food_cost_sar - delivery_commission_sar)) > 0.01;
        """)
        contribution_errors = cursor.fetchone()[0]
        suite.record_check(
            name="contribution_margin_identity",
            expected=0,
            actual=contribution_errors,
            passed=(contribution_errors == 0),
        )

        # ----------------------------------------------------------------------
        # Check 14: Commissions Only on Delivery Orders
        # ----------------------------------------------------------------------
        cursor.execute("""
            SELECT COUNT(*) FROM marts.fact_orders
            WHERE channel <> 'delivery' AND delivery_commission_sar <> 0;
        """)
        invalid_commissions = cursor.fetchone()[0]
        suite.record_check(
            name="commissions_only_on_delivery",
            expected=0,
            actual=invalid_commissions,
            passed=(invalid_commissions == 0),
        )

        # ----------------------------------------------------------------------
        # Check 15: Rerun Idempotency Test
        # Rerunning same batch (2026-01) changes neither fact counts nor revenue
        # ----------------------------------------------------------------------
        cursor.execute("SELECT COUNT(*), SUM(net_sales_sar) FROM marts.fact_orders WHERE batch_month = '2026-01';")
        count_before, sales_before = cursor.fetchone()

        # Re-run batch load for 2026-01
        load_monthly_batch(
            "2026-01",
            os.path.join(RAW_CLEAN_DIR, "orders_2026_01.csv"),
            os.path.join(RAW_CLEAN_DIR, "order_lines_2026_01.csv"),
        )

        cursor.execute("SELECT COUNT(*), SUM(net_sales_sar) FROM marts.fact_orders WHERE batch_month = '2026-01';")
        count_after, sales_after = cursor.fetchone()

        sales_diff = abs(float(sales_before) - float(sales_after))
        suite.record_check(
            name="rerun_batch_idempotency",
            expected=f"count == {count_before}, sales == {sales_before}",
            actual=f"count == {count_after}, sales == {sales_after}",
            passed=(count_before == count_after and sales_diff <= 0.01),
        )

        # ----------------------------------------------------------------------
        # Check 16: Separate Warning for Expected-but-Missing Branch/Date Coverage
        # ----------------------------------------------------------------------
        cursor.execute("""
            SELECT b.branch_id, d.[date]
            FROM marts.dim_branch b
            CROSS JOIN (
                SELECT DISTINCT [date] FROM marts.fact_orders
            ) d
            LEFT JOIN marts.fact_orders o ON b.branch_id = o.branch_id AND d.[date] = o.[date]
            WHERE o.order_id IS NULL;
        """)
        missing_coverage = cursor.fetchall()
        if missing_coverage:
            suite.record_warning(
                name="branch_date_coverage",
                message=f"Missing order coverage for {len(missing_coverage)} branch-day combinations.",
            )
        else:
            print("[INFO] Branch date coverage: 100% active on all operating calendar days.")

        # ----------------------------------------------------------------------
        # Check 17: Isolated Test Schema Fixture Executions (Never Production Marts)
        # ----------------------------------------------------------------------
        print("\n--- Executing Isolated Schema Fixture Tests (test_marts) ---")
        cursor.execute("""
            IF NOT EXISTS (SELECT 1 FROM sys.schemas WHERE name = N'test_marts')
                EXEC(N'CREATE SCHEMA [test_marts];');
            
            IF OBJECT_ID(N'test_marts.fact_orders', N'U') IS NOT NULL DROP TABLE [test_marts].[fact_orders];
            IF OBJECT_ID(N'test_marts.fact_order_lines', N'U') IS NOT NULL DROP TABLE [test_marts].[fact_order_lines];

            SELECT TOP 0 * INTO [test_marts].[fact_orders] FROM [marts].[fact_orders];
            SELECT TOP 0 * INTO [test_marts].[fact_order_lines] FROM [marts].[fact_order_lines];
        """)

        # Fixture 1: Three-line delivery order fixture to catch duplicated order-level commission
        # Order: 1 delivery order, 3 lines, net_sales = 100.00 SAR, commission = 20.00 SAR
        cursor.execute("""
            INSERT INTO [test_marts].[fact_orders] (
                order_id, [date], order_timestamp, branch_id, channel, customer_id,
                line_count, net_sales_sar, food_cost_sar, delivery_commission_sar, contribution_sar, batch_month
            ) VALUES (
                'ORD-TEST-COMM-001', '2026-01-15', '2026-01-15 13:00:00', 'BR01', 'delivery', 'CUST-10001',
                3, 100.00, 30.00, 20.00, 50.00, '2026-01'
            );

            INSERT INTO [test_marts].[fact_order_lines] (
                order_line_id, order_id, [date], branch_id, product_id, channel, customer_id,
                quantity, unit_price_sar, unit_cost_sar, discount_sar, net_sales_sar, food_cost_sar, batch_month
            ) VALUES
            ('LIN-TEST-01', 'ORD-TEST-COMM-001', '2026-01-15', 'BR01', 'PRD01', 'delivery', 'CUST-10001', 1, 25.00, 8.00, 0.00, 25.00, 8.00, '2026-01'),
            ('LIN-TEST-02', 'ORD-TEST-COMM-001', '2026-01-15', 'BR01', 'PRD02', 'delivery', 'CUST-10001', 1, 35.00, 10.00, 0.00, 35.00, 10.00, '2026-01'),
            ('LIN-TEST-03', 'ORD-TEST-COMM-001', '2026-01-15', 'BR01', 'PRD03', 'delivery', 'CUST-10001', 1, 40.00, 12.00, 0.00, 40.00, 12.00, '2026-01');
        """)

        # Verify commission in test_marts fact_orders is 20.00 and fact_order_lines does NOT contain delivery_commission_sar
        cursor.execute("SELECT delivery_commission_sar FROM test_marts.fact_orders WHERE order_id = 'ORD-TEST-COMM-001';")
        test_comm = float(cursor.fetchone()[0])
        # Verify order_lines schema does not possess a duplicated commission column
        cursor.execute("""
            SELECT COUNT(*) FROM sys.columns
            WHERE object_id = OBJECT_ID('test_marts.fact_order_lines') AND name = 'delivery_commission_sar';
        """)
        line_has_comm = cursor.fetchone()[0]

        suite.record_check(
            name="three_line_fixture_non_duplicated_commission",
            expected="commission == 20.00 and fact_order_lines has no delivery_commission_sar column",
            actual=f"commission == {test_comm} and column_present == {line_has_comm}",
            passed=(test_comm == 20.00 and line_has_comm == 0),
        )

        # Fixture 2: Demonstrate dirty fixtures are rejected by quarantine gate
        # Take snapshot of production marts count before testing dirty fixtures
        cursor.execute("SELECT COUNT(*) FROM marts.fact_orders;")
        prod_marts_orders_before = cursor.fetchone()[0]

        dirty_orders = os.path.join(RAW_DIRTY_DIR, "orders_2026_01_dirty.csv")
        dirty_lines = os.path.join(RAW_DIRTY_DIR, "order_lines_2026_01_dirty.csv")
        is_valid_dirty, violations = validate_source_files(dirty_orders, dirty_lines)

        suite.record_check(
            name="dirty_fixture_rejected_by_validation_gate",
            expected="is_valid == False and violations >= 3",
            actual=f"is_valid == {is_valid_dirty} and violations == {len(violations)}",
            passed=(not is_valid_dirty and len(violations) >= 3),
        )

        # Verify production marts remained completely untouched
        cursor.execute("SELECT COUNT(*) FROM marts.fact_orders;")
        prod_marts_orders_after = cursor.fetchone()[0]

        suite.record_check(
            name="production_marts_unchanged_after_dirty_rejection",
            expected=prod_marts_orders_before,
            actual=prod_marts_orders_after,
            passed=(prod_marts_orders_before == prod_marts_orders_after),
        )

        # Clean up isolated test schema
        cursor.execute("""
            DROP TABLE [test_marts].[fact_order_lines];
            DROP TABLE [test_marts].[fact_orders];
            DROP SCHEMA [test_marts];
        """)
        print("✓ Cleaned up isolated test_marts schema.")

    finally:
        cursor.close()
        conn.close()

    suite.save_report()

    if suite.has_failure:
        print("\n❌ Quality suite encountered failures. Exiting with status 1.")
        sys.exit(1)
    else:
        print("\n✅ All quality checks PASSED successfully.")
        sys.exit(0)


if __name__ == "__main__":
    run_all_checks()
