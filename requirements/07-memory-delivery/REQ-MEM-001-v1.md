# REQ-MEM-001-v1 — Local artifacts and traceable delivery

ID: REQ-MEM-001-v1
Status: Active
Coverage: Partial
Owner: Unassigned
Updated: 2026-11-11
Supersedes: None

## Requirement

Each run must save a report and compact history; external delivery is only reported successful after a connector returns evidence.

## Acceptance criteria

- [ ] AC1: Repeated report generation does not duplicate history or erase outcomes.
- [ ] AC2: PDF generation errors are disclosed.
- [ ] AC3: Drive files are recorded by returned IDs; missing connector access is reported.
- [ ] AC4: Simulated recommendation outcomes remain distinguishable from executed-trade outcomes.

## Implementation references

- [skills/egx-check/scripts/egx_memory.py](../../skills/egx-check/scripts/egx_memory.py)
- [skills/egx-check/scripts/egx.py](../../skills/egx-check/scripts/egx.py)

## Verification

- python3 tests/test_egx.py
- Live connector round trip not exercised in this review.

## Revision notes

Initial documented baseline or proposal. No prior revision.
