#!/usr/bin/env python3
"""Small UI fixes (2026-11-04 review).

- ISC Queue: "Role Name" and "Workday Assignable Role" showed the same name side by side in a 13-column grid.
  One "Role" column now shows the role name and keeps the Workday role link (related actions) once it exists.
  (Grid columns can't be hidden per view: no documented column render/visible attribute, so Approved By / Date stay.)
Idempotent; runs after grid_style.py.
"""
import json, os
p = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'presentation', 'iscRoleRequestsView.pmd')
raw = open(p, encoding='utf-8').read()
d = json.loads(raw)


def walk(n):
    if isinstance(n, dict):
        if n.get('type') == 'grid' and n.get('id') == 'allPendingGrid':
            cols = n['columns']
            ids = [c.get('columnId') for c in cols]
            if 'colWdRoleName' in ids:
                wd = cols[ids.index('colWdRoleName')]
                wd['label'] = 'Role'
                wd['cellTemplate']['instanceList'][0]['descriptor'] = "<% role.roleName ?? '' %>"
                wd['excel'] = {"value": "<% role.roleName ?? '' %>"}
                if 'colRoleName' in ids:
                    i = ids.index('colRoleName')
                    cols.remove(wd)
                    cols[i] = wd
        for v in n.values(): walk(v)
    elif isinstance(n, list):
        for v in n: walk(v)


walk(d)
new = json.dumps(d, indent=2, ensure_ascii=False) + '\n'
if new != raw:
    open(p, 'w', encoding='utf-8').write(new)
print('ui_tweaks: ' + ('ISC Queue role columns merged' if new != raw else 'no change'))
