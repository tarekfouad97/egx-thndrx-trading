# REQ-RISK-001-v1 — Shared capital and estimated loss budgets

ID: REQ-RISK-001-v1
Status: Active
Coverage: Implemented
Owner: Unassigned
Updated: 2026-11-11
Supersedes: None

## Requirement

Only valid plans may receive allocation; swing and T0 plans share available cash, concentration and estimated stop-risk budgets.

## Acceptance criteria

- [ ] AC1: Wait records receive zero allocation regardless of the legacy include_wait_orders flag.
- [ ] AC2: Cash debit includes buy fees; stop-risk includes configured exit fees and slippage.
- [ ] AC3: Unknown cash or unquantified existing holding risk blocks additional allocation.
- [ ] AC4: Zero risk remains zero; actual-size net R:R must pass.

## Implementation references

- [skills/egx-check/scripts/egx.py](../../skills/egx-check/scripts/egx.py)

## Verification

- python3 tests/test_risk.py
- python3 tests/test_egx.py

## Revision notes

Initial documented baseline or proposal. No prior revision.
