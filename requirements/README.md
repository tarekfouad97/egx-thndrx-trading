# Requirements register

This is the shared specification and contribution starting point. It records existing intended behavior, known gaps and proposals; it does not claim that every requirement already passes. Baseline: integration commit `eb92411` plus the current report-design requests.

| Section | Current revisions |
|---|---|
| [Safety Workflow](01-safety-workflow/README.md) | [REQ-SAFE-001-v1](01-safety-workflow/REQ-SAFE-001-v1.md), [REQ-FLOW-001-v1](01-safety-workflow/REQ-FLOW-001-v1.md) |
| [Market Analysis](02-market-analysis/README.md) | [REQ-DATA-001-v1](02-market-analysis/REQ-DATA-001-v1.md), [REQ-DATA-002-v1](02-market-analysis/REQ-DATA-002-v1.md), [REQ-NEWS-001-v1](02-market-analysis/REQ-NEWS-001-v1.md) |
| [Signals Risk](03-signals-risk/README.md) | [REQ-RISK-001-v1](03-signals-risk/REQ-RISK-001-v1.md), [REQ-T0-001-v1](03-signals-risk/REQ-T0-001-v1.md), [REQ-T0-002-v1](03-signals-risk/REQ-T0-002-v1.md) |
| [Position Management](04-position-management/README.md) | [REQ-POS-001-v1](04-position-management/REQ-POS-001-v1.md), [REQ-POS-002-v1](04-position-management/REQ-POS-002-v1.md) |
| [Research Backtesting](05-research-backtesting/README.md) | [REQ-BT-001-v1](05-research-backtesting/REQ-BT-001-v1.md), [REQ-BT-002-v1](05-research-backtesting/REQ-BT-002-v1.md) |
| [Reporting](06-reporting/README.md) | [REQ-REPORT-001-v2](06-reporting/REQ-REPORT-001-v2.md), [REQ-REPORT-002-v1](06-reporting/REQ-REPORT-002-v1.md) |
| [Memory Delivery](07-memory-delivery/README.md) | [REQ-MEM-001-v1](07-memory-delivery/REQ-MEM-001-v1.md) |
| [Collaboration](08-collaboration/README.md) | [REQ-COLLAB-001-v1](08-collaboration/REQ-COLLAB-001-v1.md) |

## IDs and revisions

Format: **REQ-SECTION-NNN-vN**, for example `REQ-T0-002-v1`. The stable family `REQ-T0-002` identifies the requirement; `-v1`, `-v2`, etc. identifies the exact revision. File names and H1 headings include the full ID. Never reuse a family for unrelated work.

One requirement per Markdown file. Sections have their own README. [current.json](current.json) lists one latest revision per family, including proposals; “current revision” does not mean approved or implemented.

A real version chain is included: [REQ-REPORT-001-v1](06-reporting/REQ-REPORT-001-v1.md) captures the previous ivory design; [REQ-REPORT-001-v2](06-reporting/REQ-REPORT-001-v2.md) captures the requested dark design.

## Status versus coverage

- **Active**: governing baseline from documented repository behavior or an explicit user request. This initial capture is not a claim of independent stakeholder sign-off.
- **Proposed**: needs maintainer discussion/acceptance. Review findings are proposals until agreed.
- **Superseded**: retained for history; a newer revision replaces it.
- **Coverage** is separate: Implemented, Partial, Not implemented, or Historical. Acceptance checkboxes remain unchecked until a reviewer records evidence for that revision; “Implemented” alone is not test sign-off.

## Changing a requirement

1. Discuss the problem in an issue and cite the exact current ID. Use [the template](_template.md).
2. For a new capability, choose the next unused number in its section and start at `-v1`.
3. For a behavioral or acceptance-criteria change, copy the current file to `-vN+1`, set `Supersedes` to the previous ID, and explain the change. Preserve the prior requirement text and criteria; only its lifecycle status may change to Superseded.
4. Keep the new revision Proposed during discussion and update the section README, this index and current.json when adding it. Upon maintainer acceptance, update its status and coverage and mark the replaced revision Superseded in the same PR. A proposal can be the latest revision while the previous Active revision remains governing until acceptance; current.json records latest, not approval.
5. Typo/link fixes or new verification evidence do not require a version bump if semantics remain identical. Record the correction in revision notes and rely on Git history. Never silently rewrite a previous decision.
6. PRs cite full IDs, affected criteria, code/tests, migration impact and remaining gaps. Do not bump the requirement version for a code fix that simply meets the existing requirement.

Owners start Unassigned so nobody is assigned without agreement. Claim work through an issue; the maintainer coordinates ownership and reviews changes.

## First contribution opportunities

Start with [the integration review](../docs/reviews/eb92411.md). F1/F2 cover fast T0 integrity/expiry; F3/F4 cover partial-position state and quantities; F5/F6 cover simulation semantics and statistics. Pick one requirement and add a focused failing test before implementing its fix. UI contributors can work on REPORT; data contributors on DATA; documentation contributors on acceptance criteria and evidence.

Run `python3 scripts/check_requirements.py` before proposing a change. See [CONTRIBUTING.md](../CONTRIBUTING.md) for setup, relevant tests and PR expectations.
