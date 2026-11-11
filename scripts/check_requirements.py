#!/usr/bin/env python3
"""Validate the versioned requirements register using only the standard library."""
import json
import re
import sys
from pathlib import Path


def check(root):
    errors, records, families = [], {}, {}
    for path in sorted(root.glob('*/REQ-*.md')):
        content = path.read_text()
        fields = dict(re.findall(r'^(ID|Status|Coverage|Owner|Updated|Supersedes): (.+)$', content, re.M))
        rid = fields.get('ID', '')
        match = re.fullmatch(r'(REQ-[A-Z0-9]+-\d{3})-v([1-9]\d*)', rid)
        def fail(message):
            errors.append(f'{path.relative_to(root)}: {message}')
        if not match:
            fail('invalid or missing versioned ID')
            continue
        family, version = match[1], int(match[2])
        if rid in records:
            fail('duplicate ID')
        records[rid] = (path, fields)
        families.setdefault(family, []).append((version, rid, fields))
        if path.stem != rid or not content.startswith(f'# {rid} — '):
            fail('filename and heading must match the full ID')
        for field in ('Owner', 'Updated', 'Supersedes'):
            if not fields.get(field):
                fail(f'missing {field}')
        if fields.get('Status') not in ('Active', 'Proposed', 'Superseded'):
            fail('invalid Status')
        if fields.get('Coverage') not in ('Implemented', 'Partial', 'Not implemented', 'Historical'):
            fail('invalid Coverage')
        for section in ('Requirement', 'Acceptance criteria', 'Implementation references', 'Verification', 'Revision notes'):
            if not re.search(r'^## ' + re.escape(section) + r'\n\n\S', content, re.M):
                fail(f'missing or empty {section}')
        if not re.search(r'^- \[[ x]\] AC\d+: .+', content, re.M):
            fail('missing numbered acceptance criteria')
        for link in re.findall(r'\]\(([^)]+)\)', content):
            if '://' in link or link.startswith('#'):
                continue
            target = link.split('#')[0]
            if not (path.parent / target).exists():
                fail(f'broken local link: {link}')
    try:
        current = json.loads((root / 'current.json').read_text())
        if not isinstance(current, list):
            raise ValueError('expected an array')
        seen = set()
        for row in current:
            rid = row['id']
            if rid in seen:
                errors.append(f'current.json: duplicate {rid}')
            seen.add(rid)
            if rid not in records:
                errors.append(f'current.json: unknown {rid}')
            elif records[rid][0] != root / row['path']:
                errors.append(f'current.json: path mismatch for {rid}')
        expected = {max(rows)[1] for rows in families.values()}
        if seen != expected:
            errors.append(f'current.json: must contain exactly the latest revision of each family; missing={sorted(expected-seen)}, extra={sorted(seen-expected)}')
    except (ValueError, OSError, KeyError, TypeError) as exc:
        errors.append(f'current.json: {exc}')
    for family, rows in families.items():
        rows.sort()
        if [r[0] for r in rows] != list(range(1, rows[-1][0] + 1)):
            errors.append(f'{family}: revisions must be consecutive from v1')
        for version, rid, fields in rows:
            previous = 'None' if version == 1 else f'{family}-v{version-1}'
            if fields.get('Supersedes') != previous:
                errors.append(f'{rid}: Supersedes must be {previous}')
            if version == rows[-1][0] and fields.get('Status') == 'Superseded':
                errors.append(f'{rid}: latest revision cannot be Superseded')
            if version < rows[-1][0] and fields.get('Status') != 'Superseded':
                if not (fields.get('Status') == 'Active' and all(r[2].get('Status') == 'Proposed' for r in rows if r[0] > version)):
                    errors.append(f'{rid}: older revision must be Superseded, or Active while its replacements are Proposed')
    if not records:
        errors.append('no requirement files found')
    return errors, len(records), len(families)


if __name__ == '__main__':
    root = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path(__file__).resolve().parents[1] / 'requirements'
    errors, revisions, families = check(root)
    for error in errors:
        print(f'ERROR: {error}', file=sys.stderr)
    if errors:
        sys.exit(1)
    print(f'Requirements OK: {revisions} revisions across {families} families')
