#!/usr/bin/env python3
"""Audit Log speed (2026-11-04, timed: the page took 2.1-2.4 s).

1. Lookup lists dropped. The Audit Log loaded every shell org (609 rows, ~560 ms), every shell role and every AAA role
   only to fill in org / role links for old records written before audit records stored orgWid / roleWid. Those
   records were backfilled (`repair --backfill-wids`), so the page now uses the stored WIDs alone; a record
   without one shows its name as plain text, as before.
2. Graph pages 1-4 are skipped (`exclude`) while page 0's total says they'd be empty; before, each repeated
   offset 0 to keep the Graph cache rule (tools/graphql_audit.py), costing four calls for nothing.
Runs after graphql_audit.py. Idempotent.
"""
import json, os

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'presentation')
PAGES = ['auditLogViewer', 'comsInsights', 'shellOrgDetail', 'accessReview', 'confirmAccessReview']
TOTAL = "((!empty(auditPage0.data) && !empty(auditPage0.data.r)) ? (auditPage0.data.r.total ?? 0) : 0)"
LOOKUP = ("let codes = logs.filter(e => { empty(e.orgWid) && !empty(e.coName) }).map(e => { e.coName }); "
          "let names = logs.filter(e => { empty(e.roleWid) && !empty(e.roleName) }).map(e => { e.roleName }); "
          "let orgs = size(codes) == 0 ? [] : (allShellOrgs.data ?? []).filter(o => { !empty(o.organizationByName) && codes.contains(o.code) }).map(o => { { 'code': o.code, 'id': o.organizationByName.id } }); "
          "let roles = size(names) == 0 ? [] : list:flatten([shellRoles.data ?? [], aaaRoles.data ?? []]).filter(r => { !empty(r.role) && names.contains(r.role.descriptor) }).map(r => { { 'name': r.role.descriptor, 'id': r.role.id } }); ")
PER_ROW = ("let om = empty(e.orgWid) ? orgs.filter(o => { o.code == (e.coName ?? '') }) : []; "
           "let rm = empty(e.roleWid) ? roles.filter(r => { r.name == (e.roleName ?? '') }) : []; ")
SWAPS = [(LOOKUP, ''), (PER_ROW, ''),
         ("'orgWid': !empty(e.orgWid) ? e.orgWid : (size(om) > 0 ? om[0].id : '')", "'orgWid': e.orgWid ?? ''"),
         ("'roleWid': !empty(e.roleWid) ? e.roleWid : (size(rm) > 0 ? rm[0].id : '')", "'roleWid': e.roleWid ?? ''")]
out = []
for page in PAGES:
    p = os.path.join(ROOT, page + '.pmd')
    raw = open(p, encoding='utf-8').read()
    d = json.loads(raw)
    for e in d['endPoints']:
        if e['name'].startswith('auditPage') and e['name'][9:].isdigit() and int(e['name'][9:]) > 0:
            e['exclude'] = f"<% {TOTAL} <= {int(e['name'][9:]) * 100} %>"
    if page == 'auditLogViewer':
        s = json.dumps(d, ensure_ascii=False)
        for a, b in SWAPS:
            s = s.replace(json.dumps(a)[1:-1], json.dumps(b)[1:-1])
        d = json.loads(s)
        left = json.dumps(d)
        for name in ('allShellOrgs', 'shellRoles', 'aaaRoles'):
            if left.count(name + '.') == 0:
                d['endPoints'] = [e for e in d['endPoints'] if e['name'] != name]
    new = json.dumps(d, indent=2, ensure_ascii=False) + '\n'
    if new != raw:
        open(p, 'w', encoding='utf-8').write(new)
        out.append(page)
print('audit_speed: ' + (', '.join(out) or 'no change'))
