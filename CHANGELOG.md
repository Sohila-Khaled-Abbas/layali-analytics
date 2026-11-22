# Changelog

All notable changes to Layali Analytics are documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.0.0] — 2026-11-22

### Added

#### Data Generation (`src/generate_pos.py`)
- Fixed-seed (42) reproducible synthetic POS generator for a fictional 3-branch Saudi restaurant chain
- 5 months of clean data (Jan–May 2026) in monthly CSV batches; June held out for refresh demo
- 25 fixed menu items across 5 categories: Mains, Grills, Mezze, Beverages, Desserts
- 5,000 synthetic customer IDs with 25% anonymous orders (`customer_id = NULL`)
- Day-of-week weighting (Friday 1.45×, Saturday 1.30×) and time-of-day distribution (Lunch 35%, Dinner 55%)
- Delivery commission = 20% of net order sales (delivery completed orders only)
- Planted Obhur anomaly from April 1: volume ×0.80, delivery channel shifts to 55%
- Dirty data copies with manifest (duplicate lines, invalid branch FK `BR99`, impossible discounts)
- `--month YYYY-MM` and `--all` CLI flags
- Monthly summary statistics printed to stdout (order counts, line counts, min/max dates, revenue totals)

#### SQL Server Data Warehouse (`sql/`)
- `01_init_database.sql` — `LayaliAnalytics` database + `raw`, `staging`, `marts` schemas
- `02_create_raw_tables.sql` — Raw zone tables (all NVARCHAR columns + `source_file`, `batch_month` metadata)
- `03_create_staging_views.sql` — Staging views with explicit casts, FK validation flags, deterministic ROW_NUMBER dedup
- `04_create_marts_tables.sql` — Star schema: `dim_date`, `dim_branch`, `dim_product`, `dim_channel`, `dim_customer`, `fact_orders`, `fact_order_lines`
- `05_populate_dim_date.sql` — Calendar spine Jan 1–Jun 30, 2026 (T-SQL `DATEFROMPARTS`, `DATENAME`)
- `06_sample_analytical_queries.sql` — 10 business queries (revenue by branch, top products, channel mix, Obhur anomaly, etc.)

#### ETL Loader (`src/load_pos.py`)
- Pre-load Python validation gate (branch FK + discount integrity); quarantines before any DB writes
- Idempotent raw batch replacement (`DELETE WHERE batch_month = ?` then INSERT)
- SQL-side staging quality gate
- Marts promotion (orders with aggregated line totals; lines with order-level dimension keys copied)
- `--init-db`, `--all`, `--month YYYY-MM`, `--test-quarantine` CLI flags
- Streaming CSV reader (`csv.DictReader`) to avoid memory exhaustion on bulk inserts

#### Database Utilities (`src/db.py`)
- `get_connection()` — pyodbc connection from `.env` environment variables
- `execute_tsql_script()` — `GO` batch splitter for multi-statement SQL scripts

#### Quality Suite (`tests/run_checks.py`)
- 21 automated data quality checks covering uniqueness, referential integrity, domain rules, reconciliation, idempotency, and dirty-data isolation
- Outputs `reports/quality.json` with check name, expected, actual, pass/fail
- Exits with code `1` on any failure
- Runs dirty fixtures in isolated `test_marts` schema; production marts never touched

#### Unit Tests (`tests/test_pos_generator.py`)
- 5 pytest tests: reproducibility, branch count, ID uniqueness, commission formula, anonymous rate

#### Documentation
- `docs/data_dictionary.md` — Full schema reference with grain definitions, all columns, types, nullability
- `docs/generator_assumptions.md` — Planted anomalies, pricing assumptions, channel weights

#### GitHub & Community Files
- `README.md` with mermaid architecture diagrams, ER diagram, quick start, sample queries, badges
- `LICENSE` (MIT, 2026)
- `CONTRIBUTING.md`
- `CODE_OF_CONDUCT.md` (Contributor Covenant v2.1)
- `.github/ISSUE_TEMPLATE/bug_report.md`
- `.github/ISSUE_TEMPLATE/feature_request.md`
- `.github/pull_request_template.md`
- `.github/workflows/quality_checks.yml` (GitHub Actions CI)

---

## [Unreleased]

### Planned
- Power BI semantic model (`powerbi/layali.pbix`) with DAX measures and dashboard
- June 2026 data generation and refresh demonstration walkthrough
- dbt models as an alternative transformation layer
- Docker Compose setup for SQL Server + environment bootstrapping
