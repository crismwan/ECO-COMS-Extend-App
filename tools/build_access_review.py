#!/usr/bin/env python3
"""Access Review (2026-11-04): every position that holds an ECO-COMS shell role, with when ECO-COMS last
changed it and when someone last confirmed it is still needed.

Same structure as the other list pages (product owner 2026-11-04: "grids are not similar to the structure on
other pages"): a VIEW page with the ← Home link and About box, count cards, and a list grid (Excel export,
sortable text columns, buttons last). Grids with tick boxes only exist on EDIT pages, which Workday draws as
boxed tables, so the checklist is its own page: Review All Positions opens confirmAccessReview, one row per
position with a Still Needed tick; OK writes one Role Assignment / REVIEW audit record per ticked row and
returns to the list (flow accessReviewFlow).

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
        {"type": "button", "id": "reviewAllButton", "label": "Review All Positions", "action": "PRIMARY",
         "taskReference": {"taskId": "confirmAccessReview"}},
        {"type": "grid", "id": "accessReviewGrid", "label": "Positions Holding Shell Roles", "rowVariableName": "rv", "readOnly": True,
         "rows": "<% " + ROWS + " %>",
         "columns": [
           txt("colRole", "Role", "<% rv.role %>"),
           txt("colOrg", "Organization", "<% rv.org %>"),
           txt("colPosition", "Position", "<% rv.pos %>"),
           txt("colChanged", "Last Changed in ECO-COMS", "<% comsAccessReview.lastChanged(" + LOGS + ", rv.role, rv.posWid, rv.pos) %>"),
           txt("colReviewed", "Last Reviewed", "<% comsAccessReview.lastReviewed(" + LOGS + ", rv.role, rv.posWid, rv.pos) %>"),
           {"type": "column", "columnId": "colManage", "label": "Manage", "cellTemplate": {
             "type": "button", "id": "manageRoleButton", "label": "Manage", "action": "AUXILIARY",
             "taskReference": {"taskId": "editRoleAssignment", "parameterBindings": {
               "roleId": "<% rv.roleWid %>", "roleName": "<% rv.role %>", "orgId": "<% rv.orgWid %>", "orgName": "<% rv.org %>"}}}}]}]}]}]},
    "footer": FOOT}}
save('accessReview.pmd', page)

GOUT = lambda field, value: {"value": value, "valueOutBinding": "postReview." + field}
REVIEW_OUT = [
    GOUT("timestamp", "<% date:now().format(\"yyyy-MM-dd'T'HH:mm:ss'Z'\") %>"),
    GOUT("objectType", "Role Assignment"), GOUT("action", "REVIEW"),
    GOUT("coReferenceId", "<% rv.posWid %>"), GOUT("coName", "<% rv.org %>"),
    GOUT("roleName", "<% rv.role %>"), GOUT("roleWid", "<% rv.roleWid %>"), GOUT("orgWid", "<% rv.orgWid %>"),
    GOUT("positionName", "<% rv.pos %>"), GOUT("positionWid", "<% rv.posWid %>"),
    GOUT("effectiveDate", "<% date:now().format('yyyy-MM-dd') %>"),
    GOUT("triggeredBy", "<% selectedWorker.descriptor ?? '' %>"), GOUT("changedByWid", "<% selectedWorker.id ?? '' %>"),
    GOUT("details", "<% 'Access review: ' + rv.pos + ' still needs ' + rv.role + ' on ' + rv.org %>"),
]
# Checklist (product owner 2026-11-04: "the checklist worked best so you can review all at once"): every row on one
# EDIT page; each ticked row is its own POST (per-row grid submission), unticked rows are excluded.
confirm = {"id": "confirmAccessReview", "securityDomains": ["ManageCOMSShellOrgs"], "include": ["comsAccessReview.script"],
  "endPoints": [
    {"name": "selectedWorker", "baseUrlType": "COMMON", "url": "/workers/me", "authType": "sso", "bestEffort": "true",
     "failOnStatusCodes": FOS([400, 403, 429])},
    {"name": "shellRoles", "baseUrlType": "workday-wql", "url": "data", "authType": "sso", "bestEffort": "true",
     "wqlQuery": {"queryId": "allShellAssignableRolesinTenant"}, "failOnStatusCodes": FOS([400, 429])}] + AUDIT_EPS,
  "outboundData": {"outboundEndPoints": [
    {"name": "postReview", "baseUrlType": "BUSINESS-OBJECT", "url": "/comsAuditLogs", "httpMethod": "POST", "authType": "sso",
     "exclude": "<% stillNeededCheckBox.value != true %>", "failOnStatusCodes": FOS([400, 403, 429, 500])}]},
  "presentation": {"pageType": "EDIT", "headerSize": "STANDARD", "title": {"type": "title", "label": "ECO-COMS: Review All Positions"},
    "cancelOverride": {"taskId": "accessReview"},
    "body": {"type": "basicFormLayout", "id": "confirmAccessReviewForm", "sections": [
      {"type": "layoutSection", "id": "aboutSection", "children": [{"type": "fieldSet", "id": "aboutFieldSet", "title": "About This Page", "children": [NOTE(
        "Tick <b>Still Needed</b> on every position you checked and click <b>OK</b>: each tick is recorded in the Audit Log as a "
        "review, and nothing changes in Workday. Leave a row unticked to skip it. To take a role away, click <b>Cancel</b> and use "
        "<b>Manage</b> on the Access Review.")]}]},
      {"type": "layoutSection", "id": "reviewSection", "children": [{"type": "fieldSet", "id": "reviewFieldSet", "title": "Role Assignments", "children": [
        {"type": "text", "id": "noRowsText", "label": "ⓘ Nothing to show", "enabled": False, "visible": "<% size(" + ROWS + ") == 0 %>",
         "value": "No positions hold an ECO-COMS shell role right now."},
        {"type": "grid", "id": "reviewChecklistGrid", "label": "Positions Holding Shell Roles", "rowVariableName": "rv",
         "rows": "<% " + ROWS + " %>", "doNotAdd": True, "doNotRemove": True,
         "columns": [
           txt("colRole", "Role", "<% rv.role %>"),
           txt("colOrg", "Organization", "<% rv.org %>"),
           txt("colPosition", "Position", "<% rv.pos %>"),
           txt("colReviewed", "Last Reviewed", "<% comsAccessReview.lastReviewed(" + LOGS + ", rv.role, rv.posWid, rv.pos) %>"),
           {"type": "column", "columnId": "colStillNeeded", "label": "Still Needed", "cellTemplate": {
             "type": "checkBox", "id": "stillNeededCheckBox", "value": "<% false %>", "valuesOut": REVIEW_OUT}}]}]}]}]},
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
