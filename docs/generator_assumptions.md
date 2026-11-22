# Layali Analytics: Synthetic POS Generator Assumptions

> **Context**: This document details all mathematical, business, and structural assumptions planted within `src/generate_pos.py`. These assumptions are kept separate from analytical findings and business intelligence deliverables.

---

## 1. Scope, Timezone & Determinism
* **Date Range**: January 1, 2026 through June 30, 2026 (inclusive).
* **Timezone**: `Asia/Riyadh` (UTC+03:00) local operating hours.
* **Random Seed**: Fixed seed `42`. To guarantee reproducible and collision-free stable IDs regardless of whether batches are generated individually (`--month YYYY-MM`) or concurrently, daily simulation seeds are derived deterministically:
  $$\text{seed}_{\text{day}} = 42 + (\text{date} - \text{start\_date})\times 100 + \text{branch\_index}$$
* **Holdout Set**: January through May 2026 (`2026-01` to `2026-05`) are generated initially. June 2026 (`2026-06`) is withheld for incremental ETL pipeline refresh and validation demonstrations.

---

## 2. Master Data Entities

### 2.1 Branches
All branches opened prior to January 2026:
| Branch ID | Branch Name | Opened Date | Baseline Profile |
| :--- | :--- | :--- | :--- |
| `BR01` | Al Rawdah | 2021-03-15 | High-volume flagship, mature dine-in audience |
| `BR02` | Al Hamra | 2022-08-01 | Balanced suburban family and takeaway hub |
| `BR03` | Obhur | 2024-05-10 | Coastal / leisure branch, subject to the Q2 shift |

### 2.2 Products (25 Fixed Menu Items)
Authentic Middle Eastern & Saudi culinary catalog spanning 5 categories:
* **Appetizers**:
  * `PRD01`: Hummus Bil Tahina (Price: 22.00 SAR, Cost: 5.50 SAR)
  * `PRD02`: Mutabbal Eggplant (Price: 24.00 SAR, Cost: 6.00 SAR)
  * `PRD03`: Fattoush Salad (Price: 26.00 SAR, Cost: 6.50 SAR)
  * `PRD04`: Tabbouleh (Price: 25.00 SAR, Cost: 6.25 SAR)
  * `PRD05`: Sambousek Meat & Cheese (Price: 28.00 SAR, Cost: 7.50 SAR)
* **Grills**:
  * `PRD06`: Shish Tawook Skewers (Price: 58.00 SAR, Cost: 18.50 SAR)
  * `PRD07`: Lamb Kebab Skewers (Price: 68.00 SAR, Cost: 24.00 SAR)
  * `PRD08`: Mixed Grill Platter (Price: 95.00 SAR, Cost: 35.00 SAR)
  * `PRD09`: Grilled Ribeye Steak Tikka (Price: 85.00 SAR, Cost: 32.00 SAR)
  * `PRD10`: Grilled Jumbo Prawns (Price: 110.00 SAR, Cost: 42.00 SAR)
* **Rice & Mains**:
  * `PRD11`: Traditional Lamb Kabsa (Price: 75.00 SAR, Cost: 26.00 SAR)
  * `PRD12`: Chicken Mandi (Price: 48.00 SAR, Cost: 15.00 SAR)
  * `PRD13`: Sayadieh Fish & Rice (Price: 65.00 SAR, Cost: 22.00 SAR)
  * `PRD14`: Lamb Shank Madghout (Price: 88.00 SAR, Cost: 32.00 SAR)
  * `PRD15`: Oven-baked Musakhan (Price: 52.00 SAR, Cost: 17.00 SAR)
* **Desserts**:
  * `PRD16`: Cheese Kunafa (Price: 32.00 SAR, Cost: 9.00 SAR)
  * `PRD17`: Umm Ali (Price: 28.00 SAR, Cost: 7.50 SAR)
  * `PRD18`: Date Pudding with Caramel (Price: 35.00 SAR, Cost: 9.50 SAR)
  * `PRD19`: Pistachio Baklava Selection (Price: 38.00 SAR, Cost: 12.00 SAR)
  * `PRD20`: Muhallabia with Rose Water (Price: 20.00 SAR, Cost: 4.50 SAR)
* **Beverages**:
  * `PRD21`: Saudi Specialty Coffee Dallah (Price: 30.00 SAR, Cost: 6.00 SAR)
  * `PRD22`: Fresh Mint Lemonade (Price: 18.00 SAR, Cost: 3.50 SAR)
  * `PRD23`: Pomegranate Virgin Mojito (Price: 24.00 SAR, Cost: 5.00 SAR)
  * `PRD24`: Karak Tea Pot (Price: 16.00 SAR, Cost: 3.00 SAR)
  * `PRD25`: Sparkling Mineral Water 750ml (Price: 15.00 SAR, Cost: 3.50 SAR)

### 2.3 Customers
* Pool of 5,000 synthetic IDs (`CUST-10001` through `CUST-15000`). No names, contact details, or PII.
* **Anonymous Ratio**: Exactly 25% of orders are anonymous walk-ins/unregistered guest orders (`customer_id = NULL`).
* **Repeat Distribution**: 75% of orders draw from the customer pool with realistic repeat visitation dynamics across months.

---

## 3. Order Dynamics & Volume Models

### 3.1 Daily Volume & Day-of-Week Seasonality
* **Baseline**: 80 to 160 orders per branch/day.
* **Day-of-Week Multipliers**:
  * Sunday – Wednesday: 0.95x – 1.00x
  * Thursday: 1.20x (weekend onset)
  * Friday: 1.45x (peak family lunch & dinner)
  * Saturday: 1.30x (weekend leisure)

### 3.2 Operating Hours & Intraday Peak Weighting
* **Operating Hours**: 12:00 PM to 00:30 AM (closed 00:30 - 11:59).
* **Lunch Peak (12:00 - 15:30)**: ~35% of daily transactions (peak at 13:30 - 14:30).
* **Afternoon Lull (15:30 - 18:30)**: ~10% of daily transactions (café, desserts, light snacks).
* **Dinner Peak (18:30 - 23:30)**: ~55% of daily transactions (peak at 20:30 - 22:30).

### 3.3 Channel Mix
* **Standard Baseline**:
  * Dine-in: 45%
  * Takeaway: 30%
  * Delivery: 25%

---

## 4. Planted Analytical Anomaly: The "Obhur Shift"
Starting **April 1, 2026**:
1. **Volume Reduction**: Obhur daily order count is reduced by **20%** ($\text{volume} \times 0.80$).
2. **Channel Pivot**: Obhur channel allocation shifts dramatically toward delivery:
   * Delivery: **55%**
   * Takeaway: **25%**
   * Dine-in: **20%**
3. **Integrity Rule**: Revenue is never directly manipulated. Financial contraction or margin shifts emerge strictly from order count decline, delivery commission exposure, and product basket selection.

---

## 5. Financial & Mathematical Rules
* **VAT**: All money values strictly exclude VAT.
* **No Adjustments**: No tips, refunds, or service charges exist in the core data.
* **Line Pricing & Discount**:
  * Gross Line Amount: $\text{Gross} = \text{quantity} \times \text{unit\_price}$
  * `discount_sar`: Total discount for the line (not unit discount). 85% of lines have zero discount; 15% carry promotional discounts (10% to 20% of line gross, capped strictly below gross).
  * Line Net Sales: $\text{net\_sales} = \text{Gross} - \text{discount\_sar}$
  * Line Food Cost: $\text{food\_cost} = \text{quantity} \times \text{unit\_cost}$
* **Delivery Commission**:
  * Exactly **20% of net order sales** for completed delivery orders:
    $$\text{delivery\_commission\_sar} = \text{round}(0.20 \times \sum \text{line\_net\_sales}, 2)$$
  * Zero for dine-in, takeaway, and all cancelled orders.
* **Order Status**:
  * `completed` (~97% overall; 99% dine-in, 98% takeaway, 95% delivery)
  * `cancelled` (~3% overall). Cancelled orders contribute zero to net sales, food cost, and commissions.
* **Rounding**: All monetary calculations adhere to decimal-safe two decimal places (`round(..., 2)`).

---

## 6. Raw Data Storage & Dirty Data Manifest
* **Clean Batches** (`data/raw/clean/`):
  * Strictly immutable. Never overwritten once written.
  * Formatted as standard monthly CSV files (`orders_YYYY_MM.csv`, `order_lines_YYYY_MM.csv`) alongside master tables (`branches.csv`, `products.csv`, `customers.csv`).
* **Dirty Batches** (`data/raw/dirty/`):
  * Separate corrupted copies (`orders_YYYY_MM_dirty.csv`, `order_lines_YYYY_MM_dirty.csv`).
  * Injected corruptions:
    1. **Duplicate Lines**: Repeated `order_line_id` records in order lines.
    2. **Invalid Branch Foreign Keys**: Orders with invalid branch reference `BR99`.
    3. **Invalid Discounts**: Order lines where `discount_sar > quantity * unit_price` (resulting in negative net sales) or negative discounts.
  * Manifest file `data/raw/dirty/manifest.csv` and `manifest.json` catalog every injected defect with exact identifiers and corruption types for automated data-quality testing and quarantine demonstration.
