# Layali Analytics: Enterprise Data Dictionary

This document defines the schema, grains, data types, nullability, and business descriptions across all data tiers (`raw`, `staging`, `marts`) in the Layali Analytics SQL Server data warehouse.

---

## 1. Grain Definitions & Dimensional Architecture

### 1.1 The Concept of Grain in Layali Analytics
* **`marts.fact_orders`**:
  * **Grain**: Exactly **one completed customer order**.
  * **Business Meaning**: Represents a single transaction event at a specific branch, date, and channel. It captures order-level aggregations (line count, order net sales, order food cost) and order-level economics (delivery commission and net contribution margin).
  * **Key Cardinality**: Primary Key is `order_id`.

* **`marts.fact_order_lines`**:
  * **Grain**: Exactly **one line item on a completed order**.
  * **Business Meaning**: Represents a specific product purchased within an order, with quantity, line pricing, line discount, and line food cost.
  * **Key Cardinality**: Primary Key is `order_line_id`. Foreign Key is `order_id`.

### 1.2 Why an Order with Three Items is Still One Order (The Multi-Item Basket Principle)
Consider an order where a customer dines in at Al Rawdah and orders:
1. `PRD01` (Hummus) – Qty 1 @ 22.00 SAR
2. `PRD07` (Lamb Kebab) – Qty 2 @ 68.00 SAR = 136.00 SAR
3. `PRD22` (Mint Lemonade) – Qty 1 @ 18.00 SAR

* **In `marts.fact_order_lines`**:
  * There are **three records** (`LIN-01`, `LIN-02`, `LIN-03`).
  * Total units: $1 + 2 + 1 = 4$ units.
  * Line sales sum to $22.00 + 136.00 + 18.00 = 176.00\text{ SAR}$.
  * Product dimensions are attached at this grain.

* **In `marts.fact_orders`**:
  * There is **exactly one record** (`ORD-0001`).
  * `line_count` = 3.
  * `net_sales_sar` = 176.00 SAR.
  * Channel, branch, date, and customer dimensions exist here.
  * If this were a delivery order with 20% commission ($176.00 \times 0.20 = 35.20\text{ SAR}$), that 35.20 SAR exists **only once** on the order record. If commission were copied to each line, summing lines across the warehouse would falsely inflate commission by 3x ($105.60\text{ SAR}$)!
  * **Power BI Rule**: The two fact tables are kept separate and related to shared dimensions in a Star Schema. They are **never joined directly together** in reporting.

---

## 2. Table Specifications

### 2.1 Raw Schema (`raw`)
Preserves incoming raw text rows, source file lineage, and batch partition metadata.

| Table | Column Name | Data Type | Nullable | Description |
| :--- | :--- | :--- | :---: | :--- |
| `raw.branches` | `branch_id` | `NVARCHAR(20)` | No | Natural branch key (`BR01`, `BR02`, `BR03`) |
| | `branch_name` | `NVARCHAR(100)` | No | Name of restaurant branch |
| | `opened_date` | `NVARCHAR(20)` | No | Branch opening date string |
| | `source_file` | `NVARCHAR(255)` | No | Ingested source CSV filename |
| | `loaded_at` | `DATETIME2` | No | System timestamp when row was loaded |
| `raw.products` | `product_id` | `NVARCHAR(20)` | No | Product key (`PRD01` - `PRD25`) |
| | `product_name` | `NVARCHAR(100)` | No | Menu item name |
| | `category` | `NVARCHAR(50)` | No | Menu category |
| | `unit_price_sar` | `NVARCHAR(50)` | No | Menu item price in SAR |
| | `unit_cost_sar` | `NVARCHAR(50)` | No | Raw food preparation cost in SAR |
| | `source_file` | `NVARCHAR(255)` | No | Ingested source CSV filename |
| | `loaded_at` | `DATETIME2` | No | System load timestamp |
| `raw.customers` | `customer_id` | `NVARCHAR(50)` | No | Synthetic customer key (`CUST-10001`...) |
| | `source_file` | `NVARCHAR(255)` | No | Ingested source CSV filename |
| | `loaded_at` | `DATETIME2` | No | System load timestamp |
| `raw.orders` | `order_id` | `NVARCHAR(50)` | No | Natural order identifier |
| | `order_timestamp` | `NVARCHAR(50)` | No | Date and time of order placement |
| | `order_date` | `NVARCHAR(20)` | No | Order date string |
| | `branch_id` | `NVARCHAR(20)` | No | Branch foreign key |
| | `channel` | `NVARCHAR(50)` | No | Sales channel (`dine-in`, `takeaway`, `delivery`) |
| | `customer_id` | `NVARCHAR(50)` | Yes | Customer foreign key (nullable for anonymous) |
| | `status` | `NVARCHAR(50)` | No | Order status (`completed`, `cancelled`) |
| | `delivery_commission_sar` | `NVARCHAR(50)` | No | Order commission value |
| | `source_file` | `NVARCHAR(255)` | No | Ingested source CSV filename |
| | `batch_month` | `NVARCHAR(7)` | No | Batch partition month (`YYYY-MM`) |
| | `loaded_at` | `DATETIME2` | No | System load timestamp |
| `raw.order_lines` | `order_line_id` | `NVARCHAR(50)` | No | Natural order line key |
| | `order_id` | `NVARCHAR(50)` | No | Order foreign key |
| | `product_id` | `NVARCHAR(20)` | No | Product foreign key |
| | `quantity` | `NVARCHAR(20)` | No | Item quantity |
| | `unit_price_sar` | `NVARCHAR(50)` | No | Menu unit price |
| | `unit_cost_sar` | `NVARCHAR(50)` | No | Unit food cost |
| | `discount_sar` | `NVARCHAR(50)` | No | Total discount applied to this line |
| | `source_file` | `NVARCHAR(255)` | No | Ingested source CSV filename |
| | `batch_month` | `NVARCHAR(7)` | No | Batch partition month (`YYYY-MM`) |
| | `loaded_at` | `DATETIME2` | No | System load timestamp |

---

### 2.2 Staging Views (`staging`)
Typed representations with deterministic deduplication of exact duplicate source rows. Does **not** silently repair corrupt keys or discounts.

| View Name | Key Calculations & Casts | Integrity Assertions Exposed |
| :--- | :--- | :--- |
| `staging.stg_branches` | `opened_date` cast to `DATE` | Checked against master catalog |
| `staging.stg_products` | `unit_price_sar`, `unit_cost_sar` cast to `DECIMAL(12,2)` | None |
| `staging.stg_customers` | `customer_id` filtered for non-empty values | Unique distinct values |
| `staging.stg_orders` | Deduplicated via `ROW_NUMBER() OVER (PARTITION BY batch_month, order_id ORDER BY loaded_at ASC) = 1`. Casts timestamps to `DATETIME2`, dates to `DATE`, commission to `DECIMAL(12,2)`. | `is_valid_branch`, `is_valid_channel`, `is_valid_status` |
| `staging.stg_order_lines` | Deduplicated via `ROW_NUMBER() OVER (PARTITION BY batch_month, order_line_id ORDER BY loaded_at ASC) = 1`. Gross = `qty * unit_price`, Net = `Gross - discount`, Cost = `qty * unit_cost`. | `is_valid_product`, `is_valid_discount` (`0 <= discount <= Gross`) |

---

### 2.3 Marts Dimensional Model (`marts`)
Star schema optimized for analytical query performance and Power BI Desktop consumption.

#### Dimensions
* **`marts.dim_date`**:
  * `date` (`DATE`, PK): Calendar day.
  * `month_start` (`DATE`): First day of calendar month.
  * `year_month` (`NVARCHAR(7)`): Display string `YYYY-MM`.
  * `month_sort` (`INT`): Numeric sort key `YYYYMM`.
  * `day_name` (`NVARCHAR(20)`): Day of week name (e.g. `Friday`).
  * `weekday_sort` (`INT`): Weekday sort order (Saudi calendar: Sunday=1 to Saturday=7).
  * `is_weekend` (`BIT`): 1 for Friday and Saturday, 0 otherwise.

* **`marts.dim_branch`**:
  * `branch_id` (`NVARCHAR(20)`, PK): Primary key (`BR01`, `BR02`, `BR03`).
  * `branch_name` (`NVARCHAR(100)`): Al Rawdah, Al Hamra, Obhur.
  * `opened_date` (`DATE`): Branch launch date.

* **`marts.dim_product`**:
  * `product_id` (`NVARCHAR(20)`, PK): Primary key (`PRD01` to `PRD25`).
  * `product_name` (`NVARCHAR(100)`): Item name.
  * `category` (`NVARCHAR(50)`): Appetizers, Grills, Rice & Mains, Desserts, Beverages.
  * `unit_price_sar` (`DECIMAL(12,2)`): Standard selling price excluding VAT.
  * `unit_cost_sar` (`DECIMAL(12,2)`): Standard preparation food cost.

* **`marts.dim_channel`**:
  * `channel` (`NVARCHAR(50)`, PK): `dine-in`, `takeaway`, `delivery`.
  * `channel_name` (`NVARCHAR(50)`): Formatted display label.

* **`marts.dim_customer`**:
  * `customer_id` (`NVARCHAR(50)`, PK): Synthetic customer ID (`CUST-10001` to `CUST-15000`).
  * *Note*: Anonymous walk-ins retain `NULL` in fact tables. No synthetic record exists for anonymous.

#### Fact Tables
* **`marts.fact_orders`** (Grain: One completed order):
  * `order_id` (`NVARCHAR(50)`, PK): Primary order key.
  * `date` (`DATE`, FK to `dim_date`): Date of order.
  * `order_timestamp` (`DATETIME2`): Full local timestamp (`Asia/Riyadh`).
  * `branch_id` (`NVARCHAR(20)`, FK to `dim_branch`): Operating branch.
  * `channel` (`NVARCHAR(50)`, FK to `dim_channel`): Sales channel.
  * `customer_id` (`NVARCHAR(50)`, FK to `dim_customer`, NULL allowed): Customer identifier.
  * `line_count` (`INT`): Total distinct line items on order.
  * `net_sales_sar` (`DECIMAL(12,2)`): Total net revenue after line discounts ($\sum \text{line\_net\_sales}$).
  * `food_cost_sar` (`DECIMAL(12,2)`): Total ingredient food cost ($\sum \text{line\_food\_cost}$).
  * `delivery_commission_sar` (`DECIMAL(12,2)`): Exactly 20% of net sales for delivery orders, 0 for dine-in/takeaway.
  * `contribution_sar` (`DECIMAL(12,2)`): Net contribution = $\text{net\_sales} - \text{food\_cost} - \text{delivery\_commission}$.
  * `batch_month` (`NVARCHAR(7)`): Ingestion batch tracking month.

* **`marts.fact_order_lines`** (Grain: One completed order line item):
  * `order_line_id` (`NVARCHAR(50)`, PK): Unique line identifier.
  * `order_id` (`NVARCHAR(50)`): Parent order reference.
  * `date` (`DATE`, FK to `dim_date`): Copied from order.
  * `branch_id` (`NVARCHAR(20)`, FK to `dim_branch`): Copied from order.
  * `product_id` (`NVARCHAR(20)`, FK to `dim_product`): Purchased menu item.
  * `channel` (`NVARCHAR(50)`, FK to `dim_channel`): Copied from order.
  * `customer_id` (`NVARCHAR(50)`, FK to `dim_customer`, NULL allowed): Copied from order.
  * `quantity` (`INT`): Units sold.
  * `unit_price_sar` (`DECIMAL(12,2)`): Price per unit.
  * `unit_cost_sar` (`DECIMAL(12,2)`): Cost per unit.
  * `discount_sar` (`DECIMAL(12,2)`): Total promotional discount on line.
  * `net_sales_sar` (`DECIMAL(12,2)`): Line net revenue = $\text{quantity} \times \text{unit\_price} - \text{discount}$.
  * `food_cost_sar` (`DECIMAL(12,2)`): Line food cost = $\text{quantity} \times \text{unit\_cost}$.
  * `batch_month` (`NVARCHAR(7)`): Ingestion batch tracking month.
