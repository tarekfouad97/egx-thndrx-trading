# REQ-FLOW-001-v1 — Evidence and downgrade-only verdicts

ID: REQ-FLOW-001-v1
Status: Active
Coverage: Partial
Owner: Unassigned
Updated: 2026-11-11
Supersedes: None

## Requirement

A complete recommendation must use script-computed gates and an intact step ledger, distinguish evidence provenance, and honor every explicit downgrade.

## Acceptance criteria

- [ ] AC1: Failed or unknown prerequisites cannot become valid by prose.
- [ ] AC2: Typed data, attestations and script checks are reported separately.
- [ ] AC3: Any early signal states incomplete checks and must not bypass an explicit downgrade.

## Implementation references

- [skills/egx-check/scripts/egx_gates.py](../../skills/egx-check/scripts/egx_gates.py)
- [skills/egx-check/scripts/egx_steps.py](../../skills/egx-check/scripts/egx_steps.py)

## Verification

- python3 tests/test_egx.py
- Open gap: review finding F1 (fast signal).

## Revision notes

Initial documented baseline or proposal. No prior revision.
