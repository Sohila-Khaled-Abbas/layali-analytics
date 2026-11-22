---
name: 💡 Feature Request
about: Suggest an improvement or new capability
title: '[FEAT] '
labels: enhancement
assignees: ''
---

## 💡 Feature Summary

<!-- One sentence: what does this feature do? -->

## 🎯 Motivation

<!-- What analytics or teaching gap does this address?
     What problem are you trying to solve? -->

## 📐 Proposed Approach

<!-- How should it work? Include:
     - Which files would change (src/, sql/, tests/, docs/)
     - T-SQL or Python impact
     - Any new tables or columns in the star schema
     - Impact on existing quality checks -->

## 🔄 Alternatives Considered

<!-- What other approaches did you consider, and why did you rule them out? -->

## ✅ Definition of Done

<!-- How will we know the feature is complete? List acceptance criteria. -->

- [ ] Code written and passing `python tests/run_checks.py`
- [ ] New pytest tests added where applicable
- [ ] `docs/data_dictionary.md` updated if schema changed
- [ ] `CHANGELOG.md` entry added under `[Unreleased]`
- [ ] README updated if user-facing behaviour changes

## 📋 Scope Check

<!-- Please confirm this feature fits the project scope. -->

- [ ] Uses T-SQL only (no PostgreSQL or MySQL syntax)
- [ ] Money columns use `DECIMAL(12,2)`, never `FLOAT`
- [ ] No PII or real customer data introduced
- [ ] Does not break idempotency of batch loads
- [ ] Cancelled orders still excluded from all marts
