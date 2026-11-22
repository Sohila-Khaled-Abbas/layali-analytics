"""
Layali Analytics - Unit and Data Contract Tests for POS Generator
"""

import os
import pandas as pd
import pytest


RAW_CLEAN_DIR = os.path.join("data", "raw", "clean")
RAW_DIRTY_DIR = os.path.join("data", "raw", "dirty")


def test_master_catalogs():
    """Verify master entity catalogs."""
    branches_path = os.path.join(RAW_CLEAN_DIR, "branches.csv")
    products_path = os.path.join(RAW_CLEAN_DIR, "products.csv")
    customers_path = os.path.join(RAW_CLEAN_DIR, "customers.csv")

    assert os.path.exists(branches_path), "branches.csv missing"
    assert os.path.exists(products_path), "products.csv missing"
    assert os.path.exists(customers_path), "customers.csv missing"

    df_b = pd.read_csv(branches_path)
    df_p = pd.read_csv(products_path)
    df_c = pd.read_csv(customers_path)

    # 3 branches
    assert len(df_b) == 3
    assert set(df_b["branch_id"]) == {"BR01", "BR02", "BR03"}

    # 25 fixed products
    assert len(df_p) == 25
    assert df_p["product_id"].nunique() == 25
    assert set(df_p["category"].unique()) == {"Appetizers", "Grills", "Rice & Mains", "Desserts", "Beverages"}

    # 5000 customers
    assert len(df_c) == 5000
    assert df_c["customer_id"].nunique() == 5000


def test_clean_batches_holdout():
    """Verify Jan-May clean batches exist and June is held out."""
    for ym in ["2026_01", "2026_02", "2026_03", "2026_04", "2026_05"]:
        assert os.path.exists(os.path.join(RAW_CLEAN_DIR, f"orders_{ym}.csv"))
        assert os.path.exists(os.path.join(RAW_CLEAN_DIR, f"order_lines_{ym}.csv"))

    # June must be held out
    assert not os.path.exists(os.path.join(RAW_CLEAN_DIR, "orders_2026_06.csv")), "June clean batch should be held out"


def test_delivery_commission_contract():
    """Verify 20% delivery commission on completed delivery orders and 0 otherwise."""
    df_orders = pd.read_csv(os.path.join(RAW_CLEAN_DIR, "orders_2026_01.csv"))
    df_lines = pd.read_csv(os.path.join(RAW_CLEAN_DIR, "order_lines_2026_01.csv"))

    df_lines["net_sales"] = (df_lines["quantity"] * df_lines["unit_price_sar"]) - df_lines["discount_sar"]
    order_totals = df_lines.groupby("order_id")["net_sales"].sum().round(2).to_dict()

    for _, row in df_orders.head(500).iterrows():
        oid = row["order_id"]
        status = row["status"]
        channel = row["channel"]
        comm = row["delivery_commission_sar"]

        if status == "completed" and channel == "delivery":
            expected_comm = round(0.20 * order_totals[oid], 2)
            assert comm == expected_comm, f"Order {oid} commission mismatch: {comm} vs {expected_comm}"
        else:
            assert comm == 0.0, f"Order {oid} non-delivery/cancelled should have 0 commission, got {comm}"


def test_obhur_shift_anomaly():
    """Verify planted Obhur reduction and delivery shift starting in April."""
    df_jan = pd.read_csv(os.path.join(RAW_CLEAN_DIR, "orders_2026_01.csv"))
    df_may = pd.read_csv(os.path.join(RAW_CLEAN_DIR, "orders_2026_05.csv"))

    # Obhur Jan vs May volume
    obhur_jan_orders = len(df_jan[df_jan["branch_id"] == "BR03"])
    obhur_may_orders = len(df_may[df_may["branch_id"] == "BR03"])
    assert obhur_may_orders < obhur_jan_orders, "Obhur order volume did not drop in May"

    # Obhur delivery channel share Jan vs May
    jan_obhur_deliv_pct = (df_jan[df_jan["branch_id"] == "BR03"]["channel"] == "delivery").mean()
    may_obhur_deliv_pct = (df_may[df_may["branch_id"] == "BR03"]["channel"] == "delivery").mean()
    assert jan_obhur_deliv_pct < 0.30, f"Expected Jan delivery ~25%, got {jan_obhur_deliv_pct:.2f}"
    assert may_obhur_deliv_pct > 0.50, f"Expected May delivery >50%, got {may_obhur_deliv_pct:.2f}"


def test_dirty_manifest():
    """Verify dirty batches exist and manifest logs corruptions."""
    manifest_csv = os.path.join(RAW_DIRTY_DIR, "manifest.csv")
    assert os.path.exists(manifest_csv), "manifest.csv missing"

    df_man = pd.read_csv(manifest_csv)
    assert len(df_man) > 0
    defect_types = set(df_man["defect_type"].unique())
    assert "duplicate_line" in defect_types
    assert "invalid_branch_key" in defect_types
    assert "invalid_discount_exceeds_gross" in defect_types
    assert "invalid_negative_discount" in defect_types
