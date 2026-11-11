# REQ-REPORT-002-v1 — Honest report data and safe rendering

ID: REQ-REPORT-002-v1
Status: Active
Coverage: Implemented
Owner: Unassigned
Updated: 2026-11-11
Supersedes: None

## Requirement

Report values must reflect the current computed plan, preserve escaping, and label synthetic data and incomplete evidence.

## Acceptance criteria

- [ ] AC1: Allocation is recomputed when generating a report.
- [ ] AC2: T0 cards display the intraday quote and session date.
- [ ] AC3: Only HTTP(S) source links are active; text and embedded data remain escaped.
- [ ] AC4: Skipped/open steps are not counted as script-proven.
- [ ] AC5: Synthetic previews cannot be mistaken for current signals.

## Implementation references

- [skills/egx-check/scripts/egx.py](../../skills/egx-check/scripts/egx.py)
- [skills/egx-check/scripts/egx_page.py](../../skills/egx-check/scripts/egx_page.py)

## Verification

- python3 tests/test_risk.py
- python3 tests/test_egx.py

## Revision notes

Initial documented baseline or proposal. No prior revision.
