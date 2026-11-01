#!/usr/bin/env python3
"""UI polish pass (2026-10-31 live review). Idempotent: run it after any builder in tools/.

- Grid labels: no '(n)' count in the label; Workday already shows 'n items' next to it.
- About boxes: every 'About This Page/Tab' text starts with the blue ⓘ, like the rest of the app.
- Audit actions: shown in sentence case ('Assign position'), matching the Changes by Action legend.
- ISC queue: one About box first (intro merged in), then the cards, as on the other list pages.
- Audit Log: the Changes by Action chart sits with the filters it reflects.
- Shell Org Manager, Manage Role Assignments tab: About This Tab box like the other tabs.
- 'Admin Provisioning' in page text is the AAA Role Provisioning page.
"""
import json, os, re

ROOT = os.path.join(os.path.dirname(__file__), '..', 'presentation')
INFO = '<span style="color:#0055B7;font-size:12px;font-weight:700">ⓘ </span>'
BODY = '<span style="color:#374151;font-size:12px">'

GRID_LABELS = {
    ('auditLogViewer', 'AuditLogGrid'): 'Audit Log',
    ('bulkRoleResults', 'uploadsGrid'): 'My Uploads',
    ('bulkRoleResults', 'rowResultsGrid'): 'Rows',
    ('bulkRoleTemplate', 'bulkTemplateGrid'): 'Role Assignments',
    ('shellOrgDetail', 'orgRolesGrid'): 'Role Assignments',
    ('shellOrgDetail', 'orgHistoryGrid'): 'Changes',
    ('shellOrgManager', 'appsGrid'): 'Applications',
    ('shellOrgManager', 'patternsGrid'): "<% 'Patterns for ' + (queryParams.appName ?? queryParams.appCode ?? '') %>",
    ('shellOrgManager', 'allShellOrgsGrid'): 'Shell Organizations',
    ('shellOrgManager', 'filteredShellOrgsGrid'): "<% 'Shell Organizations for ' + (queryParams.appName ?? queryParams.appCode ?? '') %>",
}
ACTION = re.compile(r"^<% (\w+)\.action \?\? '' %>$")


def load(n):
    return json.load(open(os.path.join(ROOT, n + '.pmd')))


def save(n, d, before):
    if json.dumps(d) != before:
        open(os.path.join(ROOT, n + '.pmd'), 'w').write(json.dumps(d, indent=2, ensure_ascii=False) + '\n')
        return True
    return False


def walk(o, fn):
    if isinstance(o, dict):
        fn(o)
        for v in list(o.values()):
            walk(v, fn)
    elif isinstance(o, list):
        for v in o:
            walk(v, fn)


def find(o, id_):
    hit = []
    walk(o, lambda x: hit.append(x) if x.get('id') == id_ else None)
    return hit[0] if hit else None


changed = []
for f in sorted(os.listdir(ROOT)):
    if not f.endswith('.pmd'):
        continue
    n = f[:-4]
    d = load(n)
    before = json.dumps(d)

    def fix(o):
        if o.get('type') == 'grid' and (n, o.get('id')) in GRID_LABELS:
            o['label'] = GRID_LABELS[(n, o['id'])]
        if o.get('type') == 'fieldSet' and str(o.get('title', '')).startswith('About This'):
            for k in o.get('children', []):
                v = k.get('value')
                if k.get('type') == 'richText' and isinstance(v, str) and v.startswith(BODY):
                    k['value'] = INFO + v
                break
        if o.get('type') == 'text' and isinstance(o.get('value'), str):
            m = ACTION.match(o['value'])
            if m:
                a = m.group(1) + '.action'
                o['value'] = "<% empty(" + a + ") ? '' : (" + a + ".substring(0, 1) + " + a + ".substring(1).lowerCase()) %>"
        v = o.get('value')
        if o.get('type') == 'richText' and isinstance(v, str) and 'Admin Provisioning' in v:
            o['value'] = v.replace('Admin Provisioning', 'AAA Role Provisioning')
    walk(d, fix)

    pr = d.get('presentation', {})
    if n == 'iscRoleRequestsView':
        secs = pr['body']['sections']
        ids = [s.get('id') for s in secs]
        if 'descSection' in ids:
            desc = find(secs[ids.index('descSection')], 'pageDesc')['value']
            info = find(pr, 'maintainActionInfo')
            static = info['value'].replace(INFO, '').replace("\\'", "'").replace("'", "\\'")
            m = re.match(r"^<% (.*) %>$", desc, re.S)
            info['value'] = "<% " + m.group(1).replace('<span style="color:#374151', INFO + '<span style="color:#374151', 1) + " + '<br><br>' + '" + static + "' %>"
            secs.pop(ids.index('descSection'))
        ids = [s.get('id') for s in secs]
        if ids.index('actionsInfoSection') > ids.index('summaryCardsSection'):
            secs.insert(ids.index('summaryCardsSection'), secs.pop(ids.index('actionsInfoSection')))
    if n == 'auditLogViewer':
        secs = pr['body']['sections']
        ids = [s.get('id') for s in secs]
        if 'auditChartSection' in ids:
            chart = find(secs[ids.index('auditChartSection')], 'auditChartCardContainer')['cards']
            filt = find(pr, 'auditFilterCardContainer')
            filt['cards'] = filt['cards'] + chart
            filt['layout'] = 'masonry'
            secs.pop(ids.index('auditChartSection'))
    if n == 'shellOrgManager':
        tab = [t for t in pr['tabs'] if t.get('label') == 'Manage Role Assignments'][0]
        kids = tab['children']
        if not any(k.get('id') == 'rolesAboutFieldSet' for k in kids):
            ra = [k for k in kids if k.get('id') == 'roleAssignmentsFieldSet'][0]
            note = [c for c in ra['children'] if c.get('id') == 'roleAssignmentsNote'][0]
            ra['children'].remove(note)
            if note['value'].startswith(BODY):
                note['value'] = INFO + note['value']
            kids.insert(kids.index(ra), {"type": "fieldSet", "id": "rolesAboutFieldSet", "title": "About This Tab", "children": [note]})
    if save(n, d, before):
        changed.append(n)
print('polish changed:', changed)
