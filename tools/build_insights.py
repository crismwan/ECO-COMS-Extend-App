#!/usr/bin/env python3
"""ECO-COMS Insights (product owner 2026-11-02: "a more insightful report based on all business objects").

Model reports cover one business object each, so the cross-object view is a VIEW page in the hub:
  - four count cards: pending requests (overdue), approved in the last 30 days, changes in the last 30 days,
    bulk runs in the last 30 days
  - charts: requests by status, requests by application, shell orgs active vs inactive, changes by action
    (last 30 days), bulk runs by status
  - Applications at a Glance: per application code, shell orgs, patterns and role requests
  - Oldest Pending Requests
Also writes the BreakdownChart card, registers the task and adds the hub link. Idempotent.
Script helpers: presentation/scripts/comsInsights.script.
"""
import json, os
R = os.path.join(os.path.dirname(__file__), '..')
P = lambda *a: os.path.join(R, *a)


def save(p, d):
    open(p, 'w').write(json.dumps(d, indent=2, ensure_ascii=False) + '\n')


FOS = lambda *c: [{"code": x} for x in c]
INFO = '<span style="color:#0055B7;font-size:12px;font-weight:700">ⓘ </span><span style="color:#374151;font-size:12px">{}</span>'

# ---- card: generic donut ----
save(P('presentation', 'cards', 'BreakdownChart.card'), {
    "id": "BreakdownChart",
    "parameters": ["title", "subtitle", "slices"],
    "header": {"title": "<% title ?? \"\" %>", "subtitle": "<% subtitle ?? \"\" %>"},
    "body": {"type": "chartCard", "chart": {
        "type": "donutChart2", "data": "<% slices ?? [] %>", "dataVariableName": "slice",
        "sliceSizeDataSet": {"name": "Count", "value": "<% slice[\"count\"] %>"},
        "sliceColorDataSet": {"name": "Group", "value": "<% slice[\"label\"] %>"},
        "showPercentLabels": False, "animateOnLoad": True}}})

# ---- endpoints ----
eps = [
    {"name": "requestCount", "baseUrlType": "BUSINESS-OBJECT", "url": "/comsAssignableRoles?limit=1", "authType": "sso", "bestEffort": "true", "failOnStatusCodes": FOS(400, 429)},
]
for i in range(3):
    eps.append({"name": f"requestPage{i}", "baseUrlType": "BUSINESS-OBJECT", "authType": "sso", "isCollection": True, "bestEffort": "true", "failOnStatusCodes": FOS(429),
                "url": f"/comsAssignableRoles?limit=100&offset={i * 100}"})
eps += [
    {"name": "allShellOrgs", "baseUrlType": "workday-wql", "url": "data", "authType": "sso", "bestEffort": "true", "wqlQuery": {"queryId": "allShellOrgs"}, "failOnStatusCodes": FOS(400, 429)},
    {"name": "comsApplications", "baseUrlType": "BUSINESS-OBJECT", "url": "/comsApplications?limit=100", "authType": "sso", "isCollection": True, "bestEffort": "true", "failOnStatusCodes": FOS(429)},
    {"name": "auditLogCount", "baseUrlType": "BUSINESS-OBJECT", "url": "/comsAuditLogs?limit=1", "authType": "sso", "bestEffort": "true", "failOnStatusCodes": FOS(400, 429)},
]
for i in range(3):   # newest 300 audit records
    eps.append({"name": f"auditPage{i}", "baseUrlType": "BUSINESS-OBJECT", "authType": "sso", "isCollection": True, "bestEffort": "true", "failOnStatusCodes": FOS(429),
                "url": f"<% let t = auditLogCount.total ?? 0; let start = (t - {(i + 1) * 100}) < 0 ? 0 : (t - {(i + 1) * 100}); let cnt = t - {i * 100} - start; '/comsAuditLogs?limit=' + (cnt > 0 ? cnt : 1) + '&offset=' + (cnt > 0 ? start : t) %>"})
eps += [
    {"name": "bulkRunCount", "baseUrlType": "BUSINESS-OBJECT", "url": "/comsBulkRuns?limit=1", "authType": "sso", "bestEffort": "true", "failOnStatusCodes": FOS(400, 429)},
    {"name": "bulkRunPage0", "baseUrlType": "BUSINESS-OBJECT", "authType": "sso", "isCollection": True, "bestEffort": "true", "failOnStatusCodes": FOS(429),
     "url": "<% let t = bulkRunCount.total ?? 0; let start = (t - 100) < 0 ? 0 : (t - 100); let cnt = t - start; '/comsBulkRuns?limit=' + (cnt > 0 ? cnt : 1) + '&offset=' + (cnt > 0 ? start : t) %>"},
]

REQ = "list:flatten([requestPage0.data ?? [], requestPage1.data ?? [], requestPage2.data ?? []])"
AUD = "list:flatten([auditPage0.data ?? [], auditPage1.data ?? [], auditPage2.data ?? []])"
RUNS = "(bulkRunPage0.data ?? [])"
ORGS = "(allShellOrgs.data ?? [])"


def count_card(title, text, subtitle):
    return {"type": "card", "cardId": "CountCard", "parameters": f"<% {{ 'title': '{title}', 'countText': {text}, 'subtitle': '{subtitle}' }} %>"}


def chart(title, slices, subtitle):
    return {"type": "card", "cardId": "BreakdownChart", "parameters": f"<% {{ 'title': '{title}', 'subtitle': {subtitle}, 'slices': {slices} }} %>"}


kpis = [
    count_card("ISC Turnaround", f"comsInsights.turnaroundText({REQ})", "Request to approval, last 90 days"),
    count_card("Pending ISC Review", f"'' + comsRequestStats.countPending({REQ}) + ' pending · ' + comsRequestStats.countOverdue({REQ}) + ' overdue'", "Overdue after 3 business days"),
    count_card("Approved, Last 30 Days", f"'' + {REQ}.filter(r => {{ r.status == 'Approved' && comsInsights.inDays(r.approvedDate, comsInsights.lastDays(30)) }}).size() + ' role requests'", "By approval date"),
    count_card("Changes, Last 30 Days", f"'' + comsInsights.countInDays({AUD}, 'timestamp', comsInsights.lastDays(30)) + ' audit records'", "Newest 300 audit records"),
    None,   # set below (needs a let)
]
kpis[4] = {"type": "card", "cardId": "CountCard", "parameters": (f"<% let runs = {RUNS}.filter(r => {{ comsInsights.inDays(r.uploadedAt, comsInsights.lastDays(30)) }}); "
                         f"{{ 'title': 'Bulk Runs, Last 30 Days', 'countText': '' + size(runs) + ' runs · ' + runs.filter(r => {{ ('' + (r.status ?? '')).upperCase().contains('FAIL') }}).size() + ' failed', 'subtitle': 'Uploads and grid edits' }} %>")}

charts = [
    chart("Role Requests by Status", f"comsInsights.statusSlices({REQ})", f"'' + size({REQ}) + ' requests'"),
    chart("Role Requests by Application", f"comsInsights.appSlices({REQ})", "'Top applications'"),
    {"type": "card", "cardId": "ShellOrgStatusChart", "parameters": "<% { 'activeCount': size((allShellOrgs.data ?? []).filter(o => { (o.code ?? '').startsWith('X:') && !(o.code ?? '').contains(':PATTERN') && o.cf_active1 == true })), 'inactiveCount': size((allShellOrgs.data ?? []).filter(o => { (o.code ?? '').startsWith('X:') && !(o.code ?? '').contains(':PATTERN') && o.cf_active1 != true })) } %>"},
    {"type": "card", "cardId": "AuditActionChart", "parameters": f"<% let f = comsAuditFilters.filterLogs({AUD}, '30d', ''); {{ 'addCount': comsAuditFilters.countAction(f, 'ADD'), 'inactivateCount': comsAuditFilters.countAction(f, 'INACTIVATE'), 'reactivateCount': comsAuditFilters.countAction(f, 'REACTIVATE'), 'assignCount': comsAuditFilters.countAction(f, 'ASSIGN POSITION'), 'removeCount': comsAuditFilters.countAction(f, 'REMOVE POSITION'), 'requestCount': comsAuditFilters.countAction(f, 'REQUEST'), 'approveCount': comsAuditFilters.countAction(f, 'APPROVE'), 'denyCount': comsAuditFilters.countAction(f, 'DENY'), 'deleteCount': comsAuditFilters.countAction(f, 'DELETE'), 'totalText': '' + size(f) + ' records, last 30 days' }} %>"},
    chart("Bulk Runs by Status", f"comsInsights.bulkSlices({RUNS})", f"'' + size({RUNS}) + ' runs'"),
]


def text_col(cid, label, value, kind="text"):
    return {"type": "column", "columnId": cid, "label": label, "cellTemplate": {"type": kind, "id": cid.replace("Column", kind.capitalize()), "value": value, "enabled": False}}


apps_grid = {
    "type": "grid", "id": "appInsightsGrid", "label": "Applications at a Glance", "readOnly": True,
    "rows": f"<% comsInsights.appRows({REQ}, {ORGS}, comsApplications.data ?? []) %>", "rowVariableName": "appRow",
    "columns": [
        {"type": "column", "columnId": "appCodeColumn", "label": "Application ID", "cellTemplate": {
            "type": "button", "id": "appCodeButton", "action": "LINK", "label": "<% appRow.code %>",
            "taskReference": {"taskId": "shellOrgManager", "parameterBindings": {"appCode": "<% appRow.code %>", "appName": "<% appRow.name %>"}}}},
        text_col("appNameColumn", "Name", "<% appRow.name %>"),
        text_col("shellActiveColumn", "Active Shell Orgs", "<% appRow.shellActive %>", "number"),
        text_col("shellInactiveColumn", "Inactive Shell Orgs", "<% appRow.shellInactive %>", "number"),
        text_col("patternsColumn", "Patterns", "<% appRow.patterns %>", "number"),
        text_col("pendingColumn", "Pending Requests", "<% appRow.pending %>", "number"),
        text_col("approvedColumn", "Approved", "<% appRow.approved %>", "number"),
        text_col("deniedColumn", "Denied", "<% appRow.denied %>", "number"),
        text_col("lastRequestColumn", "Last Request", "<% appRow.lastRequest %>"),
    ]}

pending_grid = {
    "type": "grid", "id": "oldestPendingGrid", "label": "Oldest Pending Requests", "readOnly": True,
    "rows": f"<% comsInsights.oldestPending({REQ}, 10) %>", "rowVariableName": "pendingRow",
    "columns": [
        text_col("requestedColumn", "Requested", "<% ('' + (pendingRow.requestedDate ?? '')).substring(0, 10) %>"),
        text_col("roleColumn", "Role", "<% pendingRow.roleName ?? '' %>"),
        text_col("applicationColumn", "Application", "<% comsInsights.appCodeOf(pendingRow.application) %>"),
        text_col("requestedByColumn", "Requested By", "<% !empty(pendingRow.requestedBy) ? (pendingRow.requestedBy.descriptor ?? '') : '' %>"),
        text_col("referenceColumn", "Reference", "<% pendingRow.referenceId ?? '' %>"),
        {"type": "column", "columnId": "openColumn", "label": "Open", "cellTemplate": {
            "type": "button", "id": "openQueueButton", "action": "AUXILIARY", "label": "ISC Queue", "taskReference": {"taskId": "iscRoleRequestsView"}}},
    ]}

page = {
    "id": "comsInsights",
    "securityDomains": ["ManageCOMSShellOrgs"],
    "include": ["comsRequestStats.script", "comsAuditFilters.script", "comsInsights.script"],
    "endPoints": eps,
    "presentation": {
        "title": {"type": "title", "label": "ECO-COMS: Insights"},
        "pageType": "VIEW",
        "body": {"type": "basicFormLayout", "id": "comsInsightsForm", "sections": [
            {"type": "layoutSection", "id": "navSection", "children": [
                {"type": "button", "label": "← Home", "taskReference": {"taskId": "home"}, "action": "LINK", "suppressDiscardDialog": True}]},
            {"type": "layoutSection", "id": "aboutSection", "children": [
                {"type": "fieldSet", "id": "aboutFieldSet", "title": "About This Page", "children": [
                    {"type": "richText", "id": "aboutDesc", "enabled": False, "value": INFO.format(
                        "One view across ECO-COMS: role requests, shell organizations and patterns, the audit log and bulk runs. "
                        "Counts read up to 300 role requests, the newest 300 audit records and the newest 100 bulk runs. "
                        "Select an <b>Application ID</b> to open it in Shell Org Manager. For Workday custom reports use the "
                        "ECO-COMS report data sources (Role Requests, Audit Trail, Bulk Runs, Applications).")}]}]},
            {"type": "layoutSection", "id": "kpiSection", "children": [{"type": "cardContainer", "id": "kpiCardContainer", "layout": "masonry", "cards": kpis}]},
            {"type": "layoutSection", "id": "chartsSection", "children": [{"type": "cardContainer", "id": "chartsCardContainer", "layout": "masonry", "cards": charts}]},
            {"type": "layoutSection", "id": "appsSection", "children": [apps_grid]},
            {"type": "layoutSection", "id": "pendingSection", "children": [pending_grid]},
        ]},
        "footer": {"type": "footer", "children": [{"type": "pod", "podId": "ecoComsFooter"}]},
    }}
save(P('presentation', 'comsInsights.pmd'), page)

# ---- AMD task + hub link ----
amdp = P('presentation', 'ecocomsphase_xclw_cm_sync2_vmzvxm.amd')
amd = json.load(open(amdp))
if not any(t['id'] == 'comsInsights' for t in amd['tasks']):
    amd['tasks'].append({"id": "comsInsights", "routingPattern": "/comsInsights", "page": {"id": "comsInsights"}})
    save(amdp, amd)
hp = P('presentation', 'home.pmd')
home = json.load(open(hp))
nav = home['presentation']['body']['navigationTasks']
if not any(n.get('task', {}).get('taskId') == 'comsInsights' for n in nav):
    nav.insert(1, {"type": "item", "task": {"taskId": "comsInsights"}, "label": "Insights", "icon": "wd-accent-checkmarked-page"})
    save(hp, home)

# ---- reports: one lean data source per key object ----
for old in ['AcademicUnits', 'AllAssignableRoles', 'AllAuditLogs', 'AllShellOrgs']:
    f = P('model', old + '.report')
    if os.path.exists(f): os.remove(f)


def report(rid, name, label, bo, domains, sort, cols):
    d = {"id": rid, "name": name, "label": label, "businessObject": bo, "defaultSecurityDomains": domains,
         "sortConfigs": [{"id": 1, "order": "a", "field": sort[0], "direction": sort[1]}], "columns": []}
    for i, c in enumerate(cols):
        col = {"id": i + 1, "name": c[1], "order": chr(97 + i)}
        if c[0] is None: col["isSelfReferencing"] = True
        else: col["field"] = c[0]
        d["columns"].append(col)
    save(P('model', name + '.report'), d)


report(10, "COMSRoleRequests", "ECO-COMS Role Requests", "COMSAssignableRole",
       ["ManageCOMSAssignableRoles", "MaintainCOMSAssignableRoles", "ManageCOMSAdminProvisioning"], ("requestedDate", "DESCENDING"),
       [(None, "Role Request"), ("referenceId", "Reference ID"), ("roleName", "Role Name"), ("application", "Application"), ("status", "Status"),
        ("requestedBy", "Requested By"), ("requestedDate", "Requested Date"), ("approvedBy", "Approved By"), ("approvedDate", "Approved Date"),
        ("shellOrgCode", "Shell Org Code"), ("positionNames", "Positions"), ("securityGroupName", "Security Group"), ("effectiveDate", "Effective Date"),
        ("iscTicketReference", "ISC Ticket"), ("denialReason", "Denial Reason")])
report(11, "COMSAuditTrail", "ECO-COMS Audit Trail", "COMSAuditLog", ["ViewCOMSAuditLog"], ("timestamp", "DESCENDING"),
       [("timestamp", "Timestamp"), ("action", "Action"), ("objectType", "Change Type"), ("coName", "Organization"), ("coReferenceId", "Organization Code"),
        ("roleName", "Role"), ("positionName", "Position"), ("effectiveDate", "Effective Date"), ("triggeredBy", "Changed By"), ("details", "Details")])
report(12, "COMSBulkRunHistory", "ECO-COMS Bulk Runs", "COMSBulkRun", ["ManageCOMSShellOrgs"], ("uploadedAt", "DESCENDING"),
       [("batchRef", "Batch"), ("source", "Source"), ("runMode", "Mode"), ("status", "Status"), ("effectiveDate", "Effective Date"),
        ("changeCount", "Changes"), ("uploadedByName", "Uploaded By"), ("uploadedAt", "Uploaded"), ("finishedAt", "Finished"), ("summary", "Summary")])
report(13, "COMSApplicationSetup", "ECO-COMS Applications", "COMSApplication", ["ManageCOMSApplicationSetup", "ManageCOMSAdminProvisioning"], ("appId", "ASCENDING"),
       [("appId", "Application ID"), ("name", "Name"), ("orgType", "Org Type"), ("orgSubtype", "Org Subtype"), ("namePrefix", "Allowed Prefixes"),
        ("active", "Active"), ("downstreamConsumer", "Downstream Consumer"), ("workdayOrgName", "Workday Organization")])
print('insights page, BreakdownChart card, 4 reports')
