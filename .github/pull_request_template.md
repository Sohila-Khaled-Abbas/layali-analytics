## 📝 Summary

<!-- What does this PR do? One paragraph. Link the issue it resolves. -->

Fixes #<!-- issue number -->

---

## 🔄 Changes

<!-- List the files changed and what changed in each. -->

| File | Change |
|------|--------|
| `src/` | |
| `sql/` | |
| `tests/` | |
| `docs/` | |

---

## ✅ Quality Checklist

**Run these before marking Ready for Review:**

- [ ] `python tests/run_checks.py` exits with code **0** (all 21 checks pass)
- [ ] `pytest tests/test_pos_generator.py -v` — all tests pass
- [ ] No `.env` file or raw CSV data committed
- [ ] Money uses `DECIMAL(12,2)`, never `FLOAT`
- [ ] SQL is T-SQL only — no PostgreSQL syntax

**Documentation:**

- [ ] Docstrings updated for changed functions
- [ ] `docs/data_dictionary.md` updated if schema changed
- [ ] `docs/generator_assumptions.md` updated if generator changed
- [ ] `CHANGELOG.md` entry added under `[Unreleased]`

**Data integrity:**

- [ ] Cancelled orders still excluded from both fact tables
- [ ] Commission column absent from `fact_order_lines`
- [ ] Anonymous customers still use `NULL` (no "unknown" surrogate)
- [ ] Batch loads still idempotent (re-running same batch = no change)

---

## 🧪 Testing Evidence

<!-- Paste the final lines of `python tests/run_checks.py` output here. -->

```
All 21 checks passed.
```

---

## 📋 Notes for Reviewer

<!-- Anything the reviewer should pay special attention to. -->
