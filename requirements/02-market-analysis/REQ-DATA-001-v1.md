# REQ-DATA-001-v1 — OHLCV and benchmark alignment

ID: REQ-DATA-001-v1
Status: Active
Coverage: Implemented
Owner: Unassigned
Updated: 2026-11-11
Supersedes: None

## Requirement

Indicator inputs must reject malformed bars; relative-strength returns require matching stock and benchmark start and end dates.

## Acceptance criteria

- [ ] AC1: Non-finite prices, invalid high/low ranges, negative volume and duplicate/out-of-order timestamps are rejected.
- [ ] AC2: Unaligned or missing benchmark data produces unknown RS, not zero.
- [ ] AC3: During an observed open session, swing analysis excludes the current unfinished daily candle.

## Implementation references

- [skills/egx-check/scripts/egx_chart.js](../../skills/egx-check/scripts/egx_chart.js)

## Verification

- node tests/test_chart.js
- node tests/test_chart_rules.js

## Revision notes

Initial documented baseline or proposal. No prior revision.
