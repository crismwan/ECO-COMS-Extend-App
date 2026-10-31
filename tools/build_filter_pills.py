#!/usr/bin/env python3
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
  "header": {"title": "Time period", "icon": "wd-accent-clipboard-checklist"},
  "body": {"type": "pillCard", "pills": [
    pill(lbl, ('empty(period) || period == "all"' if key == "all" else 'period == "' + key + '"'), "auditLogViewer",
         {"period": key, "changeType": '<% changeType ?? "" %>'}) for lbl, key in PERIODS]}}
TYPES = [("All types", ""), ("Shell Org", "Shell Org"), ("Pattern", "Shell Org Pattern"), ("Org Status", "Org Status"),
         ("Role Assignment", "Role Assignment"), ("Assignable Role", "Assignable Role")]
type_card = {"id": "AuditTypePillCard", "parameters": ["period", "changeType"],
  "header": {"title": "Change type", "icon": "wd-accent-clipboard-checklist"},
  "body": {"type": "pillCard", "pills": [
    pill(lbl, ('empty(changeType)' if key == "" else 'changeType == "' + key + '"'), "auditLogViewer",
         {"period": '<% period ?? "" %>', "changeType": key}) for lbl, key in TYPES]}}
for c in (period_card, type_card):
    open(os.path.join(ROOT, 'cards', c['id'] + '.card'), 'w').write(json.dumps(c, indent=2, ensure_ascii=False) + '\n')

page = load('auditLogViewer.pmd')
secs = page['presentation']['body']['sections']
i = [s.get('id') for s in secs].index('auditFilterSection')
P = "<% { 'period': queryParams.period ?? '', 'changeType': queryParams.changeType ?? '' } %>"
secs[i] = {"type": "layoutSection", "id": "auditFilterSection", "children": [{"type": "cardContainer", "id": "auditFilterCardContainer", "layout": "grid", "cards": [
    {"type": "card", "cardId": "AuditPeriodPillCard", "parameters": P},
    {"type": "card", "cardId": "AuditTypePillCard", "parameters": P}]}]}
save('auditLogViewer.pmd', page)
print('ok')

# ── ISC Role Requests: request type + status pills; the landing page's queue links as one pill card ──
VIEWS = [("All requests", ""), ("AAA provisioning", "aaa"), ("Assignable roles", "assignable")]
STATUSES = [("Pending", "Pending ISC Review"), ("Approved", "Approved"), ("Denied", "Denied"), ("All", "All")]
isc_view_card = {"id": "IscViewPillCard", "parameters": ["view", "status"],
  "header": {"title": "Request type", "icon": "wd-accent-clipboard-checklist"},
  "body": {"type": "pillCard", "pills": [
    pill(lbl, ('empty(view)' if key == "" else 'view == "' + key + '"'), "iscRoleRequestsView",
         {"view": key, "status": '<% status ?? "" %>'}) for lbl, key in VIEWS]}}
isc_status_card = {"id": "IscStatusPillCard", "parameters": ["view", "status"],
  "header": {"title": "Status", "icon": "wd-accent-clipboard-checklist"},
  "body": {"type": "pillCard", "pills": [
    pill(lbl, ('empty(status) || status == "Pending ISC Review"' if key == "Pending ISC Review" else 'status == "' + key + '"'), "iscRoleRequestsView",
         {"view": '<% view ?? "" %>', "status": key}) for lbl, key in STATUSES]}}
isc_queue_card = {"id": "IscQueuePillCard",
  "header": {"title": "Open the queue", "subtitle": "Pending requests waiting for ISC review", "icon": "wd-accent-clipboard-checklist"},
  "body": {"type": "pillCard", "pills": [
    {"label": lbl, "taskReference": {"taskId": "iscRoleRequestsView", "parameterBindings": {"view": key}}} for lbl, key in
    [("All pending requests", ""), ("Pending AAA provisioning", "aaa"), ("Pending assignable roles", "assignable")]]}}
for c in (isc_view_card, isc_status_card, isc_queue_card):
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

hub = load('iscRoleRequestsHub.pmd')
hs = hub['presentation']['body']['sections']
j = [s.get('id') for s in hs].index('iscHubLinksSection')
hs[j] = {"type": "layoutSection", "id": "iscHubLinksSection", "children": [{"type": "cardContainer", "id": "iscQueueCardContainer", "layout": "grid", "cards": [
    {"type": "card", "cardId": "IscQueuePillCard"}]}]}
save('iscRoleRequestsHub.pmd', hub)
print('isc ok')
