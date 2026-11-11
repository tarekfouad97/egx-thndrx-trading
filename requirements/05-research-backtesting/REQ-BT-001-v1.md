# REQ-BT-001-v1 — Reproducible causal replay

ID: REQ-BT-001-v1
Status: Active
Coverage: Partial
Owner: Unassigned
Updated: 2026-11-11
Supersedes: None

## Requirement

Historical analysis must only see information available at the signal timestamp, and output must disclose simulation assumptions and differences from live rules.

## Acceptance criteria

- [ ] AC1: Signals on bar i cannot fill before bar i+1.
- [ ] AC2: Input universe, data dates, fees and slippage assumptions are recorded.
- [ ] AC3: The replay window matches the live export limit or is explicitly labeled different.
- [ ] AC4: Synthetic selftest output is not evidence of an EGX edge.

## Implementation references

- [tests/backtest.js](../../tests/backtest.js)
- [skills/egx-check/scripts/egx_chart.js](../../skills/egx-check/scripts/egx_chart.js)

## Verification

- node tests/backtest.js --selftest
- Review F5: live/history parity is incomplete.

## Revision notes

Initial documented baseline or proposal. No prior revision.
