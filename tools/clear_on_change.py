#!/usr/bin/env python3
"""A field that OK flagged clears its error as soon as the user changes it (negative tests 2026-11-05).

Found live on Edit Role Assignment: OK with no positions gave "Select at least one position to add or remove.";
picking a position afterwards left the error showing, and Workday refuses OK while an error shows, so the user was
stuck until a reload (CLAUDE.md "Widget validation"). The same gap was on Submit Assignable Role Request (Custom
Organization) and AAA Role Request (Application, Effective Date).

For every widget an onSubmit calls setError on, on the pages below: its onChange starts with self.clearError()
(added when missing; a new onChange when it has none). EXTRA: other fields whose change also makes the error moot.
Idempotent. Static check Static.clearOnChange reports the pages not listed here.
"""
import json, os, re

R = os.path.join(os.path.dirname(__file__), '..', 'presentation')
PAGES = ['editRoleAssignment', 'bulkRoleGrid', 'assignableRoleManager', 'adminProvisioning', 'newShellOrg',
         'bulkRoleChanges', 'deleteAssignableRole', 'manageShellOrgStatus']
# A fileUploader has no onChange; its event is onFileAdd (developer.workday.com "fileUploader", 2026-11-05).
EVENT = {'fileUploader': 'onFileAdd'}
SKIP_TYPES = set()
# (page, widget whose change clears, event) -> widgets whose OK error it clears ("add or remove": either list fixes it).
# Bulk Edit puts its grid-level errors (no changes yet, over 50, duplicate row, already holds the role, role/org
# missing) on Effective Date, so every grid change clears it too (regression 2026-11-05: ticking Remove left
# "No changes yet" showing and OK refused). OK re-checks the date anyway.
_BULK_DATE = ['effectiveDate']
EXTRA = {('editRoleAssignment', 'positionsToRemoveInstanceList', 'onChange'): ['positionsToAddInstanceList'],
         ('bulkRoleGrid', 'removeCheckBox', 'onChange'): _BULK_DATE,
         ('bulkRoleGrid', 'positionAddList', 'onChange'): _BULK_DATE,
         ('bulkRoleGrid', 'roleOrgDropdown', 'onChange'): _BULK_DATE,
         ('bulkRoleGrid', 'addGrid', 'onRowRemove'): _BULK_DATE,
         ('bulkRoleGrid', 'addGrid', 'onRowAdd'): _BULK_DATE}


def index(n, out):
    if isinstance(n, dict):
        if n.get('id'): out[n['id']] = n
        for v in n.values(): index(v, out)
    elif isinstance(n, list):
        for v in n: index(v, out)
    return out


def add_clear(w, call, ev='onChange'):
    oc = w.get(ev)
    if not isinstance(oc, str) or not oc.strip():
        w[ev] = f'<% {call} %>'
        return True
    oc = oc.replace('self.clearError(); self.clearError()', 'self.clearError()')  # an earlier run doubled it
    w[ev] = oc
    if call.rstrip(';') in oc: return False
    m = re.match(r'\s*<%', oc)
    assert m, w.get('id')
    w[ev] = oc[:m.end()] + f'\n  {call}' + oc[m.end():]
    return True


for page in PAGES:
    p = os.path.join(R, page + '.pmd')
    d = json.load(open(p))
    ids = index(d.get('presentation', {}), {})
    sub = d.get('onSubmit') or ''
    changed = []
    for t in sorted(set(re.findall(r'(\w+)\.setError\(', sub))):
        w = ids.get(t)
        if w is None or w.get('enabled') in (False, 'false'): continue
        if w.get('type') in SKIP_TYPES: continue
        ev = EVENT.get(w.get('type'), 'onChange')
        oc = str(w.get(ev, ''))
        if f'{t}.clearError()' in oc or 'self.setError' in oc: continue
        # name the widget rather than self: the docs' onFileAdd example doesn't use self
        call = f'{t}.clearError();' if ev != 'onChange' else 'self.clearError();'
        if add_clear(w, call, ev): changed.append(f'{t}.{ev}')
    for (pg, src, ev), targets in EXTRA.items():
        if pg != page: continue
        for t in targets:
            if add_clear(ids[src], f'{t}.clearError();', ev): changed.append(f'{src}.{ev}->{t}')
    open(p, 'w').write(json.dumps(d, indent=2, ensure_ascii=False) + '\n')
    print(f"{page}: {', '.join(changed) if changed else 'nothing to add'}")
