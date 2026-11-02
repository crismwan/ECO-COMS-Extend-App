#!/usr/bin/env python3
"""UI improvements from "ECO-COMS UI Recommendations" (update of 2026-11-02, product owner: "continue with
recommendations"). Idempotent. Two steps in rebuild_all.sh:

  tools/ux_improvements.py           before grid_style.py (new columns get the standard grid format)
    1. always-visible helpText on fields whose help was only in a guide (guides show only in guided tours)
    2. ISC Queue: Waiting column (business days pending) and oldest first in the Pending view
    3. empty states with an action button (My Assignable Role Requests, AAA Role Requests)
    5. Bulk Edit: live change counter (readOnlyText + setValue; setValue is ignored on text widgets)
    6. receipt cards: View in Audit Log (filtered to the last 24 hours and the change type)
    7. Audit Log: Last 90 days period and an Application column (the grid's own column filter filters by it)
  tools/ux_improvements.py --tiles   after title_banner.py
    4. one-line summary under the title tile on pages whose About box starts closed (collapse_about.py)
Recommendation 8 (ISC turnaround) is on the Insights page (build_insights.py).
"""
import json, os, re, sys
R = os.path.join(os.path.dirname(__file__), '..', 'presentation')


def load(rel):
    return json.load(open(os.path.join(R, rel)))


def save(rel, d):
    open(os.path.join(R, rel), 'w').write(json.dumps(d, indent=2, ensure_ascii=False) + '\n')


def walk(n, f):
    if isinstance(n, dict):
        f(n)
        for v in list(n.values()): walk(v, f)
    elif isinstance(n, list):
        for v in list(n): walk(v, f)


def find(d, wid):
    hit = []
    walk(d, lambda n: hit.append(n) if n.get('id') == wid else None)
    return hit[0] if hit else None


done = []

# ---- 4. one-line summaries in the title tile (last step) ----
SUMMARY = {
    'iscRoleRequestsView': 'Role requests waiting for ISC review. Open a row\'s Review Process link to approve or deny it.',
    'auditLogViewer': 'Every change ECO-COMS made in Workday. Filter by time period and change type.',
    'shellOrgManager': 'Shell organizations, patterns and role assignments for one application.',
    'bulkRoleChanges': 'Upload a file of role changes, validate it, then apply it.',
    'bulkRoleTemplate': 'Download the current template for bulk role changes.',
    'newSchemaPattern': 'Add a shell org pattern in the format the application uses.',
}
SUB = '<br><span style="color:#374151;font-size:13px">{}</span>'
if '--tiles' in sys.argv:
    for page, text in SUMMARY.items():
        d = load(page + '.pmd')
        t = find(d, 'titleBannerRichText')
        if not t: continue
        v = t['value']
        if v.startswith('<%'):
            continue   # scripted titles (e.g. ISC Queue follows the filter): summary added inside the script below
        v = re.sub(r'<br><span style="color:#374151;font-size:13px">.*?</span>$', '', v)
        t['value'] = v + SUB.format(text.replace("'", '&#39;'))
        save(page + '.pmd', d)
        done.append(page)
    # scripted tiles: append the summary as a literal at the end of the expression
    for page, text in SUMMARY.items():
        d = load(page + '.pmd')
        t = find(d, 'titleBannerRichText')
        if not t or not t['value'].startswith('<%'): continue
        expr = t['value'][2:-2].strip()
        expr = re.sub(r" \+ '<br><span style=\"color:#374151;font-size:13px\">.*?</span>'$", '', expr)
        t['value'] = "<% " + expr + " + '" + SUB.format(text.replace("'", '&#39;')).replace("'", "\\'") + "' %>"
        save(page + '.pmd', d)
        done.append(page + ' (scripted)')
    print('title tile summaries:', ', '.join(done))
    sys.exit(0)

# ---- 1. visible help text ----
HELP = {
    ('assignableRoleManager.pmd', 'applicationDropdown'): 'The generated role name starts with this application code.',
    ('bulkRoleChanges.pmd', 'effectiveDate'): 'A weekday this year or next. One date applies to every row.',
    ('bulkRoleChanges.pmd', 'realRunCheckBox'): 'Leave unticked to validate only: nothing changes in Workday.',
    ('newShellOrg.pmd', 'effectiveDate'): 'A weekday (Monday to Friday) this year or next.',
}
for (page, wid), text in HELP.items():
    d = load(page)
    w = find(d, wid)
    if w is not None and not w.get('helpText'):
        w['helpText'] = text
        save(page, d)
        done.append(f'help {page[:-4]}.{wid}')

# ---- 2. ISC Queue: Waiting column, oldest first when showing Pending ----
d = load('iscRoleRequestsView.pmd')
g = find(d, 'allPendingGrid')
if g and 'oldest first' not in g.get('rows', ''):
    inner = g['rows'].strip()[2:-2].strip()
    g['rows'] = ("<% let f = " + inner + "; /* oldest first */ comsRequestStats.statusOrDefault(queryParams.status ?? '') == 'Pending ISC Review' "
                 "? list:flatten([list:sort(f.filter(r => { !empty(r.requestedDate) }), 'requestedDate', true), f.filter(r => { empty(r.requestedDate) })]) : f %>")
    done.append('ISC oldest first')
if g and not any(c.get('columnId') == 'colWaiting' for c in g['columns']):
    i = next(k for k, c in enumerate(g['columns']) if c.get('columnId') == 'colRequestedDate') + 1
    var = g.get('rowVariableName', 'row')
    g['columns'].insert(i, {"type": "column", "columnId": "colWaiting", "label": "Waiting", "cellTemplate": {
        "type": "text", "id": "waitingText", "enabled": False, "value": f"<% comsRequestStats.waitingText({var}) %>"}})
    done.append('ISC Waiting column')
save('iscRoleRequestsView.pmd', d)

# ---- 3. empty states with an action ----
for page, task, label in [('assignableRoleManagerView.pmd', 'assignableRoleManager', 'Submit a Request'),
                          ('adminProvisioningView.pmd', 'adminProvisioning', 'Submit AAA Role Request')]:
    d = load(page)
    holder = []
    walk(d, lambda n: holder.append(n) if any(isinstance(c, dict) and c.get('id') == 'emptyStateMsg' for c in n.get('children', [])) else None)
    if holder:
        kids = holder[0]['children']
        msg = next(c for c in kids if c.get('id') == 'emptyStateMsg')
        btn = {"type": "button", "id": "emptyActionButton", "action": "PRIMARY", "label": label,
               "visible": msg.get('visible', 'true'), "taskReference": {"taskId": task}}
        kids[:] = [c for c in kids if c.get('id') != 'emptyActionButton']
        kids.insert(kids.index(msg) + 1, btn)
        save(page, d)
        done.append(f'empty action {page[:-4]}')

# ---- 5. Bulk Edit change counter ----
d = load('bulkRoleGrid.pmd')
COUNT = ("let removals = currentGrid.rows.filter(r => { r.childrenMap.colRemove.value == true }).size(); "
         "let additions = addGrid.rows.filter(r => { !empty(r.childrenMap.colPositionAdd.value) }).size(); "
         "changesReadOnlyText.setValue((removals + additions == 0) ? 'No changes yet. Up to 50 per submit.' : "
         "('' + removals + ' removal' + (removals == 1 ? '' : 's') + ' and ' + additions + ' addition' + (additions == 1 ? '' : 's') + ' ready'"
         " + ((removals + additions) > 50 ? ': over the limit of 50 per submit' : ' (up to 50 per submit)')));")
holder = []
walk(d, lambda n: holder.append(n) if any(isinstance(c, dict) and c.get('id') in ('changesText', 'changesReadOnlyText') for c in n.get('children', [])) else None)
if holder:
    kids = holder[0]['children']
    for k, c in enumerate(kids):
        if c.get('id') in ('changesText', 'changesReadOnlyText'):
            kids[k] = {"type": "readOnlyText", "id": "changesReadOnlyText", "label": "Changes", "value": "No changes yet. Up to 50 per submit."}
    MARK = '/* change counter */'


    def hook(widget, key):
        old = (widget.get(key) or '').strip()
        body = old[2:-2].strip() if old.startswith('<%') else ''
        body = body.split(MARK)[0].rstrip()
        if body and not body.endswith(';'): body += ';'
        widget[key] = '<% ' + (body + ' ' if body else '') + MARK + ' ' + COUNT + ' %>'

    hook(find(d, 'removeCheckBox'), 'onChange')
    hook(find(d, 'positionAddList'), 'onChange')
    hook(find(d, 'addGrid'), 'onRowRemove')
    save('bulkRoleGrid.pmd', d)
    done.append('bulk change counter')

# ---- 6. receipts: View in Audit Log ----
for card, ctype in [('ShellOrgReceiptCard', 'Shell Org'), ('ShellOrgPatternReceiptCard', 'Shell Org Pattern'), ('ShellOrgStatusReceiptCard', 'Org Status')]:
    rel = f'cards/{card}.card'
    d = load(rel)
    foot = d.setdefault('footer', [])
    if not any(f.get('label') == 'View in Audit Log' for f in foot) and len(foot) < 5:
        foot.append({"label": "View in Audit Log", "taskReference": {"taskId": "auditLogViewer", "parameterBindings": {"period": "24h", "changeType": ctype}}})
        save(rel, d)
        done.append(f'audit link {card}')

# ---- 7. Audit Log: Last 90 days + Application column ----
rel = 'cards/AuditPeriodPillCard.card'
d = load(rel)
pills = d['body']['pills']
if not any('90d' in json.dumps(p) for p in pills):
    i = next(k for k, p in enumerate(pills) if '"30d"' in json.dumps(p)) + 1
    pills.insert(i, {"label": "<% (period == \"90d\") ? \"✓ Last 90 days\" : \"Last 90 days\" %>",
                     "taskReference": {"taskId": "auditLogViewer", "parameterBindings": {"period": "90d", "changeType": "<% changeType ?? \"\" %>"}}})
    save(rel, d)
    done.append('audit 90d pill')
d = load('auditLogViewer.pmd')
g = find(d, 'AuditLogGrid')
if g and not any(c.get('columnId') == 'columnApplication' for c in g['columns']):
    i = next(k for k, c in enumerate(g['columns']) if c.get('columnId') == 'columnAction') + 1
    g['columns'].insert(i, {"type": "column", "columnId": "columnApplication", "label": "Application", "cellTemplate": {
        "type": "text", "id": "applicationText", "enabled": False,
        "value": "<% let n = (logEntry.coName ?? '').startsWith('X:') ? logEntry.coName : (logEntry.roleName ?? ''); "
                 "n.startsWith('X:') ? (n.substringBefore(':') + ':' + n.substringAfter(':').substringBefore(':')) : '' %>"}})
    save('auditLogViewer.pmd', d)
    done.append('audit Application column')

print('ux improvements:', ', '.join(done) or 'none (already applied)')
