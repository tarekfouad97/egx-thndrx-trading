# REQ-POS-001-v1 — Deterministic management with explicit missing facts

ID: REQ-POS-001-v1
Status: Active
Coverage: Partial
Owner: Unassigned
Updated: 2026-11-11
Supersedes: None

## Requirement

Management actions must come from the rule engine, include reasons and quantities, preserve a nondecreasing trailing stop, and identify missing facts.

## Acceptance criteria

- [ ] AC1: Material-news, stop, support-break, time-stop, partial, trail and hold outcomes identify their rule.
- [ ] AC2: Unknown partial_done is not treated as a confirmed false value.
- [ ] AC3: Bars used to count held sessions are dated, ordered and sufficiently complete.
- [ ] AC4: Reports display the computed action, including partial sales.

## Implementation references

- [skills/egx-check/scripts/egx_manage.py](../../skills/egx-check/scripts/egx_manage.py)
- [skills/egx-check/scripts/egx_page.py](../../skills/egx-check/scripts/egx_page.py)

## Verification

- python3 tests/test_egx.py
- Review F3: unknown partial state still needs coverage.

## Revision notes

Initial documented baseline or proposal. No prior revision.
