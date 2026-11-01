#!/usr/bin/env python3
"""UI polish pass (2026-10-31 live review). Idempotent: run it after any builder in tools/.

- Grid labels: no '(n)' count in the label; Workday already shows 'n items' next to it.
- About boxes: every 'About This Page/Tab' text starts with the blue ⓘ, like the rest of the app.
- Audit actions: shown in sentence case ('Assign position'), matching the Changes by Action legend.
- ISC queue: one About box first (intro merged in), then the cards, as on the other list pages.
- Audit Log: the Changes by Action chart sits with the filters it reflects.
- Shell Org Manager, Manage Role Assignments tab: About This Tab box like the other tabs.
- Page names match the buttons that open them (2026-11-01): My Assignable Role Requests, AAA Role Requests,
  ISC Queue. Timestamps in Pacific time.
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
# Timestamps are stored in UTC ('2026-11-01T01:31:03Z'); show them in Pacific time, to the minute, with the
# zone name from the date ('PDT' / 'PST'). developer.workday.com formatDateWithTimeZones (SimpleDateFormat).
UTC_TS = [re.compile(r"\(([\w.\[\]]+) \?\? ''\)\.replace\('T', ' '\)\.replace\('Z', ' UTC'\)"),
          re.compile(r"\(([\w.\[\]]+) \?\? ''\)\.replace\('T', ' '\)\.replace\('Z', ''\) \+ ' UTC'")]


def pacific(v):
    return ("(empty(" + v + ") ? '' : date:formatDateWithTimeZones(" + v + ".substring(0, 19).replace('T', ' '), "
            "'UTC', 'yyyy-MM-dd HH:mm:ss', 'America/Los_Angeles', 'yyyy-MM-dd HH:mm z'))")


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
        if o.get('type') == 'fieldSet' and o.get('title') in ('About FUH Administration', 'How It Works', 'How to Use This Template'):
            o['title'] = 'About This Page'
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
        for key in ('value', 'parameters'):
            if isinstance(o.get(key), str):
                for rx in UTC_TS:
                    o[key] = rx.sub(lambda m: pacific(m.group(1)), o[key])
        v = o.get('value')
        if o.get('type') == 'richText' and isinstance(v, str) and 'Admin Provisioning' in v:
            o['value'] = v.replace('Admin Provisioning', 'AAA Role Requests')
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
    # page names match the buttons that open them (product owner, 2026-11-01)
    RENAME = [('Assignable Role Manager', 'My Assignable Role Requests'), ('AAA Role Provisioning', 'AAA Role Requests'),
              ('AAA Provisioning Requests', 'AAA Role Requests')]
    def rename(o):
        for key in ('label', 'title', 'value'):
            v = o.get(key)
            if isinstance(v, str) and o.get('type') in ('button', 'richText', 'text', 'fieldSet', 'grid', 'title', None):
                for a, b in RENAME:
                    v = v.replace(a, b)
                o[key] = v
    walk(pr, rename)
    if n == 'iscRoleRequestsView':
        t = pr['title']['label']
        pr['title']['label'] = t.replace("'ECO-COMS: ' + (", "'ECO-COMS: ISC Queue – ' + (", 1).replace(" + ' (ISC)' %>", " %>")
    # request forms: the intro text goes in an About This Page box, as on every other page
    if n in ('adminProvisioning', 'assignableRoleManager'):
        def wrap(o):
            kids = o.get('children')
            if o.get('type') == 'layoutSection' and isinstance(kids, list):
                for i, k in enumerate(kids):
                    if isinstance(k, dict) and k.get('id') == 'pageDesc' and k.get('type') == 'richText':
                        kids[i] = {"type": "fieldSet", "id": "aboutFieldSet", "title": "About This Page", "children": [k]}
        walk(pr, wrap)
        walk(pr, fix)  # adds the ⓘ to the new About box
    # the AAA form was copied from the assignable one; its wording still said "Assignable Role"
    if n == 'adminProvisioning':
        AAA = [('Submit and manage Assignable Role requests by Application. Review pending requests or submit a new role request for ISC review.',
                'Submit and manage your AAA (Organizations and Roles Assignment Administrator) role requests by Application. Review your pending requests or submit a new one for ISC review.'),
               ('Submit a new Assignable Role request using the Application below.', 'Submit a new AAA role request using the Application below.')]
        def aaa(o):
            if o.get('id') == 'assignableRolesGrid':
                o['label'] = 'Pending AAA Role Requests'
            if o.get('type') == 'fieldSet' and o.get('title') == '2. Submit New Assignable Role Request':
                o['title'] = '2. Submit New AAA Role Request'
            if o.get('type') == 'richText' and isinstance(o.get('value'), str):
                for a, b in AAA:
                    o['value'] = o['value'].replace(a, b)
        walk(pr, aaa)
    # review 3 (2026-11-01): wording on forms, wizards and confirmation pages
    TEXT = {
        'createShellOrgWizard': [('Create New Shell Organization', 'Add New Shell Organization')],
        'newShellOrgPattern': [('ECO-COMS: New Shell Org Pattern', 'ECO-COMS: Add New Shell Org Pattern'),
                               ('Patterns define the CO naming structure used to create Custom Organizations in Workday.',
                                'A pattern defines how Custom Organization names are built for course-based roles.')],
        'manageShellOrgStatus': [('⚠ Warning: ', '⚠ '), ('Impact of Activating', 'Impact of Reactivating')],
        'deleteAssignableRole': [('recorded in the audit log', 'recorded in the Audit Log')],
        'newShellOrgPatternSuccess': [('The Custom Organization has been created in Workday.', 'The pattern has been created in Workday.'),
                                      ('The Shell Org Pattern has been submitted to Workday via the orchestration. Check Shell Org Manager for the new pattern.',
                                       'A record of this change is in the Audit Log. The card below shows your most recent pattern created through ECO-COMS.')],
        'roleAssignmentSuccess': [('as ASSIGN POSITION or REMOVE POSITION', 'as Assign position or Remove position'),
                                  ('Positions added', 'Positions Added'), ('Positions removed', 'Positions Removed')],
        'bulkRoleApply': [('Batch reference', 'Batch Reference'), ('VALID rows (will be applied)', 'VALID Rows (Will Be Applied)'),
                          ('INVALID rows', 'INVALID Rows')],
        'reviewRoleRequestAssignableRole': [('removes it from Pending ISC Requests', 'removes it from the ISC Queue')],
        # after the page renames these sentences named list pages as where requests come from
        'iscRoleRequestsView': [("roles from AAA Role Requests'", "roles'"), ("for assignable roles from My Assignable Role Requests'", "for assignable roles'"),
                                ("'from both My Assignable Role Requests and AAA Role Requests'", "'for both assignable and AAA roles'"),
                                ("Administrator request from AAA Role Requests, for someone", "Administrator request (Submit AAA Role Request), for someone"),
                                ("requested from My Assignable Role Requests", "requested with Submit Assignable Role Request")],
    }
    if n in TEXT:
        def text(o):
            for key in ('label', 'title', 'subtitle', 'value'):
                if isinstance(o.get(key), str):
                    for a, b in TEXT[n]:
                        o[key] = o[key].replace(a, b)
        walk(pr, text)
    # the pattern form's Application field and preview had no heading of their own
    if n == 'newShellOrgPattern':
        secs = pr['body']['sections']
        fs = [s for s in secs if s.get('id') == 'formSection'][0]
        loose = [k for k in fs['children'] if k.get('id') in ('selectedApplicationId', 'patternPreview')]
        if loose:
            fs['children'] = [{"type": "fieldSet", "id": "patternDetailsFieldSet", "title": "Pattern Details", "children": loose}] + \
                             [k for k in fs['children'] if k not in loose]
    # Withdraw: opened with view=aaa from the AAA pages; name the request type it lists
    if n == 'deleteAssignableRole':
        # opened from Workday search there's no view: it then lists both kinds, so name neither (2026-11-01 test)
        KIND = "(queryParams.view == 'aaa' ? 'AAA ' : (queryParams.view == 'assignable' ? 'Assignable ' : ''))"
        OLD_KIND = "(queryParams.view == 'aaa' ? 'AAA' : 'Assignable')"
        def kind(o):
            for key in ('title', 'label'):
                v = o.get(key)
                if v == 'My Pending Assignable Role Requests' or (isinstance(v, str) and OLD_KIND in v and 'My Pending' in v):
                    o[key] = "<% 'My Pending ' + " + KIND + " + 'Role Requests' %>"
        t = pr['title']['label']
        if not t.startswith('<%') or OLD_KIND in t:
            pr['title']['label'] = "<% 'ECO-COMS: Withdraw ' + " + KIND + " + 'Role Request' %>"
        walk(pr, kind)
    if save(n, d, before):
        changed.append(n)
print('polish changed:', changed)
