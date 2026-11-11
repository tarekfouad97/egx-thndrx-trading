# REQ-BT-002-v1 — Execution parity and defensible statistics

ID: REQ-BT-002-v1
Status: Proposed
Coverage: Not implemented
Owner: Unassigned
Updated: 2026-11-11
Supersedes: None

## Requirement

Research results must disclose intrabar ambiguity, use integer shares and current fee assumptions, and avoid treating pooled correlated trades as a validated strategy pass.

## Acceptance criteria

- [ ] AC1: Same-bar entry/partial/stop/target ambiguity uses a documented conservative rule or finer data.
- [ ] AC2: Replay and live order semantics, initial risk and exit rules are matched or differences are quantified.
- [ ] AC3: Portfolio cash/exposure constraints are simulated before portfolio drawdown is claimed.
- [ ] AC4: Uncertainty handles cross-stock/time dependence and evaluation uses held-out periods.

## Implementation references

- [tests/backtest.js](../../tests/backtest.js)

## Verification

- Add explicit OHLC-path and integer-share fixtures plus live/replay parity cases.
- Review F5/F6.

## Revision notes

Initial documented baseline or proposal. No prior revision.
