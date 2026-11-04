#!/usr/bin/env python3
"""App Activity chart on the RBAC Hub: changes per day for the last 7 days, stacked by area
(shell orgs, role assignments, role requests), from the audit log the hub already loads.
Replaces the Shell Org Overview donut there (that donut stays on Shell Org Manager and Insights).
Chart type: stackedBarChart2 (developer.workday.com "chartCard", example uses stackedBarChart2)."""
import json, os

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
P = lambda *a: os.path.join(ROOT, *a)


def save(p, d):
    open(p, 'w', encoding='utf-8').write(json.dumps(d, indent=2, ensure_ascii=False) + '\n')


save(P('presentation', 'cards', 'AppActivityChart.card'), {
    "id": "AppActivityChart",
    "parameters": ["days", "totalText"],
    "header": {"title": "App Activity", "subtitle": "<% totalText ?? \"\" %>", "icon": "wd-accent-time"},
    "body": {"type": "chartCard", "chart": {
        "type": "stackedBarChart2",
        "id": "appActivityStackedBarChart",
        "data": "<% days ?? [] %>",
        "dataVariableName": "day",
        "categoryDataSet": {"name": "Day", "value": "<% day.day %>"},
        "measurementDataSets": [
            {"name": "Shell orgs", "value": "<% day.shellOrgs %>"},
            {"name": "Role assignments", "value": "<% day.assignments %>"},
            {"name": "Role requests", "value": "<% day.requests %>"}],
        "measurementAxisOptions": {"axisTitle": "Changes"}}}})  # no footer: the Audit Log card beside it already links there (product owner 2026-11-04)

lp = P('presentation', 'hubLanding.pmd')
landing = json.load(open(lp, encoding='utf-8'))
LOGS = "auditPage0.data ?? []"
card = {"type": "card", "cardId": "AppActivityChart",
        "parameters": "<% { 'days': comsAuditFilters.activityByDay(" + LOGS + "), "
                      "'totalText': '' + size(comsAuditFilters.filterLogs(" + LOGS + ", '7d', '')) + ' changes in the last 7 days' } %>"}
for sec in landing['presentation']['body']['sections']:
    for c in sec.get('children', []):
        if c.get('id') == 'dashboardCardContainer':
            c['cards'] = [card if x.get('cardId') in ('ShellOrgStatusChart', 'AppActivityChart') else x for x in c['cards']]
save(lp, landing)
print("AppActivityChart on the RBAC Hub")
