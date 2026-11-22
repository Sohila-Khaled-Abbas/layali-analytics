# Contributing to Layali Analytics

Thank you for your interest in contributing! This project is a teaching reference for data engineering — contributions that improve clarity, correctness, or completeness are especially welcome.

---

## 📋 Before You Start

1. **Read the docs first:** [`docs/data_dictionary.md`](docs/data_dictionary.md) and [`docs/generator_assumptions.md`](docs/generator_assumptions.md) explain all design decisions.
2. **Open an issue** before starting significant work so we can discuss the approach.
3. **One concern per PR** — keep changes focused and reviewable.

---

## 🔧 Development Setup

```powershell
# Clone and enter the repo
git clone https://github.com/Sohila-Khaled-Abbas/layali-analytics.git
cd layali-analytics

# Create virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# Configure credentials (never commit .env)
Copy-Item .env.example .env
# Edit .env with your SQL Server details
```

---

## ✅ Quality Gates

**All contributions must pass the full quality suite before merging.**

```powershell
# Run data quality checks (must exit 0)
.\.venv\Scripts\python.exe tests/run_checks.py

# Run generator unit tests
.\.venv\Scripts\python.exe -m pytest tests/test_pos_generator.py -v
```

Both must pass with no failures before you open a PR.

---

## 📐 Coding Standards

### Python

- Python 3.11+ compatible syntax
- Type hints on all public functions
- Docstrings for every function and class
- No bare `except:` — always catch specific exceptions
- Money calculations: use `decimal.Decimal` or `round(..., 2)`, never `float` arithmetic
- Database credentials: environment variables only — never hardcoded

### SQL (T-SQL Only)

> [!IMPORTANT]
> This project is **T-SQL only**. Do not use PostgreSQL, MySQL, or ANSI SQL that is not valid T-SQL.

| ✅ Use | ❌ Avoid |
|--------|---------|
| `IDENTITY(1,1)` for surrogate keys | `SERIAL`, `AUTO_INCREMENT` |
| `TOP n` | `LIMIT n` |
| `DATEFROMPARTS`, `EOMONTH`, `DATENAME` | `DATE_TRUNC`, `TO_DATE` |
| `DECIMAL(12,2)` for money | `FLOAT`, `REAL`, `MONEY` |
| `NVARCHAR` for text | `VARCHAR`, `TEXT` |
| `[date]`, `[channel]` brackets around reserved words | Unquoted reserved words |
| `ISNULL(x, y)` | `IFNULL`, `NVL` |
| `CONVERT(DATE, ...)` | `CAST(... AS DATE)` where ambiguous |

### Data Integrity Rules

- Cancelled orders must **never** appear in `fact_orders` or `fact_order_lines`
- Delivery commission stored **once** on `fact_orders` — never on `fact_order_lines`
- Anonymous customers use `NULL` — no synthetic "unknown" customer surrogate in `dim_customer`
- Never silently repair invalid data in staging views — flag it and let the gate reject
- Raw zone tables keep all columns as `NVARCHAR` — casts happen only in staging views

---

## 🌿 Branching & Commits

```
main          ← stable, CI must pass
└── feature/  ← new features
└── fix/      ← bug fixes
└── docs/     ← documentation only
└── refactor/ ← code cleanup without behaviour change
```

**Commit messages** follow [Conventional Commits](https://www.conventionalcommits.org/):

```
feat: add weekly cohort retention query (#12)
fix: correct discount bound check for zero-price items (#15)
docs: clarify commission grain in data_dictionary.md (#18)
refactor: stream CSV reads in load_pos.py to reduce memory usage
test: add FK violation fixture for staging gate
```

---

## 🐛 Reporting Bugs

Use the [Bug Report template](.github/ISSUE_TEMPLATE/bug_report.md). Include:

- Your OS and Python version
- SQL Server version and ODBC driver version
- The exact command you ran
- The full error message and stack trace
- Contents of `reports/quality.json` if a quality check failed

---

## 💡 Suggesting Features

Use the [Feature Request template](.github/ISSUE_TEMPLATE/feature_request.md). Explain:

- The analytics or teaching gap the feature addresses
- How it fits the project's scope (restaurant case study, T-SQL, SQL Server)
- Any impact on existing data, tests, or SQL scripts

---

## 📄 License

By contributing, you agree that your contributions will be licensed under the [MIT License](LICENSE).
