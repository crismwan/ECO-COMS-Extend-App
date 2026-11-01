#!/usr/bin/env python3
import subprocess, sys
"""Writes the shellOrgDetail page (one shell organization: status, role assignments, audit history),
registers its task in the AMD, and adds Details buttons + active-first ordering to Shell Org Manager.
Re-run after editing: python3 tools/build_org_detail.py"""
import json, os
ROOT = os.path.join(os.path.dirname(__file__), '..', 'presentation')
FOS = lambda codes: [{"code": c} for c in codes]
FOOT = {"type": "footer", "children": [{"type": "pod", "podId": "ecoComsFooter"}]}
load = lambda n: json.load(open(os.path.join(ROOT, n)))
def save(n, d): open(os.path.join(ROOT, n), 'w').write(json.dumps(d, indent=2, ensure_ascii=False) + '\n')
def note(sid, fid, title, rid, html):
    return {"type": "layoutSection", "id": sid, "children": [{"type": "fieldSet", "id": fid, "title": title, "children": [
        {"type": "richText", "id": rid, "enabled": False,
         "value": '<span style="color:#0055B7;font-size:12px;font-weight:700">ⓘ </span><span style="color:#374151;font-size:12px">' + html + '</span>'}]}]}
txt = lambda cid, label, value: {"type": "column", "columnId": cid, "label": label, "sortableAndFilterable": "true",
    "cellTemplate": {"type": "text", "id": cid + "Text", "enabled": False, "value": value}}
inst = lambda cid, label, values: {"type": "column", "columnId": cid, "label": label,
    "cellTemplate": {"type": "instanceList", "id": cid + "InstanceList", "view": True, "relatedTask": True, "enabled": False, "values": values, "widKey": "id"}}
empty_msg = lambda tid, cond, text: {"type": "text", "id": tid, "label": "ⓘ Nothing to show", "enabled": False, "visible": "<% " + cond + " %>", "value": text}

OID = "(queryParams.orgId ?? '')"
ORG = "((allShellOrgs.data ?? []).filter(o => { (o.workdayID ?? '') == " + OID + " }))"
ACTIVE = "(size(" + ORG + ") > 0 && " + ORG + "[0].cf_active1 == true)"
NAME = "(size(" + ORG + ") > 0 ? (" + ORG + "[0].organizationByName.descriptor ?? " + ORG + "[0].code) : (queryParams.orgName ?? ''))"
CODE = "(size(" + ORG + ") > 0 ? (" + ORG + "[0].code ?? '') : (queryParams.orgCode ?? ''))"
ROLES = ("(list:flatten((shellRoles.data ?? []).map(r => { (r.roleAssignments ?? []).filter(ra => { ra.organization != null && ra.organization.id == " + OID + " })"
         ".map(ra => { { 'role': r.role, 'org': ra.organization, 'positions': ra.cf_ZCF_EE_RoleAssignedToAsPositionRestrictions ?? [], 'workers': ra.workersAssigned ?? [] } }) })))")
# audit records about this org: written with its WID, its code, or (role assignments) its name
AUD = ("(list:sort(list:flatten([auditPage0.data ?? [], auditPage1.data ?? []]).filter(a => { "
       "(!empty(a.orgWid) && a.orgWid == " + OID + ") || (!empty(queryParams.orgCode) && (a.coReferenceId ?? '') == queryParams.orgCode) || "
       "(!empty(queryParams.orgName) && (a.coName ?? '') == queryParams.orgName) }), 'timestamp', false))")

page = {"id": "shellOrgDetail", "securityDomains": ["ManageCOMSShellOrgs"],
  "endPoints": [
    {"name": "allShellOrgs", "baseUrlType": "workday-wql", "url": "data", "authType": "sso", "bestEffort": "true",
     "wqlQuery": {"queryId": "allShellOrgs"}, "failOnStatusCodes": FOS([400, 429])},
    {"name": "shellRoles", "baseUrlType": "workday-wql", "url": "data", "authType": "sso", "bestEffort": "true",
     "wqlQuery": {"queryId": "allShellAssignableRolesinTenant"}, "failOnStatusCodes": FOS([400, 429])},
    {"name": "auditLogCount", "baseUrlType": "BUSINESS-OBJECT", "url": "/comsAuditLogs?limit=1", "authType": "sso", "failOnStatusCodes": FOS([400, 429])},
    {"name": "auditPage0", "baseUrlType": "BUSINESS-OBJECT", "authType": "sso", "isCollection": True, "failOnStatusCodes": FOS([429]),
     "url": "<% let t = auditLogCount.total ?? 0; let start = (t - 100) < 0 ? 0 : (t - 100); let cnt = t - start; '/comsAuditLogs?limit=' + (cnt > 0 ? cnt : 1) + '&offset=' + (cnt > 0 ? start : t) %>"},
    {"name": "auditPage1", "baseUrlType": "BUSINESS-OBJECT", "authType": "sso", "isCollection": True, "failOnStatusCodes": FOS([429]),
     "url": "<% let t = auditLogCount.total ?? 0; let end = (t - 100) < 0 ? 0 : (t - 100); let start = (end - 100) < 0 ? 0 : (end - 100); let cnt = end - start; '/comsAuditLogs?limit=' + (cnt > 0 ? cnt : 1) + '&offset=' + (cnt > 0 ? start : t) %>"}],
  "presentation": {"headerSize": "STANDARD", "title": {"type": "title", "label": "<% 'ECO-COMS: Shell Organization – ' + " + NAME + " %>"},
    "body": {"type": "basicFormLayout", "id": "orgDetailForm", "sections": [
      {"type": "layoutSection", "id": "navSection", "children": [
        {"type": "button", "id": "backButton", "label": "← Shell Org Manager", "action": "LINK",
         "taskReference": {"taskId": "shellOrgManager", "parameterBindings": {"appCode": "<% queryParams.appCode ?? '' %>", "appName": "<% queryParams.appName ?? '' %>"}}}]},
      note("aboutSection", "aboutFieldSet", "About This Page", "aboutRichText",
        "One shell organization: its status in Workday, the roles assigned on it with their positions and workers, and the ECO-COMS changes made to it "
        "(from the newest 200 Audit Log records). Use <b>Inactivate Organization</b> or <b>Reactivate Organization</b> to change its status, or <b>Manage</b> on a role to add or remove positions."),
      {"type": "layoutSection", "id": "cardsSection", "children": [{"type": "cardContainer", "id": "orgCardContainer", "layout": "grid", "cards": [
        {"type": "card", "cardId": "CountCard", "parameters": "<% { 'title': 'Status', 'subtitle': 'In Workday', 'countText': size(" + ORG + ") == 0 ? 'Not found' : (" + ACTIVE + " ? '✓ Active' : '○ Inactive') } %>"},
        {"type": "card", "cardId": "CountCard", "parameters": "<% { 'title': 'Roles', 'subtitle': 'Assigned on this organization', 'countText': '' + size(" + ROLES + ") + (size(" + ROLES + ") == 1 ? ' role assignment' : ' role assignments') + ' · ' + '' + size(list:flatten(" + ROLES + ".map(ra => { ra.positions })).map(p => { p.id }).distinct()) + (size(list:flatten(" + ROLES + ".map(ra => { ra.positions })).map(p => { p.id }).distinct()) == 1 ? ' position' : ' positions') } %>"},
        {"type": "card", "cardId": "CountCard", "parameters": "<% { 'title': 'Changes', 'subtitle': 'Made through ECO-COMS', 'countText': '' + size(" + AUD + ") + (size(" + AUD + ") == 1 ? ' change recorded' : ' changes recorded') } %>"}]}]},
      {"type": "layoutSection", "id": "summarySection", "children": [{"type": "fieldSet", "id": "summaryFieldSet", "title": "Organization", "children": [
        {"type": "instanceList", "id": "orgInstanceList", "label": "Organization", "view": True, "relatedTask": True, "enabled": False, "widKey": "id",
         "values": "<% empty(queryParams.orgId) ? [] : [{ 'id': queryParams.orgId, 'descriptor': " + NAME + " }] %>"},
        {"type": "text", "id": "orgCodeText", "label": "Code", "enabled": False, "value": "<% " + CODE + " %>"},
        {"type": "button", "id": "changeStatusButton", "label": "<% " + ACTIVE + " ? 'Inactivate Organization' : 'Reactivate Organization' %>", "action": "AUXILIARY",
         "taskReference": {"taskId": "manageShellOrgStatus", "parameterBindings": {
           "orgId": "<% queryParams.orgId ?? '' %>", "orgCode": "<% " + CODE + " %>", "orgName": "<% " + NAME + " %>",
           "currentStatus": "<% " + ACTIVE + " ? 'Active' : 'Inactive' %>", "effectiveDate": "<% date:now().format('yyyy-MM-dd') %>",
           "patternName": "<% " + CODE + " %>", "orgType": "<% queryParams.orgType ?? '' %>", "comsAppId": "<% queryParams.appCode ?? '' %>"}}}]}]},
      {"type": "layoutSection", "id": "rolesSection", "children": [{"type": "fieldSet", "id": "rolesFieldSet", "title": "Roles on This Organization", "children": [
        empty_msg("noRolesText", "size(" + ROLES + ") == 0", "No shell roles are assigned on this organization."),
        {"type": "grid", "id": "orgRolesGrid", "gridType": "LIST", "multiViewStylingEnabled": True, "autoPaging": True, "enabled": False, "excelExportEnabled": True,
         "rowVariableName": "ra", "rows": "<% " + ROLES + " %>", "label": "Role Assignments",
         "columns": [inst("colRole", "Role", "<% ra.role != null ? [ra.role] : [] %>"),
                     inst("colPositions", "Positions", "<% ra.positions %>"),
                     inst("colWorkers", "Workers", "<% ra.workers %>"),
                     {"type": "column", "columnId": "colManage", "label": "Manage", "excel": {"enabled": False}, "cellTemplate": {
                       "type": "button", "id": "manageRoleButton", "label": "Manage", "action": "AUXILIARY",
                       "taskReference": {"taskId": "editRoleAssignment", "parameterBindings": {
                         "roleId": "<% ra.role.id ?? '' %>", "roleName": "<% ra.role.descriptor ?? '' %>",
                         "orgId": "<% ra.org.id ?? '' %>", "orgName": "<% ra.org.descriptor ?? '' %>",
                         "appCode": "<% queryParams.appCode ?? '' %>", "appName": "<% queryParams.appName ?? '' %>"}}}}]}]}]},
      {"type": "layoutSection", "id": "historySection", "children": [{"type": "fieldSet", "id": "historyFieldSet", "title": "Change History", "children": [
        empty_msg("noHistoryText", "size(" + AUD + ") == 0", "No ECO-COMS changes to this organization in the newest 200 Audit Log records. Older changes are in the Audit Log Viewer."),
        {"type": "grid", "id": "orgHistoryGrid", "gridType": "LIST", "multiViewStylingEnabled": True, "autoPaging": True, "enabled": False, "excelExportEnabled": True,
         "rowVariableName": "al", "rows": "<% " + AUD + " %>", "label": "Changes",
         "columns": [txt("colWhen", "When", "<% (al.timestamp ?? '').replace('T', ' ').replace('Z', ' UTC') %>"),
                     txt("colAction", "Action", "<% al.action ?? '' %>"),
                     txt("colRoleName", "Role", "<% al.roleName ?? '' %>"),
                     txt("colPosition", "Position", "<% al.positionName ?? '' %>"),
                     txt("colEffective", "Effective Date", "<% '' + (al.effectiveDate ?? '') %>"),
                     txt("colBy", "Changed By", "<% al.triggeredBy ?? '' %>"),
                     txt("colDetails", "Details", "<% al.details ?? '' %>")]}]}]}]},
    "footer": FOOT, "pageType": "VIEW"}}
save('shellOrgDetail.pmd', page)

# AMD task
amd = load('ecocomsphase_xclw_cm_sync2_vmzvxm.amd')
if not any(t['id'] == 'shellOrgDetail' for t in amd['tasks']):
    amd['tasks'].append({"id": "shellOrgDetail", "routingPattern": "/shellOrgDetail", "page": {"id": "shellOrgDetail"}})
save('ecocomsphase_xclw_cm_sync2_vmzvxm.amd', amd)

# Shell Org Manager: Details buttons and active orgs first
som = load('shellOrgManager.pmd')
def details_col(prefix):
    return {"type": "column", "columnId": prefix + "Details", "label": "Details", "excel": {"enabled": False}, "cellTemplate": {
        "type": "button", "id": prefix + "DetailsButton", "label": "Details", "action": "AUXILIARY",
        "taskReference": {"taskId": "shellOrgDetail", "parameterBindings": {
            "orgId": "<% org.workdayID ?? '' %>", "orgCode": "<% org.code ?? '' %>",
            "orgName": "<% org.organizationByName.descriptor ?? org.code ?? '' %>",
            "appCode": "<% queryParams.appCode ?? '' %>", "appName": "<% queryParams.appName ?? '' %>"}}}}
def active_first(rows):
    inner = rows.strip()[2:-2].strip()
    if inner.startswith('list:flatten([') and 'cf_active1 == true' in inner:
        return rows
    return "<% list:flatten([(" + inner + ").filter(o => { o.cf_active1 == true }), (" + inner + ").filter(o => { o.cf_active1 != true })]) %>"
def walk(o):
    if isinstance(o, dict):
        if o.get('id') in ('allShellOrgsGrid', 'filteredShellOrgsGrid'):
            prefix = 'colAllOrg' if o['id'] == 'allShellOrgsGrid' else 'colFiltOrg'
            if not any(c['columnId'] == prefix + 'Details' for c in o['columns']):
                i = [c['columnId'] for c in o['columns']].index(prefix + 'Manage')
                o['columns'].insert(i, details_col(prefix))
            o['rows'] = active_first(o['rows'])
        for v in o.values(): walk(v)
    elif isinstance(o, list):
        for v in o: walk(v)
walk(som['presentation'])
save('shellOrgManager.pmd', som)
print('ok')

# ── Request again: requester list → request page prefilled with the role name ──
SHORT = "((role.roleName ?? '').contains(':ROLE:') ? (role.roleName ?? '').substringAfter(':ROLE:') : (role.roleName ?? ''))"
view = load('assignableRoleManagerView.pmd')
def add_again(o):
    if isinstance(o, dict):
        if o.get('id') == 'assignableRolesGrid' and not any(c['columnId'] == 'colAgain' for c in o['columns']):
            o['columns'].append({"type": "column", "columnId": "colAgain", "label": "New Request", "excel": {"enabled": False}, "cellTemplate": {
                "type": "button", "id": "requestAgainButton", "action": "AUXILIARY",
                "label": "<% (role.status ?? '') == 'Denied' ? 'Retry' : 'Reuse' %>",
                "taskReference": {"taskId": "assignableRoleManager", "parameterBindings": {
                    "againRoleName": "<% " + SHORT + " %>",
                    "againFrom": "<% role.roleName ?? '' %>",
                    "againStatus": "<% role.status ?? '' %>",
                    "againReason": "<% role.denialReason ?? '' %>"}}}})
        for x in o.values(): add_again(x)
    elif isinstance(o, list):
        for x in o: add_again(x)
add_again(view['presentation'])
save('assignableRoleManagerView.pmd', view)

req = load('assignableRoleManager.pmd')
def prefill(o):
    if isinstance(o, dict):
        if o.get('type') == 'text' and o.get('id') == 'roleName' and 'value' not in o:
            o['value'] = "<% queryParams.againRoleName ?? '' %>"
        for x in o.values(): prefill(x)
    elif isinstance(o, list):
        for x in o: prefill(x)
prefill(req['presentation'])
secs = req['presentation']['body']['sections']
if not any(s.get('id') == 'againSection' for s in secs):
    secs.insert(1, {"type": "layoutSection", "id": "againSection", "children": [{"type": "fieldSet", "id": "againFieldSet", "children": [
        {"type": "text", "id": "againNoteText", "enabled": False, "label": "ⓘ Requesting again",
         "visible": "<% !empty(queryParams.againFrom) %>",
         "value": "<% 'Based on ' + (queryParams.againFrom ?? '') + ' (' + (queryParams.againStatus ?? '') + ')' + "
                  "(empty(queryParams.againReason) ? '' : ('. Reason given: ' + queryParams.againReason)) + "
                  "'. The role name is filled in; choose the application, organization, positions and effective date again.' %>"}]}]})
save('assignableRoleManager.pmd', req)
print('again ok')

# final UI polish pass (grid labels, About ⓘ, ...); see tools/polish.py
subprocess.run([sys.executable, os.path.join(os.path.dirname(__file__), 'polish.py')], check=True)
