# REQ-REPORT-001-v2 — Dark editorial market desk

ID: REQ-REPORT-001-v2
Status: Active
Coverage: Implemented
Owner: Unassigned
Updated: 2026-11-11
Supersedes: REQ-REPORT-001-v1

## Requirement

The report must retain the editorial hierarchy while using a dark palette and a sharper, more assertive visual treatment.

## Acceptance criteria

- [ ] AC1: Near-black background, lime accents, distinct red loss and amber wait states.
- [ ] AC2: Angular cards, strong headline/number hierarchy and clear price levels.
- [ ] AC3: No horizontal overflow at 1440, 390 and 320 pixels; Arabic content remains readable.
- [ ] AC4: Evidence expands by keyboard/pointer and is visible in print media.
- [ ] AC5: Visual changes do not alter computed verdicts, risk or share quantities.

## Implementation references

- [skills/egx-check/scripts/egx_page.py](../../skills/egx-check/scripts/egx_page.py)
- [examples/report-preview.html](../../examples/report-preview.html)

## Verification

- python3 tests/render_preview.py
- Browser render check at desktop/mobile widths and print media.
- python3 tests/test_risk.py

## Revision notes

Replaces the ivory palette with dark charcoal, lime accents and angular emphasis; preserves report semantics.
