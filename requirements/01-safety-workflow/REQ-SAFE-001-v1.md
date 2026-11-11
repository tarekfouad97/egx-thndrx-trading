# REQ-SAFE-001-v1 — Human-only order execution

ID: REQ-SAFE-001-v1
Status: Active
Coverage: Implemented
Owner: Unassigned
Updated: 2026-11-11
Supersedes: None

## Requirement

The assistant must never place, modify or cancel a broker order, enter credentials, or use private broker APIs.

## Acceptance criteria

- [ ] AC1: Chart drawings are limited to EGX-labelled marks and documented studies.
- [ ] AC2: Order instructions are text for the user; no order-ticket inputs or clicks are automated.
- [ ] AC3: Live checks stop at login or 2FA and ask the user to complete authentication.

## Implementation references

- [skills/egx-check/SKILL.md](../../skills/egx-check/SKILL.md)
- [skills/egx-check/scripts/egx_chart.js](../../skills/egx-check/scripts/egx_chart.js)

## Verification

- node tests/test_chart_draw.js
- Manual read-only Claude/ThndrX check; not performed in this review.

## Revision notes

Initial documented baseline or proposal. No prior revision.
