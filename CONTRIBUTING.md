# Contributing

Start with the [requirements register](requirements/README.md) and [integration review](docs/reviews/eb92411.md). Choose a small, named requirement and discuss ownership in an issue before overlapping someone else's work. Owners remain Unassigned until they agree.

## Propose a change

Use the requirement-change issue template. Describe the user problem, exact requirement ID, acceptance criteria and expected evidence. For changed behavior, create the next revision; preserve previous revisions. For a bug that violates an existing requirement, keep its ID/version and link the fix. See the register for lifecycle rules.

Open a PR using the supplied template. Cite full IDs such as `REQ-T0-002-v1`, distinguish implemented criteria from outstanding gaps, and include reproducible verification. A maintainer reviews proposed requirements before they become Active. Never include account credentials, private portfolio exports, browser cookies or real customer screenshots in fixtures.

## Local verification

Python tools use the standard library. JavaScript checks require Node.js. From the repository root:

```sh
python3 scripts/check_requirements.py
python3 tests/test_egx.py
python3 tests/test_risk.py
node tests/test_chart.js
node tests/test_chart_draw.js
node tests/test_chart_rules.js
node tests/backtest.js --selftest
```

Run checks relevant to the change; trading-rule fixes need a focused regression test reproducing the failure. Backtest self-tests verify software behavior, not strategy profitability.

For report changes, run `python3 tests/render_preview.py`, open `examples/report-preview.html`, inspect desktop and narrow mobile layouts, expand evidence with keyboard and pointer, and inspect print output. Keep the preview synthetic. Update the screenshots under `docs/images/` when the visual design changes.

Build the local Claude package with `python3 install.py --build-only`. Publishing, merging and assigning contributors are maintainer actions.
