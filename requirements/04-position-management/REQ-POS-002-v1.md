# REQ-POS-002-v1 — Executable partial-exit quantities

ID: REQ-POS-002-v1
Status: Proposed
Coverage: Not implemented
Owner: Unassigned
Updated: 2026-11-11
Supersedes: None

## Requirement

A partial exit must specify a positive integer quantity smaller than the held quantity; the one-share policy must be explicit.

## Acceptance criteria

- [ ] AC1: One held share never produces sell 0 or a partial action with no quantity.
- [ ] AC2: Odd-lot rounding is consistent between live management and research simulation.
- [ ] AC3: Quantity must be finite, positive and integral before producing a sell instruction.

## Implementation references

- [skills/egx-check/scripts/egx_manage.py](../../skills/egx-check/scripts/egx_manage.py)
- [tests/backtest.js](../../tests/backtest.js)

## Verification

- Add quantities 0, 1, 2, 3, 101, fractional and invalid-number cases.
- Review F4.

## Revision notes

Initial documented baseline or proposal. No prior revision.
