#!/usr/bin/env python3
"""Count cards you can click (product owner 2026-11-06: "for all these without CTA, add a quick filter of data").

Every CountCard (a title, a subtitle and a count, no button) becomes a pill card whose one pill is the count:
- On a page with a list, the pill filters that list (`quick=<key>`, or the page's own `status` filter on the ISC
  queue) and shows ✓ while the filter is on; clicking it again clears the filter.
- On pages without a list of their own (Insights, Shell Org Detail) the pill opens the list it counts, filtered.

One card file per target page (`Quick<Task>Card`), because a pill's taskId can't come from a parameter. Each pill
carries every query parameter that page uses, so a filter doesn't drop the others (CLAUDE.md "pillCard").

Runs late in rebuild_all (after apply_icons). Earlier steps expect the CountCard pages, so this step keeps each
page it changes in tools/quick_src/, and `--restore` (at the start of rebuild_all) puts them back.
"""
import glob, json, os, shutil, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, '..', 'presentation')
SRC = os.path.join(HERE, 'quick_src')

if '--restore' in sys.argv:
    for p in glob.glob(os.path.join(SRC, '*.pmd')):
        shutil.copyfile(p, os.path.join(ROOT, os.path.basename(p)))
    print('quick_filters --restore: pages with their count cards as built')
    sys.exit(0)

Q = "(queryParams.quick ?? '')"


def filt(key):
    """A filter on the page's own list: on while quick == key; clicking again clears it."""
    return {'mark': f"{Q} == '{key}'", 'quick': f"{Q} == '{key}' ? '' : '{key}'"}


# Target pages and the query parameters their pills carry (all of them, so other filters survive).
TARGETS = {
    'accessReview': ['quick'],
    'adminProvisioningView': ['quick'],
    'assignableRoleManagerView': ['quick'],
    'bulkRoleResults': ['batch', 'quick'],
    'iscRoleRequestsView': ['view', 'status'],
    'shellOrgManager': ['appCode', 'appName', 'family', 'orgType', 'quick'],
    'auditLogViewer': ['orgId', 'orgCode', 'orgName', 'period'],
    'manageShellOrgStatus': ['orgId', 'orgCode', 'orgName', 'currentStatus'],
}
KEEP = lambda *names: {n: f"queryParams.{n} ?? ''" for n in names}
ISC_STATUS = "(queryParams.status ?? '')"
ORG = "((allShellOrgs.data ?? []).filter(o => { (o.workdayID ?? '') == (queryParams.orgId ?? '') }))"

# page -> card title -> (target task, {binding: expression, 'mark': expression})
CARDS = {
    'accessReview': {
        'Vacant Positions': ('accessReview', {'mark': f"{Q} == ''", 'quick': "''"}),
        'Never Reviewed': ('accessReview', filt('never')),
        'Assigned Outside ECO-COMS': ('accessReview', filt('outside')),
    },
    'adminProvisioningView': {
        'Pending': ('adminProvisioningView', filt('pending')),
        'Decided': ('adminProvisioningView', filt('decided')),
    },
    'assignableRoleManagerView': {
        'Pending': ('assignableRoleManagerView', filt('pending')),
        'Decided': ('assignableRoleManagerView', filt('decided')),
    },
    'bulkRoleResults': {
        'Succeeded': ('bulkRoleResults', {**filt('ok'), **KEEP('batch')}),
        'Need Attention': ('bulkRoleResults', {**filt('attention'), **KEEP('batch')}),
    },
    # the ISC queue already filters by `status` ('' = pending); a clicked card that's on goes back to All
    'iscRoleRequestsView': {
        'Pending': ('iscRoleRequestsView', {'mark': f"({ISC_STATUS} == '' || {ISC_STATUS} == 'Pending ISC Review')",
                                            'status': f"({ISC_STATUS} == '' || {ISC_STATUS} == 'Pending ISC Review') ? 'All' : 'Pending ISC Review'", **KEEP('view')}),
        'Overdue': ('iscRoleRequestsView', {'mark': f"{ISC_STATUS} == 'Overdue'",
                                            'status': f"{ISC_STATUS} == 'Overdue' ? 'All' : 'Overdue'", **KEEP('view')}),
        'Approved this month': ('iscRoleRequestsView', {'mark': f"{ISC_STATUS} == 'ApprovedThisMonth'",
                                                        'status': f"{ISC_STATUS} == 'ApprovedThisMonth' ? 'All' : 'ApprovedThisMonth'", **KEEP('view')}),
    },
    'shellOrgManager': {
        'Active': ('shellOrgManager', {**filt('active'), **KEEP('appCode', 'appName', 'family', 'orgType')}),
        'Inactive': ('shellOrgManager', {**filt('inactive'), **KEEP('appCode', 'appName', 'family', 'orgType')}),
        'Patterns': ('shellOrgManager', {**filt('patterns'), **KEEP('appCode', 'appName', 'family', 'orgType')}),
    },
    # no list of their own: open the list they count
    'comsInsights': {
        'ISC Turnaround': ('iscRoleRequestsView', {'view': "''", 'status': "'Approved'"}),
        'Pending ISC Review': ('iscRoleRequestsView', {'view': "''", 'status': "'Pending ISC Review'"}),
        'Approved, Last 30 Days': ('iscRoleRequestsView', {'view': "''", 'status': "'Approved'"}),
        'Changes, Last 30 Days': ('auditLogViewer', {'period': "'30d'"}),
        'Bulk Runs, Last 30 Days': ('bulkRoleResults', {}),
    },
    'shellOrgDetail': {
        'Status': ('manageShellOrgStatus', {**KEEP('orgId', 'orgCode', 'orgName'),
                                            'currentStatus': f"(size({ORG}) > 0 && {ORG}[0].cf_active1 == true) ? 'Active' : 'Inactive'"}),
        'Roles': ('shellOrgManager', {'appCode': "queryParams.orgType ?? ''", 'appName': "queryParams.orgType ?? ''"}),
        'Changes': ('auditLogViewer', {**KEEP('orgId', 'orgCode', 'orgName'), 'period': "'all'"}),
    },
}

PAT = ("(allShellOrgs.data ?? []).filter(o => { (o.code ?? '').contains(':PATTERN') && (empty(queryParams.appCode) || "
       "(o.code ?? '').startsWith(queryParams.appCode + ':PATTERN')) })")
ORGQ = "o => { " + Q + " == 'active' ? o.cf_active1 == true : (" + Q + " == 'inactive' ? o.cf_active1 != true : true) }"
RESQ = ("x => { " + Q + " == 'ok' ? (x.result == 'DONE' || x.result == 'VALID') : (" + Q + " == 'attention' ? "
        "(x.result == 'FAILED' || x.result == 'INVALID') : true) }")


def logs_of(page):
    """Access Review's audit list, as its Never Reviewed card already passes it."""
    t = json.dumps(page)
    a = t.index('comsAccessReview.countNeverReviewed(')
    inner = json.loads('"' + t[a:t.index(") + ' never reviewed'", a)] + '"')
    rows = 'comsAccessReview.rowsFrom(shellRoles.data ?? [], comsAccessReview.vacantIds(positionFill.data ?? []))'
    assert inner.startswith('comsAccessReview.countNeverReviewed(' + rows + ', ')
    return inner[len('comsAccessReview.countNeverReviewed(' + rows + ', '):]


def body(rows):
    assert rows.startswith('<% ') and rows.endswith(' %>'), rows[:60]
    return rows[3:-3]


# How each page's list follows the filter (grid id -> new rows), from the rows as built.
def grids(name, page):
    if name == 'accessReview':
        return {'accessReviewGrid': lambda r: f"<% comsAccessReview.quick({body(r)}, {logs_of(page)}, {Q}) %>"}
    if name in ('adminProvisioningView', 'assignableRoleManagerView'):
        gid = 'aaaRolesGrid' if name == 'adminProvisioningView' else 'assignableRolesGrid'
        return {gid: lambda r: f"<% comsRequestStats.quick({body(r)}, {Q}) %>"}
    if name == 'bulkRoleResults':
        return {'rowResultsGrid': lambda r: f"<% ({body(r)}).filter({RESQ}) %>"}
    if name == 'shellOrgManager':
        f = lambda r: f"<% {Q} == 'patterns' ? {PAT} : ({body(r)}).filter({ORGQ}) %>"
        return {'allShellOrgsGrid': f, 'filteredShellOrgsGrid': f}
    return {}


def card_id(task):
    return 'Quick' + task[0].upper() + task[1:] + 'Card'


def card_file(task):
    keys = TARGETS[task]
    return {
        "id": card_id(task),
        "parameters": ["title", "subtitle", "countText", "mark"] + ['b_' + k for k in keys],
        "header": {"title": "<% title ?? \"\" %>", "subtitle": "<% subtitle ?? \"\" %>", "icon": "wd-accent-sigma"},
        "body": {"type": "pillCard", "pills": [{
            "label": "<% mark == \"y\" ? (\"✓ \" + (countText ?? \"\")) : (countText ?? \"\") %>",
            "taskReference": {"taskId": task, "parameterBindings": {k: f"<% b_{k} ?? \"\" %>" for k in keys}}}]},
    }


shutil.rmtree(SRC, ignore_errors=True)
os.makedirs(SRC)
used, done = set(), []
for name, cards in CARDS.items():
    p = os.path.join(ROOT, name + '.pmd')
    page = json.load(open(p, encoding='utf-8'))
    shutil.copyfile(p, os.path.join(SRC, name + '.pmd'))
    left = dict(cards)

    def walk(n):
        if isinstance(n, dict):
            if n.get('type') == 'card' and n.get('cardId') == 'CountCard':
                title = next((t for t in left if f"'title': '{t}'" in n['parameters']), None)
                assert title, f'{name}: a count card this step has no rule for: {n["parameters"][:80]}'
                task, b = left.pop(title)
                extra = [f"'mark': ({b['mark']}) ? 'y' : ''" if 'mark' in b else "'mark': ''"]
                extra += [f"'b_{k}': ({b.get(k, chr(39) * 2)})" for k in TARGETS[task]]
                assert n['parameters'].count("{ 'title':") == 1, n['parameters'][:80]
                n['parameters'] = n['parameters'].replace("{ 'title':", "{ " + ', '.join(extra) + ", 'title':")
                n['cardId'] = card_id(task)
                used.add(task)
            if n.get('type') == 'grid':
                g = grids(name, page).get(n.get('id'))
                if g:
                    n['rows'] = g(n['rows'])
            for v in n.values():
                walk(v)
        elif isinstance(n, list):
            for v in n:
                walk(v)
    walk(page)
    assert not left, f'{name}: count cards not found: {list(left)}'
    open(p, 'w', encoding='utf-8').write(json.dumps(page, indent=2, ensure_ascii=False) + '\n')
    done.append(name)

for task in sorted(used):
    open(os.path.join(ROOT, 'cards', card_id(task) + '.card'), 'w', encoding='utf-8').write(
        json.dumps(card_file(task), indent=2, ensure_ascii=False) + '\n')

# CountCard has no users left
left_users = [p for p in glob.glob(os.path.join(ROOT, '*.pmd')) if '"CountCard"' in open(p, encoding='utf-8').read()]
cc = os.path.join(ROOT, 'cards', 'CountCard.card')
if not left_users and os.path.exists(cc):
    os.remove(cc)
print(f'quick_filters: {len(done)} pages, {len(used)} pill cards; CountCard ' + ('kept: ' + ', '.join(left_users) if left_users else 'removed'))
