#!/usr/bin/env python3
"""Assignable Role Manager speed (2026-11-04; page took about 1.2 s).

- allPositions: an eager WQL query nothing on the page reads (and its query component returns 0 rows); dropped.
- positions: the Staffing jobs collection, only used to name the positions of old requests saved before
  positionNames existed (the REST default also caps it at 20 positions, so the names were often missing anyway).
  Requests store positionNames now, so the column shows those alone. Idempotent.
"""
import json, os, re
p = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'presentation', 'assignableRoleManager.pmd')
raw = open(p, encoding='utf-8').read()
d = json.loads(raw)
OLD = ("<% !empty(role.positionNames) ? role.positionNames : (empty(role.positions) || empty(positions.data) ? '' : "
       "positions.data.filter(p => { role.positions.contains(p.id) }).map(p => { p.descriptor }).join(', ')) %>")
s = json.dumps(d, ensure_ascii=False).replace(json.dumps(OLD)[1:-1], json.dumps("<% role.positionNames ?? '' %>")[1:-1])
d = json.loads(s)
for name in ('allPositions', 'positions'):
    if not re.search(r'(?<![\w.])' + name + r'\.(data|total|invoke)', json.dumps(d)):
        d['endPoints'] = [e for e in d['endPoints'] if e['name'] != name]
new = json.dumps(d, indent=2, ensure_ascii=False) + '\n'
if new != raw:
    open(p, 'w', encoding='utf-8').write(new)
print('arm_speed: ' + ('unused position lists dropped' if new != raw else 'no change'))
