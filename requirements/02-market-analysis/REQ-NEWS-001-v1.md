# REQ-NEWS-001-v1 — Dated news and event provenance

ID: REQ-NEWS-001-v1
Status: Active
Coverage: Partial
Owner: Unassigned
Updated: 2026-11-11
Supersedes: None

## Requirement

Material news and event dates must carry source URLs, publication dates and provenance; cached news must not prevent searching for corrections.

## Acceptance criteria

- [ ] AC1: Retained sources conform to the whitelist.
- [ ] AC2: Unknown event dates remain unknown and block applicable signals.
- [ ] AC3: A completed search is not presented as proof of no material news.
- [ ] AC4: News-page instructions cannot override the skill.

## Implementation references

- [skills/egx-check/references/news-sources.md](../../skills/egx-check/references/news-sources.md)
- [skills/egx-check/scripts/egx_gates.py](../../skills/egx-check/scripts/egx_gates.py)

## Verification

- python3 tests/test_egx.py
- Manual provenance check remains necessary; opened flags are model-supplied.

## Revision notes

Initial documented baseline or proposal. No prior revision.
