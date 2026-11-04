#!/usr/bin/env python3
"""Access Review (2026-11-04): every position that holds an ECO-COMS shell role, with when ECO-COMS last
changed it and when someone last confirmed it is still needed.

- Rows: Workday's role assignments (WQL allShellAssignableRolesinTenant), one row per role, organization
  and position. Workday role assignments carry no expiry date, and the app's COMSRoleAssignment object
  is never written, so the review is based on the app's own history instead.
- History: audit records (newest first through the Graph API; tools/graphql_audit.py converts the REST
  endpoints written here). Matched by role name and position WID (or the position ID in the name).
- Confirm: tick "Still needed" and OK. Each ticked row writes one audit record, Role Assignment / REVIEW
  (per-row grid submission; unticked rows are excluded).
- Remove: Manage opens the existing Manage Role Assignment page for that role and organization.
Also writes AccessReviewCard on the RBAC Hub and registers the task. Re-run: python3 tools/build_access_review.py
"""
import json, os

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'presentation')
FOS = lambda codes: [{"code": c} for c in codes]
FOOT = {"type": "footer", "children": [{"type": "pod", "podId": "ecoComsFooter"}]}
load = lambda n: json.load(open(os.path.join(ROOT, n), encoding='utf-8'))
def save(n, d): open(os.path.join(ROOT, n), 'w', encoding='utf-8').write(json.dumps(d, indent=2, ensure_ascii=False) + '\n')

ROWS = ("list:flatten((shellRoles.data ?? []).map(r => { list:flatten((r.roleAssignments ?? []).filter(ra => { ra.organization != null && r.role != null })"
        ".map(ra => { (ra.cf_ZCF_EE_RoleAssignedToAsPositionRestrictions ?? []).map(p => { { 'role': r.role.descriptor ?? '', 'roleWid': r.role.id ?? '', "
        "'org': ra.organization.descriptor ?? '', 'orgWid': ra.organization.id ?? '', 'pos': p.descriptor ?? '', 'posWid': p.id ?? '' } }) })) }))")
LOGS = "list:flatten([auditPage0.data ?? [], auditPage1.data ?? []])"
SCRIPT = '''/* Access Review helpers (tools/build_access_review.py). logs come newest first. */
var lastWhen = function(logs, actions, roleName, posWid, posName) {
  let posId = (posName ?? '').substringBefore(' ');
  let m = logs.filter(a => { actions.contains(a.action ?? '') && (a.roleName ?? '') == roleName && ((!empty(posWid) && (a.positionWid ?? '').contains(posWid)) || (!empty(posId) && (a.positionName ?? '').contains(posId))) });
  m.size() == 0 ? '' : ('' + (m[0].timestamp ?? '')).substring(0, 10);
};

var lastChanged = function(logs, roleName, posWid, posName) {
  let d = lastWhen(logs, ['ASSIGN POSITION'], roleName, posWid, posName);
  empty(d) ? 'Not through ECO-COMS' : d;
};

var lastReviewed = function(logs, roleName, posWid, posName) {
  let d = lastWhen(logs, ['REVIEW'], roleName, posWid, posName);
  empty(d) ? 'Never' : d;
};

{
  "lastChanged": lastChanged,
  "lastReviewed": lastReviewed
}
'''
open(os.path.join(ROOT, 'scripts', 'comsAccessReview.script'), 'w', encoding='utf-8').write(SCRIPT)


def note(sid, fid, title, rid, html):
    return {"type": "layoutSection", "id": sid, "children": [{"type": "fieldSet", "id": fid, "title": title, "children": [
        {"type": "richText", "id": rid, "enabled": False,
         "value": '<span style="color:#0055B7;font-size:12px;font-weight:700">ⓘ </span><span style="color:#374151;font-size:12px">' + html + '</span>'}]}]}


txt = lambda cid, label, value: {"type": "column", "columnId": cid, "label": label, "sortableAndFilterable": "true",
    "cellTemplate": {"type": "text", "id": cid + "Text", "enabled": False, "value": value}}
OUT = lambda field, value: {"value": value, "valueOutBinding": "postReview." + field}
REVIEW_OUT = [
    OUT("timestamp", "<% date:now().format(\"yyyy-MM-dd'T'HH:mm:ss'Z'\") %>"),
    OUT("objectType", "Role Assignment"), OUT("action", "REVIEW"),
    OUT("coReferenceId", "<% rv.posWid %>"), OUT("coName", "<% rv.org %>"),
    OUT("roleName", "<% rv.role %>"), OUT("roleWid", "<% rv.roleWid %>"), OUT("orgWid", "<% rv.orgWid %>"),
    OUT("positionName", "<% rv.pos %>"), OUT("positionWid", "<% rv.posWid %>"),
    OUT("effectiveDate", "<% date:now().format('yyyy-MM-dd') %>"),
    OUT("triggeredBy", "<% selectedWorker.descriptor ?? '' %>"), OUT("changedByWid", "<% selectedWorker.id ?? '' %>"),
    OUT("details", "<% 'Access review: ' + rv.pos + ' still needs ' + rv.role + ' on ' + rv.org %>"),
]
page = {"id": "accessReview", "securityDomains": ["ManageCOMSShellOrgs"], "include": ["comsAccessReview.script"],
  "endPoints": [
    {"name": "selectedWorker", "baseUrlType": "COMMON", "url": "/workers/me", "authType": "sso", "bestEffort": "true",
     "failOnStatusCodes": FOS([400, 403, 429])},
    {"name": "shellRoles", "baseUrlType": "workday-wql", "url": "data", "authType": "sso", "bestEffort": "true",
     "wqlQuery": {"queryId": "allShellAssignableRolesinTenant"}, "failOnStatusCodes": FOS([400, 429])},
    {"name": "auditLogCount", "baseUrlType": "BUSINESS-OBJECT", "url": "/comsAuditLogs?limit=1", "authType": "sso", "failOnStatusCodes": FOS([400, 429])},
    {"name": "auditPage0", "baseUrlType": "BUSINESS-OBJECT", "authType": "sso", "isCollection": True, "failOnStatusCodes": FOS([429]),
     "url": "<% let t = auditLogCount.total ?? 0; let start = (t - 100) < 0 ? 0 : (t - 100); let cnt = t - start; '/comsAuditLogs?limit=' + (cnt > 0 ? cnt : 1) + '&offset=' + (cnt > 0 ? start : t) %>"},
    {"name": "auditPage1", "baseUrlType": "BUSINESS-OBJECT", "authType": "sso", "isCollection": True, "failOnStatusCodes": FOS([429]),
     "url": "<% let t = auditLogCount.total ?? 0; let end = (t - 100) < 0 ? 0 : (t - 100); let start = (end - 100) < 0 ? 0 : (end - 100); let cnt = end - start; '/comsAuditLogs?limit=' + (cnt > 0 ? cnt : 1) + '&offset=' + (cnt > 0 ? start : t) %>"}],
  "outboundData": {"outboundEndPoints": [
    {"name": "postReview", "baseUrlType": "BUSINESS-OBJECT", "url": "/comsAuditLogs", "httpMethod": "POST", "authType": "sso",
     "exclude": "<% stillNeededCheckBox.value != true %>", "failOnStatusCodes": FOS([400, 403, 429, 500])}]},
  "presentation": {"pageType": "EDIT", "headerSize": "STANDARD", "title": {"type": "title", "label": "ECO-COMS: Access Review"},
    "cancelOverride": {"taskId": "home"},
    "body": {"type": "basicFormLayout", "id": "accessReviewForm", "sections": [
      note("aboutSection", "aboutFieldSet", "About This Page", "aboutRichText",
        "Every position that holds an ECO-COMS shell role in Workday, with when ECO-COMS last changed it and when someone last "
        "confirmed it is still needed (from the newest 200 Audit Log records). Tick <b>Still needed</b> on the ones you checked and click "
        "<b>OK</b>: each tick is recorded in the Audit Log as a review. To take a role away, use <b>Manage</b> on that row."),
      {"type": "layoutSection", "id": "reviewSection", "children": [{"type": "fieldSet", "id": "reviewFieldSet", "title": "Role Assignments", "children": [
        {"type": "text", "id": "noRowsText", "label": "ⓘ Nothing to show", "enabled": False, "visible": "<% (" + ROWS + ").size() == 0 %>",
         "value": "No positions hold an ECO-COMS shell role right now."},
        {"type": "grid", "id": "accessReviewGrid", "label": "Positions Holding Shell Roles", "rowVariableName": "rv",
         "rows": "<% " + ROWS + " %>", "doNotAdd": True, "doNotRemove": True,
         "columns": [
           txt("colRole", "Role", "<% rv.role %>"),
           txt("colOrg", "Organization", "<% rv.org %>"),
           txt("colPosition", "Position", "<% rv.pos %>"),
           txt("colChanged", "Last Changed in ECO-COMS", "<% comsAccessReview.lastChanged(" + LOGS + ", rv.role, rv.posWid, rv.pos) %>"),
           txt("colReviewed", "Last Reviewed", "<% comsAccessReview.lastReviewed(" + LOGS + ", rv.role, rv.posWid, rv.pos) %>"),
           {"type": "column", "columnId": "colStillNeeded", "label": "Still Needed", "cellTemplate": {
             "type": "checkBox", "id": "stillNeededCheckBox", "value": "<% false %>", "valuesOut": REVIEW_OUT}},
           {"type": "column", "columnId": "colManage", "label": "Manage", "cellTemplate": {
             "type": "button", "id": "manageRoleButton", "label": "Manage", "action": "AUXILIARY", "suppressDiscardDialog": True,
             "taskReference": {"taskId": "editRoleAssignment", "parameterBindings": {
               "roleId": "<% rv.roleWid %>", "roleName": "<% rv.role %>", "orgId": "<% rv.orgWid %>", "orgName": "<% rv.org %>"}}}}]}]}]}]},
    "footer": FOOT}}
save('accessReview.pmd', page)

amd_name = [f for f in os.listdir(ROOT) if f.endswith('.amd')][0]
amd = load(amd_name)
if not any(t['id'] == 'accessReview' for t in amd['tasks']):
    amd['tasks'].append({"id": "accessReview", "routingPattern": "/accessReview", "page": {"id": "accessReview"}})
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
print('access review page, card and task written')
