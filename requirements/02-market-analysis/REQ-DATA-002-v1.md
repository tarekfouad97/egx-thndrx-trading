# REQ-DATA-002-v1 — Market-data freshness and session completeness

ID: REQ-DATA-002-v1
Status: Proposed
Coverage: Not implemented
Owner: Unassigned
Updated: 2026-11-11
Supersedes: None

## Requirement

Session-sensitive signals must use completed candles from a verified current exchange session, with explicit age and corporate-action adjustment metadata.

## Acceptance criteria

- [ ] AC1: Calendar handles holidays and shortened sessions in Africa/Cairo.
- [ ] AC2: A new receipt for old bars does not reset market-data age.
- [ ] AC3: Incomplete five-minute bars and incomplete opening ranges cannot confirm triggers.
- [ ] AC4: Unknown corporate-action adjustment status is shown; do not silently stitch discontinuities.

## Implementation references

- [skills/egx-check/scripts/egx_chart.js](../../skills/egx-check/scripts/egx_chart.js)
- [skills/egx-check/references/analysis-rules.md](../../skills/egx-check/references/analysis-rules.md)

## Verification

- Add deterministic holiday, delayed-bar, partial-bar and split fixtures before implementation is accepted.

## Revision notes

Initial documented baseline or proposal. No prior revision.
