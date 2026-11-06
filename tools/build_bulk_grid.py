#!/usr/bin/env python3
"""Writes presentation/bulkRoleGrid.pmd (Bulk Edit Role Assignments, an EIB-style get/put in the app) and
registers its task and flow in the AMD.

How it works (product owner 2026-11-01: grid and Excel side by side; validate first, then apply):
- Without ?appCode the page lists the applications that have role assignments; Edit opens the grid for one.
- "Current Assignments" (pre-filled, one row per position holding a role on that application's shell orgs):
  tick Remove on the rows to take off.
- "Positions to Add" (+ adds a row): pick the role and organization, then search the position. A position that
  already holds that role there is flagged as you pick it.
- OK writes one DRAFT row per change to comsBulkRowResults (batchRef <ref>-DRAFT), a COMSBulkRun status
  record, and launches IORC_0037_XFD_SEC_Bulk_Role_Changes_From_Grid (asynchronous), which validates or applies them exactly like a file
  upload. The flow then opens Results, where a validated run has an Apply button.
- At most 50 changes per submit: each change is one request from the page, and the whole submit must finish
  within the 60-second page limit.
"""
import json, os
from app_grid import app_columns
ROOT = os.path.join(os.path.dirname(__file__), '..', 'presentation')
MAX = 50
FOS = lambda codes: [{"code": c} for c in codes]
PICKER = 'bulkRoleGridApps'   # VIEW page listing the applications (product owner 2026-11-02)
FOOT = {"type": "footer", "children": [{"type": "pod", "podId": "ecoComsFooter"}]}
WORKER = {"name": "selectedWorker", "baseUrlType": "COMMON", "url": "/workers/me", "authType": "sso", "bestEffort": "true", "failOnStatusCodes": FOS([400, 403, 429])}
def note(sid, fid, title, rid, html, color='#0055B7', mark='ⓘ'):
    return {"type": "layoutSection", "id": sid, "children": [{"type": "fieldSet", "id": fid, "title": title, "children": [
        {"type": "richText", "id": rid, "enabled": False,
         "value": '<span style="color:' + color + ';font-size:12px;font-weight:700">' + mark + ' </span><span style="color:#374151;font-size:12px">' + html + '</span>'}]}]}
txt = lambda cid, label, value: {"type": "column", "columnId": cid, "label": label,
    "cellTemplate": {"type": "text", "id": cid + "Text", "enabled": False, "value": value}}

APP = "(queryParams.appCode ?? '')"
# every position holding a role on the chosen application's shell orgs (same data as Download Template)
ROWS = ("list:flatten(list:flatten((shellRoles.data ?? []).map(r => { (r.roleAssignments ?? [])"
        ".filter(ra => { ra.organization != null && ((ra.organization.descriptor + ':').startsWith(" + APP + " + ':') || ra.organization.descriptor.startsWith(" + APP + " + ' ')) })"
        ".map(ra => { (ra.cf_ZCF_EE_RoleAssignedToAsPositionRestrictions ?? []).map(p => { { 'role': r.role.descriptor ?? '', 'roleWid': r.role.id ?? '', "
        "'org': ra.organization.descriptor ?? '', 'orgWid': ra.organization.id ?? '', 'position': p.descriptor ?? '', "
        "'positionId': (p.descriptor ?? '').substringBefore(' '), 'assigneeWid': p.id ?? '' } }) }) })))")
KEYS = "(" + ROWS + ".map(x => { x.roleWid + '|' + x.orgWid + '|' + x.positionId }))"
# every role/organization pair on the application, including pairs with no position yet
PAIRS = ("list:flatten((shellRoles.data ?? []).map(r => { (r.roleAssignments ?? [])"
         ".filter(ra => { ra.organization != null && ((ra.organization.descriptor + ':').startsWith(" + APP + " + ':') || ra.organization.descriptor.startsWith(" + APP + " + ' ')) })"
         ".map(ra => { { 'id': (r.role.id ?? '') + '|' + (ra.organization.id ?? ''), 'descriptor': (r.role.descriptor ?? '') + ' — ' + (ra.organization.descriptor ?? '') } }) }))")
# applications that have role assignments: X:<APP> from the organization names
APPS = ("list:flatten((shellRoles.data ?? []).map(r => { (r.roleAssignments ?? []).filter(ra => { ra.organization != null && ra.organization.descriptor.startsWith('X:') })"
        ".map(ra => { 'X:' + ra.organization.descriptor.substringAfter(':').substringBefore(':').substringBefore(' ') }) })).distinct().sort()")

REMOVES = "currentGrid.rows.filter(gr => { gr.childrenMap.colRemove.value == true })"
ADDS = "addGrid.rows.filter(ar => { !empty(ar.childrenMap.colPositionAdd.value) })"
ADD_KEY = "(ar.childrenMap.colRoleOrg.selectedEntries[0].id + '|' + ar.childrenMap.colPositionAdd.value[0])"
SUBMIT = """<%
  effectiveDate.clearError();
  changesText.clearError();
  confirmRealRunCheckBox.clearError();
  let valid = true;
  let removes = """ + REMOVES + """.size();
  let adds = """ + ADDS + """;
  let addKeys = adds.filter(ar => { !empty(ar.childrenMap.colRoleOrg.value) }).map(ar => { """ + ADD_KEY + """ });
  if (empty(queryParams.appCode)) {
    valid = false;
  } else if (removes + adds.size() == 0) {
    changesText.setError('No changes yet: tick Remove on a current assignment, or add a row under Positions to Add.');
    valid = false;
  } else if (removes + adds.size() > """ + str(MAX) + """) {
    changesText.setError('At most """ + str(MAX) + """ changes per submit (this one has ' + (removes + adds.size()) + '). Submit them in parts, or use the Excel template for large changes.');
    valid = false;
  } else if (addKeys.size() < adds.size()) {
    changesText.setError('Pick the role and organization on every row under Positions to Add.');
    valid = false;
  } else if (addKeys.distinct().size() < addKeys.size()) {
    changesText.setError('The same position is added twice to the same role and organization.');
    valid = false;
  } else if (addKeys.filter(k => { """ + KEYS + """.contains(k) }).size() > 0) {
    changesText.setError('A position under Positions to Add already holds that role on that organization (marked on its row).');
    valid = false;
  }
  if (empty(effectiveDate.value)) {
    effectiveDate.setError('Effective Date is required.');
    valid = false;
  } else if (!comsValidations.isWeekday(effectiveDate.value)) {
    effectiveDate.setError(comsValidations.errorWeekday());
    valid = false;
  } else if (!comsValidations.isCurrentOrFutureYear(effectiveDate.value)) {
    effectiveDate.setError(comsValidations.errorYear());
    valid = false;
  }
  if (valid && realRunCheckBox.value == true && confirmRealRunCheckBox.value != true) {
    confirmRealRunCheckBox.setError('Tick this to confirm the real run, or untick Real run to validate first.');
    valid = false;
  }
  valid;
%>"""
# the position picker checks itself as soon as both cells of its row are filled
POS_CHECK = """<%
  if (empty(self.value) || empty(roleOrgDropdown.value)) { self.clearError(); }
  else if (""" + KEYS + """.contains(roleOrgDropdown.selectedEntries[0].id + '|' + self.value[0])) {
    self.setError('This position already holds this role on this organization.');
  } else { self.clearError(); }
%>"""
PAIR_CHECK = """<%
  if (!empty(positionAddList.value) && !empty(self.value) && """ + KEYS + """.contains(self.selectedEntries[0].id + '|' + positionAddList.value[0])) {
    positionAddList.setError('This position already holds this role on this organization.');
  } else { positionAddList.clearError(); }
%>"""
SEARCH = ("<% empty(event.query) ? [] : (gridPosSearch.invoke({ 'q': event.query }).data ?? []).filter(o => { !empty(o.cf_PositionID) })"
          ".map(o => { {'id': o.cf_PositionID, 'descriptor': !empty(o.position_PositionManagement.descriptor) ? o.position_PositionManagement.descriptor : "
          "(!empty(o.cf_PositionText) ? o.cf_PositionText : o.cf_PositionID)} }) %>")
# same position search as Manage Role Assignment (quotes stripped so the text can't change the query)
POS_SEARCH = {"name": "gridPosSearch", "baseUrlType": "workday-wql", "authType": "sso", "isCollection": True, "bestEffort": "true", "deferred": "true",
  "url": "<% 'data?query=' + string:pathEncode('SELECT cf_PositionID, workdayID, position_PositionManagement, cf_PositionIsFilled, cf_PositionText FROM allPositions "
         "WHERE supervisoryOrganization is not empty AND cf_PositionText contains \\'' + q.replace('\\'', '').replace('\\\\', '') + '\\'') %>"}

DRAFT_REF = "<% batchRefHidden.value + '-DRAFT' %>"
NOW = "<% date:now().format(\"yyyy-MM-dd'T'HH:mm:ss'Z'\") %>"
def hidden(hid, value, field, ep):
    return {"type": "hidden", "id": hid, "value": value, "valueOutBinding": ep + "." + field}
def constants(prefix, ep, action):
    return [hidden(prefix + "BatchHidden", DRAFT_REF, "batchRef", ep), hidden(prefix + "ModeHidden", "<% 'DRAFT' %>", "runMode", ep),
            hidden(prefix + "ActionHidden", "<% '" + action + "' %>", "rowAction", ep), hidden(prefix + "ResultHidden", "<% 'DRAFT' %>", "result", ep),
            hidden(prefix + "TimeHidden", NOW, "timestamp", ep)]
REMOVE_FIELDS = [("roleName", "gr.role"), ("roleWid", "gr.roleWid"), ("orgName", "gr.org"), ("orgWid", "gr.orgWid"),
                 ("positionName", "gr.position"), ("positionId", "gr.positionId"), ("assigneeWid", "gr.assigneeWid")]
draft_ep = lambda name, exclude: {"name": name, "baseUrlType": "BUSINESS-OBJECT", "url": "/comsBulkRowResults", "httpMethod": "POST", "authType": "sso",
                                  "exclude": exclude, "failOnStatusCodes": FOS([400, 403, 429, 500])}
REF = "batchRefHidden.value"
MODE = "(realRunCheckBox.value == true ? 'APPLY' : 'VALIDATE')"
COUNT = "(" + REMOVES + ".size() + " + ADDS + ".size())"

page = {"id": "bulkRoleGrid", "securityDomains": ["ManageCOMSShellOrgs"], "include": ["comsValidations.script", "comsPatterns.script"],
  "endPoints": [WORKER,
    {"name": "shellRoles", "baseUrlType": "workday-wql", "url": "data", "authType": "sso", "bestEffort": "true",
     "wqlQuery": {"queryId": "allShellAssignableRolesinTenant"}, "failOnStatusCodes": FOS([400, 429])},
    # application names for the picker (same columns as Add Pattern and Shell Org Manager)
    {"name": "comsApplications", "baseUrlType": "BUSINESS-OBJECT", "url": "/comsApplications?limit=100", "authType": "sso",
     "isCollection": True, "bestEffort": "true", "failOnStatusCodes": FOS([400, 429])},
    POS_SEARCH],
  "onSubmit": SUBMIT,
  "outboundData": {"outboundEndPoints": [
    {"name": "createRun", "baseUrlType": "BUSINESS-OBJECT", "url": "/comsBulkRuns", "httpMethod": "POST", "authType": "sso",
     "failOnStatusCodes": FOS([400, 403, 429, 500]),
     "values": [{"outboundPath": "batchRef", "value": "<% " + REF + " %>"}, {"outboundPath": "source", "value": "<% 'Grid' %>"},
                {"outboundPath": "runMode", "value": "<% " + MODE + " %>"}, {"outboundPath": "status", "value": "<% 'Uploaded' %>"},
                {"outboundPath": "effectiveDate", "value": "<% effectiveDate.value.format('yyyy-MM-dd') %>"},
                {"outboundPath": "uploadedByName", "value": "<% selectedWorker.descriptor ?? '' %>"},
                {"outboundPath": "uploadedByWid", "value": "<% selectedWorker.id ?? '' %>"},
                {"outboundPath": "uploadedAt", "value": NOW},
                {"outboundPath": "changeCount", "value": "<% '' + " + COUNT + " %>"},
                {"outboundPath": "summary", "value": "<% 'Grid edit · ' + " + APP + " + ' · ' + " + COUNT + " + ' change(s)' %>"}]},
    draft_ep("removeDraft", "<% removeCheckBox.value != true %>"),
    draft_ep("addDraft", "<% empty(positionAddList.value) %>"),
    {"name": "launchGrid", "baseUrlType": "orchestration", "httpMethod": "POST", "authType": "sso", "failOnStatusCodes": FOS([400, 403, 429]),
     "url": "<% '/IORC_0037_XFD_SEC_Bulk_Role_Changes_From_Grid/launch?ref=' + " + REF + " + '&mode=' + " + MODE + " + '&effectiveDate=' + effectiveDate.value.format('yyyy-MM-dd') + '&changedBy=' + (selectedWorker.descriptor ?? '').urlEncode() + '&changedByWid=' + (selectedWorker.id ?? '') %>",
     "values": [{"outboundPath": "ref", "value": "<% " + REF + " %>"}]}]},
  "presentation": {"headerSize": "STANDARD", "title": {"type": "title", "label": "ECO-COMS: Bulk Edit Role Assignments"},
    "cancelOverride": {"taskId": "home"},
    # no application picked yet: only the picker shows, so there is nothing to submit
    "standardEditButtonsHidden": "<% empty(queryParams.appCode) %>",
    "body": {"type": "basicFormLayout", "id": "bulkGridForm", "sections": [
      {"type": "layoutSection", "id": "navSection", "children": [
        {"type": "button", "id": "homeButton", "label": "← Home", "action": "LINK", "suppressDiscardDialog": True, "taskReference": {"taskId": "home"}},
        {"type": "button", "id": "changeAppButton", "label": "Choose another application", "action": "LINK", "suppressDiscardDialog": True,
         "render": "<% !empty(queryParams.appCode) %>", "taskReference": {"taskId": PICKER}}]},
      note("aboutSection", "aboutFieldSet", "About This Page", "aboutRichText",
        "Change who holds roles on an application's shell organizations, right here. <b>Current Assignments</b> lists every position that holds a role now: "
        "tick <b>Remove</b> to take it off. Under <b>Positions to Add</b>, click + and pick the role and organization, then search for the position. "
        "OK checks every change in Workday first (<b>Validate only</b>, nothing changes) and opens Results, where <b>Apply</b> makes the changes. "
        "Tick <b>Real run</b> to apply straight away. Up to " + str(MAX) + " changes per submit; for more, use the Excel template."),
      {"type": "layoutSection", "id": "pickSection", "render": "<% empty(queryParams.appCode) %>", "children": [
        {"type": "fieldSet", "id": "pickFieldSet", "title": "Choose an Application", "children": [
          # the application list is on its own VIEW page (PICKER): edit pages draw grids with cell borders
          {"type": "text", "id": "pickText", "label": "Application", "enabled": False, "value": "<% 'No application chosen yet.' %>"},
          {"type": "button", "id": "pickAppButton", "label": "Choose an Application", "action": "PRIMARY", "suppressDiscardDialog": True,
           "taskReference": {"taskId": PICKER}}]}]},
      {"type": "layoutSection", "id": "runSection", "render": "<% !empty(queryParams.appCode) %>", "children": [
        {"type": "fieldSet", "id": "runFieldSet", "title": "Run", "children": [
          {"type": "hidden", "id": "batchRefHidden", "value": "<% 'GRID' + date:now().format('yyyyMMddHHmmss') + (selectedWorker.id ?? '').substring(0, 6) %>"},
          {"type": "text", "id": "changesText", "label": "Changes", "enabled": False,
           "value": "<% 'Tick Remove or add rows below. Up to " + str(MAX) + " changes per submit.' %>"},
          {"type": "date", "id": "effectiveDate", "label": "Effective Date", "required": True,
           "onChange": "<%\n  if (empty(self.value)) { self.clearError(); }\n  else if (!comsValidations.isWeekday(self.value)) { self.setError(comsValidations.errorWeekday()); }\n  else if (!comsValidations.isCurrentOrFutureYear(self.value)) { self.setError(comsValidations.errorYear()); }\n  else { self.clearError(); }\n%>"},
          {"type": "checkBox", "id": "realRunCheckBox", "label": "Real run (skip validation and make the changes in Workday now)", "value": "<% false %>", "onChange": "<% confirmRealRunCheckBox.setVisible(self.value == true); confirmRealRunCheckBox.clearError(); %>"},
          {"type": "checkBox", "id": "confirmRealRunCheckBox", "visible": False, "label": "I want to apply these changes without validating first", "value": "<% false %>",
           "onChange": "<% self.clearError() %>"}]}]},
      {"type": "layoutSection", "id": "currentSection", "render": "<% !empty(queryParams.appCode) %>", "children": [
        {"type": "fieldSet", "id": "currentFieldSet", "title": "Current Assignments", "children": [
          {"type": "grid", "id": "currentGrid", "rowVariableName": "gr", "doNotAdd": True, "doNotRemove": True, "label": "Current Assignments",
           "rows": "<% " + ROWS + " %>",
           "columns": [
             {"type": "column", "columnId": "colRemove", "label": "Remove",
              "cellTemplate": {"type": "checkBox", "id": "removeCheckBox", "value": "<% false %>"}},
             txt("colRole", "Role", "<% gr.role ?? '' %>"),
             txt("colOrg", "Organization", "<% gr.org ?? '' %>"),
             {"type": "column", "columnId": "colPosition", "label": "Position", "cellTemplate": {"type": "fieldSet", "id": "removeFieldSet", "children":
               [{"type": "text", "id": "positionText", "enabled": False, "value": "<% gr.position ?? '' %>"}]
               + [hidden("remove" + f[0].upper() + f[1:] + "Hidden", "<% " + e + " ?? '' %>", f, "removeDraft") for f, e in REMOVE_FIELDS]
               + constants("remove", "removeDraft", "REMOVE")}}]}]}]},
      {"type": "layoutSection", "id": "addSection", "render": "<% !empty(queryParams.appCode) %>", "children": [
        {"type": "fieldSet", "id": "addFieldSet", "title": "Positions to Add", "children": [
          {"type": "grid", "id": "addGrid", "rowVariableName": "ar", "label": "Positions to Add", "rows": "<% [] %>",
           "columns": [
             {"type": "column", "columnId": "colRoleOrg", "label": "Role and Organization", "required": True,
              "cellTemplate": {"type": "dropdown", "id": "roleOrgDropdown", "values": "<% " + PAIRS + " %>", "onChange": PAIR_CHECK,
                               "valuesOut": [
                                 {"value": "<% empty(self.value) ? '' : self.selectedEntries[0].id.substringBefore('|') %>", "valueOutBinding": "addDraft.roleWid"},
                                 {"value": "<% empty(self.value) ? '' : self.selectedEntries[0].id.substringAfter('|') %>", "valueOutBinding": "addDraft.orgWid"},
                                 {"value": "<% empty(self.value) ? '' : self.selectedEntries[0].descriptor.substringBefore(' — ') %>", "valueOutBinding": "addDraft.roleName"},
                                 {"value": "<% empty(self.value) ? '' : self.selectedEntries[0].descriptor.substringAfter(' — ') %>", "valueOutBinding": "addDraft.orgName"}]}},
             {"type": "column", "columnId": "colPositionAdd", "label": "Position", "required": True,
              "cellTemplate": {"type": "instanceList", "id": "positionAddList", "multiSelect": False, "values": "<% [] %>",
                               "onSearch": SEARCH, "onChange": POS_CHECK,
                               "valuesOut": [
                                 {"value": "<% empty(self.value) ? '' : self.value[0] %>", "valueOutBinding": "addDraft.positionId"},
                                 {"value": "<% empty(self.value) ? '' : self.selectedEntries[0].descriptor %>", "valueOutBinding": "addDraft.positionName"}]}},
             {"type": "column", "columnId": "colAddMeta", "label": "Action", "cellTemplate": {"type": "fieldSet", "id": "addFieldSetMeta", "children":
               [{"type": "text", "id": "addActionText", "enabled": False, "value": "<% 'Add' %>"},
                hidden("addAssigneeHidden", "<% '' %>", "assigneeWid", "addDraft")] + constants("add", "addDraft", "ADD")}}]}]}]}]},
    "footer": FOOT, "pageType": "EDIT"}}
open(os.path.join(ROOT, 'bulkRoleGrid.pmd'), 'w').write(json.dumps(page, indent=2, ensure_ascii=False) + '\n')

picker = {"id": PICKER, "securityDomains": ["ManageCOMSShellOrgs"], "include": ["comsPatterns.script"],
  "endPoints": [e for e in page["endPoints"] if e["name"] in ("shellRoles", "comsApplications")],
  "presentation": {"headerSize": "STANDARD", "title": {"type": "title", "label": "ECO-COMS: Bulk Edit Role Assignments"},
    "body": {"type": "basicFormLayout", "id": "bulkRoleGridAppsForm", "sections": [
      {"type": "layoutSection", "id": "navSection", "children": [
        {"type": "button", "id": "homeButton", "label": "← Home", "action": "LINK", "taskReference": {"taskId": "home"}}]},
      note("aboutSection", "aboutFieldSet", "About This Page", "aboutRichText",
        "Choose the application whose role assignments you want to change. <b>Edit</b> opens its current assignments, "
        "where you can remove positions and add new ones."),
      {"type": "layoutSection", "id": "pickSection", "children": [
        {"type": "fieldSet", "id": "pickFieldSet", "title": "Choose an Application", "children": [
          {"type": "grid", "id": "appPickGrid", "rowVariableName": "pa", "label": "Applications",
           "rows": "<% " + APPS + ".map(a => { {'appCode': a} }) %>",
           "columns": app_columns("pa", "bulkRoleGrid", {"appCode": "<% pa.appCode %>"}, "Edit", show_format=False)}]}]}]},
    "footer": FOOT, "pageType": "VIEW"}}
open(os.path.join(ROOT, PICKER + '.pmd'), 'w').write(json.dumps(picker, indent=2, ensure_ascii=False) + '\n')

amdp = os.path.join(ROOT, 'ecocomsphase_xclw_cm_sync2_vmzvxm.amd')
amd = json.load(open(amdp))
if not any(x['id'] == PICKER for x in amd['tasks']):
    amd['tasks'].append({"id": PICKER, "routingPattern": "/" + PICKER, "page": {"id": PICKER}})
if not any(x['id'] == 'bulkRoleGrid' for x in amd['tasks']):
    amd['tasks'].append({"id": "bulkRoleGrid", "routingPattern": "/bulkRoleGrid", "page": {"id": "bulkRoleGrid"}})
amd['flowDefinitions'] = [f for f in amd.get('flowDefinitions', []) if f['id'] != 'bulkRoleGridFlow'] + [
    {"id": "bulkRoleGridFlow", "flowSteps": [
        {"id": "bulkRoleGridStep", "taskId": "bulkRoleGrid", "startsFlow": True, "transitions": [{"order": "a", "value": "bulkRoleGridResultsStep", "condition": "true"}]},
        {"id": "bulkRoleGridResultsStep", "taskId": "bulkRoleResults", "endsFlow": True}]}]
open(amdp, 'w').write(json.dumps(amd, indent=2, ensure_ascii=False) + '\n')
print('bulkRoleGrid written')
