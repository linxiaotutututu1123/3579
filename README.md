# cn-futures-auto-trader (Windows + GitHub CI gate)

This repo is a **skeleton** for a CN futures fully-automated trading system.
It implements a strict, testable RiskPolicy backbone and uses **GitHub Actions** as the only
鈥渁utomatic self-check鈥?gate after each feature.

## Quality gate (GitHub only)
Workflow: .github/workflows/ci.yml

For every push/PR, CI runs:
- ruff format check
- ruff lint
- mypy
- pytest

### How you work with Claude (recommended)
For each small feature:
1. Ask Claude to modify only the files for that feature.
2. Commit + push.
3. Check GitHub Actions green.
4. Only then start the next feature.

## Locked spec
See: SPEC_RISK.md

## Run locally (optional)
You *can* run locally, but per your requirement CI is the gate.
- ./scripts/dev.ps1 init
- ./scripts/dev.ps1 check

(These mimic the CI steps.)