"""
Layali Analytics - Synthetic POS Data Generator
Stack: Python, pandas, numpy
Fixed Seed: 42
Date Range: 2026-01-01 to 2026-06-30 (Asia/Riyadh local operating hours)
Branches: Al Rawdah (BR01), Al Hamra (BR02), Obhur (BR03)
"""

import argparse
import json
import os
from datetime import date, datetime, timedelta
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd

# Constants & Configuration
FIXED_SEED = 42
START_DATE = date(2026, 1, 1)
END_DATE = date(2026, 6, 30)
DEFAULT_MONTHS = ["2026-01", "2026-02", "2026-03", "2026-04", "2026-05"]
HOLDOUT_MONTH = "2026-06"
ALL_MONTHS = DEFAULT_MONTHS + [HOLDOUT_MONTH]

RAW_CLEAN_DIR = os.path.join("data", "raw", "clean")
RAW_DIRTY_DIR = os.path.join("data", "raw", "dirty")

# Master Branches Catalog
BRANCHES = [
    {
        "branch_id": "BR01",
        "branch_name": "Al Rawdah",
        "opened_date": "2021-03-15",
    },
    {
        "branch_id": "BR02",
        "branch_name": "Al Hamra",
        "opened_date": "2022-08-01",
    },
    {
        "branch_id": "BR03",
        "branch_name": "Obhur",
        "opened_date": "2024-05-10",
    },
]

# Master Products Catalog: 25 Fixed Menu Items
PRODUCTS = [
    # Appetizers (5 items)
    {"product_id": "PRD01", "product_name": "Hummus Bil Tahina", "category": "Appetizers", "unit_price_sar": 22.00, "unit_cost_sar": 5.50},
    {"product_id": "PRD02", "product_name": "Mutabbal Eggplant", "category": "Appetizers", "unit_price_sar": 24.00, "unit_cost_sar": 6.00},
    {"product_id": "PRD03", "product_name": "Fattoush Salad", "category": "Appetizers", "unit_price_sar": 26.00, "unit_cost_sar": 6.50},
    {"product_id": "PRD04", "product_name": "Tabbouleh", "category": "Appetizers", "unit_price_sar": 25.00, "unit_cost_sar": 6.25},
    {"product_id": "PRD05", "product_name": "Sambousek Meat & Cheese", "category": "Appetizers", "unit_price_sar": 28.00, "unit_cost_sar": 7.50},
    # Grills (5 items)
    {"product_id": "PRD06", "product_name": "Shish Tawook Skewers", "category": "Grills", "unit_price_sar": 58.00, "unit_cost_sar": 18.50},
    {"product_id": "PRD07", "product_name": "Lamb Kebab Skewers", "category": "Grills", "unit_price_sar": 68.00, "unit_cost_sar": 24.00},
    {"product_id": "PRD08", "product_name": "Mixed Grill Platter", "category": "Grills", "unit_price_sar": 95.00, "unit_cost_sar": 35.00},
    {"product_id": "PRD09", "product_name": "Grilled Ribeye Steak Tikka", "category": "Grills", "unit_price_sar": 85.00, "unit_cost_sar": 32.00},
    {"product_id": "PRD10", "product_name": "Grilled Jumbo Prawns", "category": "Grills", "unit_price_sar": 110.00, "unit_cost_sar": 42.00},
    # Rice & Mains (5 items)
    {"product_id": "PRD11", "product_name": "Traditional Lamb Kabsa", "category": "Rice & Mains", "unit_price_sar": 75.00, "unit_cost_sar": 26.00},
    {"product_id": "PRD12", "product_name": "Chicken Mandi", "category": "Rice & Mains", "unit_price_sar": 48.00, "unit_cost_sar": 15.00},
    {"product_id": "PRD13", "product_name": "Sayadieh Fish & Rice", "category": "Rice & Mains", "unit_price_sar": 65.00, "unit_cost_sar": 22.00},
    {"product_id": "PRD14", "product_name": "Lamb Shank Madghout", "category": "Rice & Mains", "unit_price_sar": 88.00, "unit_cost_sar": 32.00},
    {"product_id": "PRD15", "product_name": "Oven-baked Musakhan", "category": "Rice & Mains", "unit_price_sar": 52.00, "unit_cost_sar": 17.00},
    # Desserts (5 items)
    {"product_id": "PRD16", "product_name": "Cheese Kunafa", "category": "Desserts", "unit_price_sar": 32.00, "unit_cost_sar": 9.00},
    {"product_id": "PRD17", "product_name": "Umm Ali", "category": "Desserts", "unit_price_sar": 28.00, "unit_cost_sar": 7.50},
    {"product_id": "PRD18", "product_name": "Date Pudding with Caramel", "category": "Desserts", "unit_price_sar": 35.00, "unit_cost_sar": 9.50},
    {"product_id": "PRD19", "product_name": "Pistachio Baklava Selection", "category": "Desserts", "unit_price_sar": 38.00, "unit_cost_sar": 12.00},
    {"product_id": "PRD20", "product_name": "Muhallabia with Rose Water", "category": "Desserts", "unit_price_sar": 20.00, "unit_cost_sar": 4.50},
    # Beverages (5 items)
    {"product_id": "PRD21", "product_name": "Saudi Specialty Coffee Dallah", "category": "Beverages", "unit_price_sar": 30.00, "unit_cost_sar": 6.00},
    {"product_id": "PRD22", "product_name": "Fresh Mint Lemonade", "category": "Beverages", "unit_price_sar": 18.00, "unit_cost_sar": 3.50},
    {"product_id": "PRD23", "product_name": "Pomegranate Virgin Mojito", "category": "Beverages", "unit_price_sar": 24.00, "unit_cost_sar": 5.00},
    {"product_id": "PRD24", "product_name": "Karak Tea Pot", "category": "Beverages", "unit_price_sar": 16.00, "unit_cost_sar": 3.00},
    {"product_id": "PRD25", "product_name": "Sparkling Mineral Water 750ml", "category": "Beverages", "unit_price_sar": 15.00, "unit_cost_sar": 3.50},
]

# Pre-generate 5,000 synthetic customer IDs
NUM_CUSTOMERS = 5000
CUSTOMER_IDS = [f"CUST-{10001 + i}" for i in range(NUM_CUSTOMERS)]

# Weights for repeat customer sampling (power law / Pareto-style frequency)
_cust_rng = np.random.default_rng(FIXED_SEED)
_weights = 1.0 / (np.arange(1, NUM_CUSTOMERS + 1) ** 0.65)
CUSTOMER_WEIGHTS = _weights / _weights.sum()


def get_day_seed(target_date: date, branch_idx: int) -> int:
    """Generate a deterministic, unique seed per day and branch for stable reruns."""
    day_offset = (target_date - START_DATE).days
    return FIXED_SEED + day_offset * 1000 + branch_idx * 10


def generate_day_orders(
    target_date: date,
    branch_idx: int,
    branch_id: str,
) -> Tuple[List[Dict], List[Dict]]:
    """Generate orders and order lines for a specific branch and calendar date."""
    rng = np.random.default_rng(get_day_seed(target_date, branch_idx))

    # Day of week weighting (0 = Monday, ..., 4 = Friday, 5 = Saturday, 6 = Sunday)
    dow = target_date.weekday()
    dow_multipliers = {
        0: 0.95,  # Monday
        1: 0.95,  # Tuesday
        2: 1.00,  # Wednesday
        3: 1.20,  # Thursday
        4: 1.45,  # Friday (Peak family dining)
        5: 1.30,  # Saturday (Weekend leisure)
        6: 0.90,  # Sunday
    }
    dow_mult = dow_multipliers.get(dow, 1.0)

    # Baseline: 80 - 160 orders/day (mean ~115)
    base_orders = rng.integers(85, 140)
    expected_orders = int(round(base_orders * dow_mult))

    # Planted Assumption: Obhur volume reduction by 20% starting April 1, 2026
    is_obhur = branch_id == "BR03"
    is_post_march = target_date >= date(2026, 4, 1)

    if is_obhur and is_post_march:
        expected_orders = int(round(expected_orders * 0.80))

    # Channels and probabilities
    if is_obhur and is_post_march:
        # Shift Obhur mix toward delivery
        channels = ["dine-in", "takeaway", "delivery"]
        channel_probs = [0.20, 0.25, 0.55]
    else:
        # Standard baseline channel mix
        channels = ["dine-in", "takeaway", "delivery"]
        channel_probs = [0.45, 0.30, 0.25]

    orders = []
    order_lines = []

    date_str = target_date.isoformat()
    date_compact = target_date.strftime("%Y%m%d")

    # Time distribution (Asia/Riyadh local operating hours)
    # Lunch: 12:00 - 15:30 (35%), Afternoon: 15:30 - 18:30 (10%), Dinner: 18:30 - 23:45 (55%)
    time_slots = ["lunch", "afternoon", "dinner"]
    slot_probs = [0.35, 0.10, 0.55]

    for order_seq in range(1, expected_orders + 1):
        order_id = f"ORD-{date_compact}-{branch_id}-{order_seq:04d}"

        # Assign time within operating hours
        slot = rng.choice(time_slots, p=slot_probs)
        if slot == "lunch":
            hour = rng.integers(12, 16)
            minute = rng.integers(0, 60)
            second = rng.integers(0, 60)
        elif slot == "afternoon":
            hour = rng.integers(16, 19)
            minute = rng.integers(0, 60)
            second = rng.integers(0, 60)
        else:
            hour = rng.integers(19, 24)
            minute = rng.integers(0, 60)
            second = rng.integers(0, 60)

        order_timestamp = f"{date_str} {hour:02d}:{minute:02d}:{second:02d}"

        channel = rng.choice(channels, p=channel_probs)

        # 25% of orders are anonymous; 75% are repeat customers
        is_anonymous = rng.random() < 0.25
        if is_anonymous:
            customer_id = None
        else:
            customer_id = rng.choice(CUSTOMER_IDS, p=CUSTOMER_WEIGHTS)

        # Order status: realistic cancellation rates
        if channel == "dine-in":
            status = "completed" if rng.random() >= 0.01 else "cancelled"
        elif channel == "takeaway":
            status = "completed" if rng.random() >= 0.02 else "cancelled"
        else:  # delivery
            status = "completed" if rng.random() >= 0.05 else "cancelled"

        # Generate 1 to 5 lines per order (mixed basket)
        num_lines = rng.choice([1, 2, 3, 4, 5], p=[0.15, 0.30, 0.30, 0.15, 0.10])
        chosen_indices = rng.choice(len(PRODUCTS), size=num_lines, replace=False)

        order_line_subtotals = []
        for line_idx, prod_idx in enumerate(chosen_indices, start=1):
            prod = PRODUCTS[prod_idx]
            order_line_id = f"LIN-{date_compact}-{branch_id}-{order_seq:04d}-{line_idx:02d}"
            quantity = int(rng.choice([1, 2, 3, 4], p=[0.65, 0.25, 0.07, 0.03]))
            unit_price = prod["unit_price_sar"]
            unit_cost = prod["unit_cost_sar"]
            gross = round(quantity * unit_price, 2)

            # Discount logic: 85% no discount, 15% promotional discount (10%, 15%, 20% off)
            has_discount = rng.random() < 0.15
            if has_discount:
                discount_pct = rng.choice([0.10, 0.15, 0.20])
                discount_sar = round(gross * discount_pct, 2)
            else:
                discount_sar = 0.00

            net_line_sales = round(gross - discount_sar, 2)
            order_line_subtotals.append(net_line_sales)

            order_lines.append(
                {
                    "order_line_id": order_line_id,
                    "order_id": order_id,
                    "product_id": prod["product_id"],
                    "quantity": quantity,
                    "unit_price_sar": unit_price,
                    "unit_cost_sar": unit_cost,
                    "discount_sar": discount_sar,
                }
            )

        # Delivery Commission: exactly 20% of net sales for completed delivery orders; 0 otherwise
        if status == "completed" and channel == "delivery":
            order_net_total = sum(order_line_subtotals)
            delivery_commission_sar = round(0.20 * order_net_total, 2)
        else:
            delivery_commission_sar = 0.00

        orders.append(
            {
                "order_id": order_id,
                "order_timestamp": order_timestamp,
                "order_date": date_str,
                "branch_id": branch_id,
                "channel": channel,
                "customer_id": customer_id if customer_id else "",
                "status": status,
                "delivery_commission_sar": delivery_commission_sar,
            }
        )

    return orders, order_lines


def generate_month_data(year_month: str) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Generate all orders and order lines for a specific YYYY-MM."""
    year, month = map(int, year_month.split("-"))
    start = date(year, month, 1)
    if month == 12:
        end = date(year + 1, 1, 1) - timedelta(days=1)
    else:
        end = date(year, month + 1, 1) - timedelta(days=1)

    all_orders = []
    all_lines = []

    cur_date = start
    while cur_date <= end:
        for branch_idx, branch in enumerate(BRANCHES):
            orders, lines = generate_day_orders(cur_date, branch_idx, branch["branch_id"])
            all_orders.extend(orders)
            all_lines.extend(lines)
        cur_date += timedelta(days=1)

    df_orders = pd.DataFrame(all_orders)
    df_lines = pd.DataFrame(all_lines)
    return df_orders, df_lines


def save_master_data():
    """Save master tables (branches, products, customers) under clean raw storage."""
    os.makedirs(RAW_CLEAN_DIR, exist_ok=True)

    branches_path = os.path.join(RAW_CLEAN_DIR, "branches.csv")
    products_path = os.path.join(RAW_CLEAN_DIR, "products.csv")
    customers_path = os.path.join(RAW_CLEAN_DIR, "customers.csv")

    if not os.path.exists(branches_path):
        pd.DataFrame(BRANCHES).to_csv(branches_path, index=False)
    if not os.path.exists(products_path):
        pd.DataFrame(PRODUCTS).to_csv(products_path, index=False)
    if not os.path.exists(customers_path):
        pd.DataFrame([{"customer_id": cid} for cid in CUSTOMER_IDS]).to_csv(customers_path, index=False)


def create_dirty_copies(
    df_orders: pd.DataFrame,
    df_lines: pd.DataFrame,
    year_month: str,
) -> Tuple[pd.DataFrame, pd.DataFrame, List[Dict]]:
    """Create dirty copies with planted defects and generate corruption manifest."""
    rng = np.random.default_rng(FIXED_SEED + int(year_month.replace("-", "")))
    manifest_entries = []

    dirty_orders = df_orders.copy()
    dirty_lines = df_lines.copy()

    # 1. Defect: Duplicate lines (duplicate 3 random lines)
    dup_indices = rng.choice(len(dirty_lines), size=3, replace=False)
    dup_rows = dirty_lines.iloc[dup_indices].copy()
    for _, row in dup_rows.iterrows():
        manifest_entries.append(
            {
                "month": year_month,
                "table": "order_lines",
                "defect_type": "duplicate_line",
                "record_id": row["order_line_id"],
                "details": f"Duplicate injection for order {row['order_id']} and product {row['product_id']}",
            }
        )
    dirty_lines = pd.concat([dirty_lines, dup_rows], ignore_index=True)

    # 2. Defect: Invalid branch keys in orders (corrupt 2 orders with non-existent 'BR99')
    completed_orders_idx = dirty_orders[dirty_orders["status"] == "completed"].index.to_numpy()
    corrupt_branch_idx = rng.choice(completed_orders_idx, size=2, replace=False)
    for idx in corrupt_branch_idx:
        orig_branch = dirty_orders.at[idx, "branch_id"]
        order_id = dirty_orders.at[idx, "order_id"]
        dirty_orders.at[idx, "branch_id"] = "BR99"
        manifest_entries.append(
            {
                "month": year_month,
                "table": "orders",
                "defect_type": "invalid_branch_key",
                "record_id": order_id,
                "details": f"Changed branch_id from {orig_branch} to invalid foreign key 'BR99'",
            }
        )

    # 3. Defect: Invalid discounts in order lines
    # a. Discount greater than line gross (resulting in negative net sales)
    line_indices = rng.choice(len(dirty_lines) - 3, size=2, replace=False)
    for idx in line_indices:
        lid = dirty_lines.at[idx, "order_line_id"]
        qty = dirty_lines.at[idx, "quantity"]
        price = dirty_lines.at[idx, "unit_price_sar"]
        gross = round(qty * price, 2)
        invalid_discount = round(gross * 1.5, 2)
        dirty_lines.at[idx, "discount_sar"] = invalid_discount
        manifest_entries.append(
            {
                "month": year_month,
                "table": "order_lines",
                "defect_type": "invalid_discount_exceeds_gross",
                "record_id": lid,
                "details": f"Discount {invalid_discount} SAR exceeds gross {gross} SAR (Qty {qty} @ {price})",
            }
        )

    # b. Negative discount
    neg_indices = rng.choice([i for i in range(len(dirty_lines) - 3) if i not in line_indices], size=2, replace=False)
    for idx in neg_indices:
        lid = dirty_lines.at[idx, "order_line_id"]
        dirty_lines.at[idx, "discount_sar"] = -25.00
        manifest_entries.append(
            {
                "month": year_month,
                "table": "order_lines",
                "defect_type": "invalid_negative_discount",
                "record_id": lid,
                "details": "Discount set to negative value -25.00 SAR",
            }
        )

    return dirty_orders, dirty_lines, manifest_entries


def print_batch_summary(
    year_month: str,
    df_orders: pd.DataFrame,
    df_lines: pd.DataFrame,
):
    """Print comprehensive summary metrics, counts, and sample records."""
    print("=" * 80)
    print(f"BATCH AUDIT REPORT: {year_month}")
    print("=" * 80)

    # Date ranges
    print(f"Date Range: {df_orders['order_date'].min()} to {df_orders['order_date'].max()}")
    print(f"Total Orders: {len(df_orders):,}")
    print(f"Total Order Lines: {len(df_lines):,}")
    print(f"Unique Order IDs: {df_orders['order_id'].nunique():,}")
    print(f"Unique Order Line IDs: {df_lines['order_line_id'].nunique():,}")

    # Counts per branch and channel
    print("\n--- Orders by Branch & Status ---")
    branch_summary = df_orders.groupby(["branch_id", "status"]).size().unstack(fill_value=0)
    print(branch_summary)

    print("\n--- Channel Distribution by Branch (%) ---")
    channel_mix = pd.crosstab(df_orders["branch_id"], df_orders["channel"], normalize="index") * 100
    print(channel_mix.round(2))

    # Financial aggregations
    df_merged = df_lines.merge(
        df_orders[["order_id", "branch_id", "channel", "status"]],
        on="order_id",
        how="left",
    )
    df_merged["gross_sar"] = df_merged["quantity"] * df_merged["unit_price_sar"]
    df_merged["net_sales_sar"] = df_merged["gross_sar"] - df_merged["discount_sar"]
    df_merged["food_cost_sar"] = df_merged["quantity"] * df_merged["unit_cost_sar"]

    completed_lines = df_merged[df_merged["status"] == "completed"]
    completed_orders = df_orders[df_orders["status"] == "completed"]

    total_net_sales = completed_lines["net_sales_sar"].sum()
    total_food_cost = completed_lines["food_cost_sar"].sum()
    total_commission = completed_orders["delivery_commission_sar"].sum()

    print("\n--- Financial Totals (Completed Orders Excl. VAT) ---")
    print(f"Total Net Sales:       {total_net_sales:12,.2f} SAR")
    print(f"Total Food Cost:       {total_food_cost:12,.2f} SAR")
    print(f"Gross Profit Margin:   {((total_net_sales - total_food_cost) / total_net_sales * 100):11.2f}%")
    print(f"Delivery Commission:   {total_commission:12,.2f} SAR")

    # Sample rows
    print("\n--- First 5 Orders ---")
    print(df_orders.head(5).to_string(index=False))

    print("\n--- Last 5 Orders ---")
    print(df_orders.tail(5).to_string(index=False))

    print("\n--- First 5 Order Lines ---")
    print(df_lines.head(5).to_string(index=False))

    print("\n--- Last 5 Order Lines ---")
    print(df_lines.tail(5).to_string(index=False))
    print("=" * 80 + "\n")


def main():
    parser = argparse.ArgumentParser(description="Layali Synthetic POS Data Generator")
    parser.add_argument(
        "--month",
        type=str,
        help="Specific month to generate (format: YYYY-MM, e.g. 2026-01 or 2026-06)",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Generate all months including June holdout (2026-01 to 2026-06)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force overwrite clean batches if they already exist",
    )
    args = parser.parse_args()

    # Determine which months to run
    if args.month:
        if args.month not in ALL_MONTHS:
            raise ValueError(f"Invalid month: {args.month}. Allowed: {ALL_MONTHS}")
        months_to_run = [args.month]
    elif args.all:
        months_to_run = ALL_MONTHS
    else:
        # Default: Jan - May (Hold out June for pipeline refresh demonstration)
        months_to_run = DEFAULT_MONTHS

    print(f"Starting Layali POS Generator with fixed seed {FIXED_SEED}")
    print(f"Target Months: {months_to_run}")

    os.makedirs(RAW_CLEAN_DIR, exist_ok=True)
    os.makedirs(RAW_DIRTY_DIR, exist_ok=True)

    # 1. Save master data
    save_master_data()
    print("Master catalogs verified (branches.csv, products.csv, customers.csv)")

    all_manifest = []
    manifest_csv = os.path.join(RAW_DIRTY_DIR, "manifest.csv")
    manifest_json = os.path.join(RAW_DIRTY_DIR, "manifest.json")

    # Load existing manifest if present to append
    if os.path.exists(manifest_json):
        try:
            with open(manifest_json, "r", encoding="utf-8") as f:
                all_manifest = json.load(f)
        except Exception:
            all_manifest = []

    for ym in months_to_run:
        clean_orders_path = os.path.join(RAW_CLEAN_DIR, f"orders_{ym.replace('-', '_')}.csv")
        clean_lines_path = os.path.join(RAW_CLEAN_DIR, f"order_lines_{ym.replace('-', '_')}.csv")
        dirty_orders_path = os.path.join(RAW_DIRTY_DIR, f"orders_{ym.replace('-', '_')}_dirty.csv")
        dirty_lines_path = os.path.join(RAW_DIRTY_DIR, f"order_lines_{ym.replace('-', '_')}_dirty.csv")

        # Clean batches are immutable: do not overwrite unless --force is specified
        if os.path.exists(clean_orders_path) and not args.force:
            print(f"Skipping clean generation for {ym}: {clean_orders_path} already exists (immutable).")
            df_orders = pd.read_csv(clean_orders_path)
            df_lines = pd.read_csv(clean_lines_path)
        else:
            df_orders, df_lines = generate_month_data(ym)
            df_orders.to_csv(clean_orders_path, index=False)
            df_lines.to_csv(clean_lines_path, index=False)
            print(f"Saved clean batch: {clean_orders_path} & {clean_lines_path}")

        # Generate dirty copy & manifest
        df_dirty_orders, df_dirty_lines, month_manifest = create_dirty_copies(df_orders, df_lines, ym)
        df_dirty_orders.to_csv(dirty_orders_path, index=False)
        df_dirty_lines.to_csv(dirty_lines_path, index=False)
        print(f"Saved dirty batch: {dirty_orders_path} & {dirty_lines_path}")

        # Update manifest entries
        # Remove old entries for this month if rerunning
        all_manifest = [m for m in all_manifest if m.get("month") != ym]
        all_manifest.extend(month_manifest)

        # Print audit report for this month
        print_batch_summary(ym, df_orders, df_lines)

    # Save manifest
    with open(manifest_json, "w", encoding="utf-8") as f:
        json.dump(all_manifest, f, indent=2)
    pd.DataFrame(all_manifest).to_csv(manifest_csv, index=False)
    print(f"Updated dirty manifest: {manifest_csv} ({len(all_manifest)} total logged defects)")


if __name__ == "__main__":
    main()
