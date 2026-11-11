# REQ-COLLAB-001-v1 — Versioned requirements and contributor traceability

ID: REQ-COLLAB-001-v1
Status: Active
Coverage: Implemented
Owner: Unassigned
Updated: 2026-11-11
Supersedes: None

## Requirement

Every requirement must have a stable family ID and an explicit revision suffix, with ownership, acceptance criteria and implementation/verification links.

## Acceptance criteria

- [ ] AC1: Filename and heading match REQ-SECTION-NNN-vN.
- [ ] AC2: A changed Active requirement is copied to vN+1; prior text and criteria are retained.
- [ ] AC3: Supersedes links and the current-version index identify the revision chain.
- [ ] AC4: PRs reference exact versioned IDs and state which acceptance criteria were checked.
- [ ] AC5: Proposed work is not labeled implemented.

## Implementation references

- [requirements/README.md](../../requirements/README.md)
- [CONTRIBUTING.md](../../CONTRIBUTING.md)
- [scripts/check_requirements.py](../../scripts/check_requirements.py)

## Verification

- python3 scripts/check_requirements.py

## Revision notes

Initial documented baseline or proposal. No prior revision.
