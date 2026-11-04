#!/usr/bin/env python3
"""Excel export values for grid columns whose cell is a container (fieldSet).

Workday can't export a fieldSet cell on its own: the whole export fails with "attempted to resolve
exporter, but no exporter found for widget ...StandardFieldSet" (live 2026-11-04, Audit Log), and the
docs say such columns need an `excel.value` (developer.workday.com "column", "Concept: grid").
The grid view doesn't change. Static check Static.excelFieldSet fails on any column left without one.
"""
import json, os

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'presentation')
VALUES = {
    ('auditLogViewer', 'columnOrganization'): "<% logEntry.coName ?? '' %>",
    ('auditLogViewer', 'columnRole'): "<% logEntry.roleName ?? '' %>",
    ('auditLogViewer', 'columnPosition'): "<% logEntry.positionName ?? '' %>",
    ('auditLogViewer', 'columnChangedBy'): "<% logEntry.triggeredBy ?? '' %>",
}
changed = []
for page in sorted({p for p, _ in VALUES}):
    path = os.path.join(ROOT, page + '.pmd')
    raw = open(path, encoding='utf-8').read()
    d = json.loads(raw)

    def walk(n):
        if isinstance(n, dict):
            if n.get('type') == 'column' and (page, n.get('columnId')) in VALUES:
                want = {"value": VALUES[(page, n['columnId'])]}
                if n.get('excel') != want:
                    n['excel'] = want
                    changed.append(f"{page}.{n['columnId']}")
            for v in n.values():
                walk(v)
        elif isinstance(n, list):
            for v in n:
                walk(v)
    walk(d)
    new = json.dumps(d, indent=2, ensure_ascii=False) + '\n'
    if new != raw:
        open(path, 'w', encoding='utf-8').write(new)
print('excel export values: ' + (', '.join(changed) or 'already set'))
