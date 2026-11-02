#!/usr/bin/env python3
import subprocess, sys
"""Replaces stacked filter buttons with pill cards (pillCard: buttons that wrap side by side; the current
choice is marked with a check). Audit Log Viewer: time period + change type. Re-run: python3 tools/build_filter_pills.py"""
import json, os
ROOT = os.path.join(os.path.dirname(__file__), '..', 'presentation')
def save(n, d): open(os.path.join(ROOT, n), 'w').write(json.dumps(d, indent=2, ensure_ascii=False) + '\n')
load = lambda n: json.load(open(os.path.join(ROOT, n)))
# card files may only use double-quoted literals inside <% %>
def pill(label, cond, task, bindings):
    return {"label": '<% (' + cond + ') ? "✓ ' + label + '" : "' + label + '" %>', "taskReference": {"taskId": task, "parameterBindings": bindings}}

PERIODS = [("All time", "all"), ("Last 24 hours", "24h"), ("Last 7 days", "7d"), ("Last 30 days", "30d")]
period_card = {"id": "AuditPeriodPillCard", "parameters": ["period", "changeType"],
  "header": {"title": "Time Period", "icon": "wd-accent-clipboard-checklist"},
  "body": {"type": "pillCard", "pills": [
    pill(lbl, ('empty(period) || period == "all"' if key == "all" else 'period == "' + key + '"'), "auditLogViewer",
         {"period": key, "changeType": '<% changeType ?? "" %>'}) for lbl, key in PERIODS]}}
TYPES = [("All types", ""), ("Shell Org", "Shell Org"), ("Pattern", "Shell Org Pattern"), ("Org Status", "Org Status"),
         ("Role Assignment", "Role Assignment"), ("Assignable Role", "Assignable Role")]
type_card = {"id": "AuditTypePillCard", "parameters": ["period", "changeType"],
  "header": {"title": "Change Type", "icon": "wd-accent-clipboard-checklist"},
  "body": {"type": "pillCard", "pills": [
    pill(lbl, ('empty(changeType)' if key == "" else 'changeType == "' + key + '"'), "auditLogViewer",
         {"period": '<% period ?? "" %>', "changeType": key}) for lbl, key in TYPES]}}
for c in (period_card, type_card):
    open(os.path.join(ROOT, 'cards', c['id'] + '.card'), 'w').write(json.dumps(c, indent=2, ensure_ascii=False) + '\n')

page = load('auditLogViewer.pmd')
secs = page['presentation']['body']['sections']
i = [s.get('id') for s in secs].index('auditFilterSection')
P = "<% { 'period': queryParams.period ?? '', 'changeType': queryParams.changeType ?? '' } %>"
# the 'Showing N of M' line sits with the filters, as on ISC Role Requests
showing = None
def take(o):
    global showing
    if isinstance(o, dict):
        kids = o.get('children')
        if isinstance(kids, list):
            for k in list(kids):
                if isinstance(k, dict) and k.get('id') == 'auditCountText': showing = k; kids.remove(k)
        for v in o.values(): take(v)
    elif isinstance(o, list):
        for v in o: take(v)
take(secs)
show_kids = [showing] if showing else []
# keep the Changes by Action chart that tools/polish.py moved in beside the filters
chart = []
def keep_chart(o):
    if isinstance(o, dict):
        if o.get('type') == 'card' and o.get('cardId') == 'AuditActionChart': chart.append(o)
        for v in o.values(): keep_chart(v)
    elif isinstance(o, list):
        for v in o: keep_chart(v)
keep_chart(secs[i])
secs[i] = {"type": "layoutSection", "id": "auditFilterSection", "children": [
    {"type": "fieldSet", "id": "auditShowFieldSet", "title": "Show", "children": show_kids},
    {"type": "cardContainer", "id": "auditFilterCardContainer", "layout": "masonry" if chart else "grid", "cards": [
    {"type": "card", "cardId": "AuditPeriodPillCard", "parameters": P},
    {"type": "card", "cardId": "AuditTypePillCard", "parameters": P}] + chart}]}
save('auditLogViewer.pmd', page)
print('ok')

# ── ISC Role Requests: request type + status pills; the landing page's queue links as one pill card ──
VIEWS = [("All requests", ""), ("AAA roles", "aaa"), ("Assignable roles", "assignable")]
STATUSES = [("Pending", "Pending ISC Review"), ("Approved", "Approved"), ("Denied", "Denied"), ("All", "All")]
isc_view_card = {"id": "IscViewPillCard", "parameters": ["view", "status"],
  "header": {"title": "Request Type", "icon": "wd-accent-clipboard-checklist"},
  "body": {"type": "pillCard", "pills": [
    pill(lbl, ('empty(view)' if key == "" else 'view == "' + key + '"'), "iscRoleRequestsView",
         {"view": key, "status": '<% status ?? "" %>'}) for lbl, key in VIEWS]}}
isc_status_card = {"id": "IscStatusPillCard", "parameters": ["view", "status"],
  "header": {"title": "Status", "icon": "wd-accent-clipboard-checklist"},
  "body": {"type": "pillCard", "pills": [
    pill(lbl, ('empty(status) || status == "Pending ISC Review"' if key == "Pending ISC Review" else 'status == "' + key + '"'), "iscRoleRequestsView",
         {"view": '<% view ?? "" %>', "status": key}) for lbl, key in STATUSES]}}
for c in (isc_view_card, isc_status_card):
    open(os.path.join(ROOT, 'cards', c['id'] + '.card'), 'w').write(json.dumps(c, indent=2, ensure_ascii=False) + '\n')

isc = load('iscRoleRequestsView.pmd')
secs = isc['presentation']['body']['sections']
i = [s.get('id') for s in secs].index('statusFilterSection')
fs = secs[i]['children'][0]
fs['children'] = [c for c in fs['children'] if c.get('type') != 'button']   # keep the 'Showing' text
fs['title'] = 'Show'
IP = "<% { 'view': queryParams.view ?? '', 'status': queryParams.status ?? '' } %>"
secs[i]['children'] = [fs, {"type": "cardContainer", "id": "iscFilterCardContainer", "layout": "grid", "cards": [
    {"type": "card", "cardId": "IscViewPillCard", "parameters": IP},
    {"type": "card", "cardId": "IscStatusPillCard", "parameters": IP}]}]
save('iscRoleRequestsView.pmd', isc)

# The ISC landing page (iscRoleRequestsHub) was retired 2026-10-31; links open iscRoleRequestsView directly.
print('isc ok')

# ── Home: the four stacked-button sections become one row of action cards (main action first) ──
ACTIONS = [
  ("HomeShellOrgActionsCard", "Shell Organizations", "Add orgs and patterns, manage status.", "wd-accent-worksheets",
   [("Open Shell Org Manager", "shellOrgManager"), ("Add Shell Org", "createShellOrgWizard"), ("Add Pattern (Clockwork)", "createShellOrgPatternWizard")]),
  ("HomeBulkActionsCard", "Bulk Role Changes", "Add or remove positions in bulk.", "wd-accent-checkmarked-page",
   [("Edit in the App", "bulkRoleGrid"), ("Upload File", "bulkRoleChanges"), ("Download Template", "bulkRoleTemplate"), ("View Results", "bulkRoleResults")]),
  ("HomeRoleRequestActionsCard", "Role Requests", "Request roles and follow their review.", "wd-accent-clipboard-checklist",
   [("View My Requests", "assignableRoleManagerView"), ("Submit New Request", "assignableRoleManager"),
    ("View AAA Requests", "adminProvisioningView"), ("Submit AAA Role Request", "adminProvisioning")]),
]
for cid, title, sub, icon, pills in ACTIONS:
    card = {"id": cid, "header": {"title": title, "subtitle": sub, "icon": icon},
            "body": {"type": "pillCard", "pills": [{"label": l, "taskReference": {"taskId": t}} for l, t in pills]}}
    open(os.path.join(ROOT, 'cards', cid + '.card'), 'w').write(json.dumps(card, indent=2, ensure_ascii=False) + '\n')
home = load('hubLanding.pmd')
hsecs = home['presentation']['body']['sections']
old_ids = ['shellOrgSection', 'bulkSection', 'assignableRoleSection', 'adminSection']
keep = [s for s in hsecs if s.get('id') not in old_ids + ['actionsSection']]
keep.append({"type": "layoutSection", "id": "actionsSection", "children": [{"type": "cardContainer", "id": "actionsCardContainer", "layout": "grid",
    "cards": [{"type": "card", "cardId": a[0]} for a in ACTIONS]}]})
home['presentation']['body']['sections'] = keep
save('hubLanding.pmd', home)
print('home ok')

# ── Shell Org Manager Summary tab: count cards + quick actions in one row, chart below; counts follow the selected application ──
qa = {"id": "ShellOrgQuickActionsCard", "header": {"title": "Quick Actions", "subtitle": "Create in Workday", "icon": "wd-accent-worksheets"},
      "body": {"type": "pillCard", "pills": [{"label": "Add Shell Org", "taskReference": {"taskId": "createShellOrgWizard"}},
                                             {"label": "Add Pattern (Clockwork)", "taskReference": {"taskId": "createShellOrgPatternWizard"}}]}}
open(os.path.join(ROOT, 'cards', 'ShellOrgQuickActionsCard.card'), 'w').write(json.dumps(qa, indent=2, ensure_ascii=False) + '\n')
PFX = "(empty(queryParams.appCode) ? 'X:' : queryParams.appCode + ':')"
ORGS = "(allShellOrgs.data ?? []).filter(o => { (o.code ?? '').startsWith(" + PFX + ") && !(o.code ?? '').contains(':PATTERN') })"
PATS = "(allShellOrgs.data ?? []).filter(o => { (o.code ?? '').startsWith(empty(queryParams.appCode) ? 'X:' : queryParams.appCode + ':PATTERN') && (o.code ?? '').contains(':PATTERN') })"
ACT = "size(" + ORGS + ".filter(o => { o.cf_active1 == true }))"
INA = "size(" + ORGS + ".filter(o => { o.cf_active1 != true }))"
SCOPE = "(empty(queryParams.appCode) ? 'All applications' : queryParams.appCode)"
som = load('shellOrgManager.pmd')
tab = som['presentation']['body']['tabs'][0] if 'tabs' in som['presentation']['body'] else None
def find_tab(o):
    if isinstance(o, dict):
        if isinstance(o.get('children'), list) and any(isinstance(c, dict) and c.get('id') in ('summaryStatsFieldSet', 'summaryCardContainer') for c in o['children']):
            return o
        for v in o.values():
            r = find_tab(v)
            if r: return r
    elif isinstance(o, list):
        for v in o:
            r = find_tab(v)
            if r: return r
tab = find_tab(som['presentation'])
tab['children'] = [
  {"type": "cardContainer", "id": "summaryCardContainer", "layout": "masonry", "cards": [
    {"type": "card", "cardId": "CountCard", "parameters": "<% { 'title': 'Active', 'subtitle': " + SCOPE + ", 'countText': '' + " + ACT + " + (" + ACT + " == 1 ? ' shell organization' : ' shell organizations') } %>"},
    {"type": "card", "cardId": "CountCard", "parameters": "<% { 'title': 'Inactive', 'subtitle': " + SCOPE + ", 'countText': '' + " + INA + " + (" + INA + " == 1 ? ' shell organization' : ' shell organizations') } %>"},
    {"type": "card", "cardId": "CountCard", "parameters": "<% { 'title': 'Patterns', 'subtitle': " + SCOPE + ", 'countText': '' + size(" + PATS + ") + (size(" + PATS + ") == 1 ? ' pattern' : ' patterns') } %>"},
    {"type": "card", "cardId": "ShellOrgQuickActionsCard"},
    {"type": "card", "cardId": "ShellOrgStatusChart", "parameters": "<% { 'activeCount': " + ACT + ", 'inactiveCount': " + INA + " } %>"}]}]
save('shellOrgManager.pmd', som)
print('summary ok')

som = load('shellOrgManager.pmd')
som['presentation']['title']['label'] = "<% empty(queryParams.appName) ? 'ECO-COMS: Shell Org Manager' : ('ECO-COMS: Shell Org Manager – ' + queryParams.appName) %>"
save('shellOrgManager.pmd', som)

# ── Error page: links as two pill cards; 'Other pages' only for a 404 (as before) ──
for cid, title, pills in [("ErrorStartAgainCard", "Start Again", [("Home", "home"), ("Shell Org Manager", "shellOrgManager")]),
                          ("ErrorOtherPagesCard", "Other Pages", [("My Assignable Role Requests", "assignableRoleManagerView"), ("AAA Role Requests", "adminProvisioningView"),
                                                                  ("ISC Queue", "iscRoleRequestsView"), ("Audit Log", "auditLogViewer")])]:
    open(os.path.join(ROOT, 'cards', cid + '.card'), 'w').write(json.dumps({"id": cid, "header": {"title": title, "icon": "wd-accent-home"},
        "body": {"type": "pillCard", "pills": [{"label": l, "taskReference": {"taskId": t}} for l, t in pills]}}, indent=2, ensure_ascii=False) + '\n')
err = load('errorPage.pmd')
esecs = err['presentation']['body']['sections']
k = [s.get('id') for s in esecs].index('navSection')
esecs[k] = {"type": "layoutSection", "id": "navSection", "children": [{"type": "cardContainer", "id": "errorLinksCardContainer", "layout": "grid", "cards": [
    {"type": "card", "cardId": "ErrorStartAgainCard"},
    {"type": "card", "cardId": "ErrorOtherPagesCard", "render": "<% queryParams.errorCode == '404' %>"}]}]}
save('errorPage.pmd', err)
print('error ok')

# final UI polish pass (grid labels, About ⓘ, ...); see tools/polish.py
subprocess.run([sys.executable, os.path.join(os.path.dirname(__file__), 'polish.py')], check=True)
