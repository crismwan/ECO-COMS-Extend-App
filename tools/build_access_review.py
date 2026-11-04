#!/usr/bin/env python3
"""Access Review (2026-11-04): every position that holds an ECO-COMS shell role, with when ECO-COMS last
changed it and when someone last confirmed it is still needed.

Same structure as the other list pages (product owner 2026-11-04: "grids are not similar to the structure on
other pages"): a VIEW page with the ← Home link and About box, count cards, and a list grid (Excel export,
sortable text columns, buttons last). Editable grids on EDIT pages draw as boxed tables, so the review is
not ticked in the grid; each row's Confirm button opens a small EDIT page (confirmAccessReview) whose OK
writes one Role Assignment / REVIEW audit record and returns to the list (flow accessReviewFlow).

- Rows: Workday's role assignments (WQL allShellAssignableRolesinTenant), one row per role, organization and
  position. Workday role assignments carry no expiry date, so the review is based on the app's own history.
- History: newest 200 audit records (Graph via tools/graphql_audit.py, which converts the REST endpoints
  written here). Matched by role name and position WID (or the position ID in the name).
- Manage opens the existing Manage Role Assignment page for that role and organization.
Also writes AccessReviewCard on the RBAC Hub and registers the tasks and flow. Idempotent.
"""
import json, os

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'presentation')
FOS = lambda codes: [{"code": c} for c in codes]
FOOT = {"type": "footer", "children": [{"type": "pod", "podId": "ecoComsFooter"}]}
load = lambda n: json.load(open(os.path.join(ROOT, n), encoding='utf-8'))
def save(n, d): open(os.path.join(ROOT, n), 'w', encoding='utf-8').write(json.dumps(d, indent=2, ensure_ascii=False) + '\n')

SCRIPT = '''/* Access Review helpers (tools/build_access_review.py). logs come newest first. */
var rowsFrom = function(roles) {
  list:flatten(roles.map(r => { list:flatten((r.roleAssignments ?? []).filter(ra => { ra.organization != null && r.role != null }).map(ra => { (ra.cf_ZCF_EE_RoleAssignedToAsPositionRestrictions ?? []).map(p => { { 'role': r.role.descriptor ?? '', 'roleWid': r.role.id ?? '', 'org': ra.organization.descriptor ?? '', 'orgWid': ra.organization.id ?? '', 'pos': p.descriptor ?? '', 'posWid': p.id ?? '' } }) })) }));
};

var lastWhen = function(logs, action, roleName, posWid, posName) {
  let posId = (posName ?? '').substringBefore(' ');
  let m = logs.filter(a => { (a.action ?? '') == action && (a.roleName ?? '') == roleName && ((!empty(posWid) && (a.positionWid ?? '').contains(posWid)) || (!empty(posId) && (a.positionName ?? '').contains(posId))) });
  m.size() == 0 ? '' : ('' + (m[0].timestamp ?? '')).substring(0, 10);
};

var lastChanged = function(logs, roleName, posWid, posName) {
  let d = lastWhen(logs, 'ASSIGN POSITION', roleName, posWid, posName);
  empty(d) ? 'Not through ECO-COMS' : d;
};

var lastReviewed = function(logs, roleName, posWid, posName) {
  let d = lastWhen(logs, 'REVIEW', roleName, posWid, posName);
  empty(d) ? 'Never' : d;
};

var countNeverReviewed = function(rows, logs) {
  rows.filter(r => { empty(lastWhen(logs, 'REVIEW', r.role, r.posWid, r.pos)) }).size();
};

var countOutside = function(rows, logs) {
  rows.filter(r => { empty(lastWhen(logs, 'ASSIGN POSITION', r.role, r.posWid, r.pos)) }).size();
};

{
  "rowsFrom": rowsFrom,
  "lastWhen": lastWhen,
  "lastChanged": lastChanged,
  "lastReviewed": lastReviewed,
  "countNeverReviewed": countNeverReviewed,
  "countOutside": countOutside
}
'''
open(os.path.join(ROOT, 'scripts', 'comsAccessReview.script'), 'w', encoding='utf-8').write(SCRIPT)

ROWS = "comsAccessReview.rowsFrom(shellRoles.data ?? [])"
LOGS = "list:flatten([auditPage0.data ?? [], auditPage1.data ?? []])"
NOTE = lambda html: {"type": "richText", "id": "aboutRichText", "enabled": False,
    "value": '<span style="color:#0055B7;font-size:12px;font-weight:700">ⓘ </span><span style="color:#374151;font-size:12px">' + html + '</span>'}
AUDIT_EPS = [
    {"name": "auditLogCount", "baseUrlType": "BUSINESS-OBJECT", "url": "/comsAuditLogs?limit=1", "authType": "sso", "failOnStatusCodes": FOS([400, 429])},
    {"name": "auditPage0", "baseUrlType": "BUSINESS-OBJECT", "authType": "sso", "isCollection": True, "failOnStatusCodes": FOS([429]),
     "url": "<% let t = auditLogCount.total ?? 0; let start = (t - 100) < 0 ? 0 : (t - 100); let cnt = t - start; '/comsAuditLogs?limit=' + (cnt > 0 ? cnt : 1) + '&offset=' + (cnt > 0 ? start : t) %>"},
    {"name": "auditPage1", "baseUrlType": "BUSINESS-OBJECT", "authType": "sso", "isCollection": True, "failOnStatusCodes": FOS([429]),
     "url": "<% let t = auditLogCount.total ?? 0; let end = (t - 100) < 0 ? 0 : (t - 100); let start = (end - 100) < 0 ? 0 : (end - 100); let cnt = end - start; '/comsAuditLogs?limit=' + (cnt > 0 ? cnt : 1) + '&offset=' + (cnt > 0 ? start : t) %>"}]
txt = lambda cid, label, value: {"type": "column", "columnId": cid, "label": label, "sortableAndFilterable": "true",
    "cellTemplate": {"type": "text", "id": cid + "Text", "enabled": False, "value": value}}
ROW_PARAMS = {"role": "<% rv.role %>", "roleWid": "<% rv.roleWid %>", "org": "<% rv.org %>", "orgWid": "<% rv.orgWid %>",
              "pos": "<% rv.pos %>", "posWid": "<% rv.posWid %>"}
count = lambda title, sub, text: {"type": "card", "cardId": "CountCard",
    "parameters": "<% { 'title': '" + title + "', 'subtitle': '" + sub + "', 'countText': " + text + " } %>"}

page = {"id": "accessReview", "securityDomains": ["ManageCOMSShellOrgs"], "include": ["comsAccessReview.script"],
  "endPoints": [
    {"name": "shellRoles", "baseUrlType": "workday-wql", "url": "data", "authType": "sso", "bestEffort": "true",
     "wqlQuery": {"queryId": "allShellAssignableRolesinTenant"}, "failOnStatusCodes": FOS([400, 429])}] + AUDIT_EPS,
  "presentation": {"pageType": "VIEW", "headerSize": "STANDARD", "title": {"type": "title", "label": "ECO-COMS: Access Review"},
    "body": {"type": "basicFormLayout", "id": "accessReviewForm", "sections": [
      {"type": "layoutSection", "id": "navSection", "children": [
        {"type": "button", "label": "← Home", "taskReference": {"taskId": "home"}, "action": "LINK"}]},
      {"type": "layoutSection", "id": "aboutSection", "children": [{"type": "fieldSet", "id": "aboutFieldSet", "title": "About This Page", "children": [NOTE(
        "Every position that holds an ECO-COMS shell role in Workday, with when ECO-COMS last changed it and when someone last "
        "confirmed it is still needed (from the newest 200 Audit Log records). Workday role assignments have no expiry date, so "
        "review them here: <b>Confirm</b> records in the Audit Log that the position still needs the role, and <b>Manage</b> "
        "opens the role assignment to remove it.")]}]},
      {"type": "layoutSection", "id": "summaryCardsSection", "children": [{"type": "cardContainer", "id": "accessReviewCardContainer", "layout": "grid", "cards": [
        count("Positions", "Holding a shell role", "'' + size(" + ROWS + ") + ' positions'"),
        count("Never Reviewed", "No review in the Audit Log", "'' + comsAccessReview.countNeverReviewed(" + ROWS + ", " + LOGS + ") + ' never reviewed'"),
        count("Assigned Outside ECO-COMS", "No ECO-COMS change on record", "'' + comsAccessReview.countOutside(" + ROWS + ", " + LOGS + ") + ' assigned outside'")]}]},
      {"type": "layoutSection", "id": "gridSection", "children": [{"type": "fieldSet", "id": "reviewFieldSet", "title": "Role Assignments", "children": [
        {"type": "text", "id": "noRowsText", "label": "ⓘ Nothing to show", "enabled": False, "visible": "<% size(" + ROWS + ") == 0 %>",
         "value": "No positions hold an ECO-COMS shell role right now."},
        {"type": "grid", "id": "accessReviewGrid", "label": "Positions Holding Shell Roles", "rowVariableName": "rv", "readOnly": True,
         "rows": "<% " + ROWS + " %>",
         "columns": [
           txt("colRole", "Role", "<% rv.role %>"),
           txt("colOrg", "Organization", "<% rv.org %>"),
           txt("colPosition", "Position", "<% rv.pos %>"),
           txt("colChanged", "Last Changed in ECO-COMS", "<% comsAccessReview.lastChanged(" + LOGS + ", rv.role, rv.posWid, rv.pos) %>"),
           txt("colReviewed", "Last Reviewed", "<% comsAccessReview.lastReviewed(" + LOGS + ", rv.role, rv.posWid, rv.pos) %>"),
           {"type": "column", "columnId": "colConfirm", "label": "Confirm", "cellTemplate": {
             "type": "button", "id": "confirmReviewButton", "label": "Confirm", "action": "AUXILIARY",
             "taskReference": {"taskId": "confirmAccessReview", "parameterBindings": ROW_PARAMS}}},
           {"type": "column", "columnId": "colManage", "label": "Manage", "cellTemplate": {
             "type": "button", "id": "manageRoleButton", "label": "Manage", "action": "AUXILIARY",
             "taskReference": {"taskId": "editRoleAssignment", "parameterBindings": {
               "roleId": "<% rv.roleWid %>", "roleName": "<% rv.role %>", "orgId": "<% rv.orgWid %>", "orgName": "<% rv.org %>"}}}}]}]}]}]},
    "footer": FOOT}}
save('accessReview.pmd', page)

ro = lambda wid, label, value: {"type": "text", "id": wid, "label": label, "enabled": False, "value": value}
OUT = lambda field, value: {"outboundPath": field, "value": value}
confirm = {"id": "confirmAccessReview", "securityDomains": ["ManageCOMSShellOrgs"],
  "endPoints": [
    {"name": "selectedWorker", "baseUrlType": "COMMON", "url": "/workers/me", "authType": "sso", "bestEffort": "true",
     "failOnStatusCodes": FOS([400, 403, 429])}],
  "outboundData": {"outboundEndPoints": [
    {"name": "postReview", "baseUrlType": "BUSINESS-OBJECT", "url": "/comsAuditLogs", "httpMethod": "POST", "authType": "sso",
     "failOnStatusCodes": FOS([400, 403, 429, 500]), "values": [
       OUT("timestamp", "<% date:now().format(\"yyyy-MM-dd'T'HH:mm:ss'Z'\") %>"),
       OUT("objectType", "Role Assignment"), OUT("action", "REVIEW"),
       OUT("coReferenceId", "<% queryParams.posWid ?? '' %>"), OUT("coName", "<% queryParams.org ?? '' %>"),
       OUT("roleName", "<% queryParams.role ?? '' %>"), OUT("roleWid", "<% queryParams.roleWid ?? '' %>"),
       OUT("orgWid", "<% queryParams.orgWid ?? '' %>"),
       OUT("positionName", "<% queryParams.pos ?? '' %>"), OUT("positionWid", "<% queryParams.posWid ?? '' %>"),
       OUT("effectiveDate", "<% date:now().format('yyyy-MM-dd') %>"),
       OUT("triggeredBy", "<% selectedWorker.descriptor ?? '' %>"), OUT("changedByWid", "<% selectedWorker.id ?? '' %>"),
       OUT("details", "<% 'Access review: ' + (queryParams.pos ?? '') + ' still needs ' + (queryParams.role ?? '') + ' on ' + (queryParams.org ?? '') %>")]}]},
  "onSubmit": "<%\n  stillNeededCheckBox.clearError();\n  let valid = true;\n  if (stillNeededCheckBox.value != true) {\n    stillNeededCheckBox.setError('Tick the box to confirm this position still needs the role.');\n    valid = false;\n  }\n  valid;\n%>",
  "presentation": {"pageType": "EDIT", "headerSize": "STANDARD", "title": {"type": "title", "label": "ECO-COMS: Confirm Access"},
    "cancelOverride": {"taskId": "accessReview"},
    "body": {"type": "basicFormLayout", "id": "confirmAccessReviewForm", "sections": [
      {"type": "layoutSection", "id": "aboutSection", "children": [{"type": "fieldSet", "id": "aboutFieldSet", "title": "About This Page", "children": [NOTE(
        "Confirm that this position still needs this role. Clicking <b>OK</b> records your review in the Audit Log; nothing "
        "changes in Workday. To take the role away instead, click <b>Cancel</b> and use <b>Manage</b> on the Access Review.")]}]},
      {"type": "layoutSection", "id": "confirmSection", "children": [{"type": "fieldSet", "id": "confirmFieldSet", "title": "Role Assignment", "children": [
        ro("roleText", "Role", "<% queryParams.role ?? '' %>"),
        ro("orgText", "Organization", "<% queryParams.org ?? '' %>"),
        ro("positionText", "Position", "<% queryParams.pos ?? '' %>"),
        {"type": "checkBox", "id": "stillNeededCheckBox", "label": "This position still needs this role", "value": "<% false %>",
         "onChange": "<% self.clearError() %>"}]}]}]},
    "footer": FOOT}}
save('confirmAccessReview.pmd', confirm)

amd_name = [f for f in os.listdir(ROOT) if f.endswith('.amd')][0]
amd = load(amd_name)
for tid in ('accessReview', 'confirmAccessReview'):
    if not any(t['id'] == tid for t in amd['tasks']):
        amd['tasks'].append({"id": tid, "routingPattern": "/" + tid, "page": {"id": tid}})
amd['flowDefinitions'] = [f for f in amd.get('flowDefinitions', []) if f['id'] != 'accessReviewFlow'] + [{"id": "accessReviewFlow", "flowSteps": [
        {"id": "confirmAccessReviewStep", "taskId": "confirmAccessReview", "startsFlow": True,
         "transitions": [{"order": "a", "value": "accessReviewStep", "condition": "true"}]},
        {"id": "accessReviewStep", "taskId": "accessReview", "endsFlow": True}]}]
save(amd_name, amd)

save(os.path.join('cards', 'AccessReviewCard.card'), {
    "id": "AccessReviewCard",
    "header": {"title": "Access Review", "subtitle": "Is every role still needed?", "icon": "wd-accent-shield"},
    "body": {"type": "simpleCard", "value": "Every position holding a shell role, when it last changed and when it was last reviewed. Confirm or remove each one."},
    "footer": [{"label": "Open Access Review", "taskReference": {"taskId": "accessReview"}}]})
hub = load('hubLanding.pmd')


def add_card(n):
    if isinstance(n, dict):
        cards = n.get('cards')
        if isinstance(cards, list) and any(c.get('cardId') == 'InsightsCard' for c in cards if isinstance(c, dict)):
            if not any(c.get('cardId') == 'AccessReviewCard' for c in cards):
                i = next(i for i, c in enumerate(cards) if c.get('cardId') == 'InsightsCard')
                cards.insert(i + 1, {"type": "card", "cardId": "AccessReviewCard"})
            return True
        return any(add_card(v) for v in n.values())
    if isinstance(n, list):
        return any(add_card(v) for v in n)
    return False


if not add_card(hub):
    raise SystemExit('build_access_review: InsightsCard not found on the RBAC Hub')
save('hubLanding.pmd', hub)
print('access review pages, card, tasks and flow written')
