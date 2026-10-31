#!/usr/bin/env python3
"""Writes the three bulk role change pages and registers them in the AMD."""
import json, os
ROOT = os.path.join(os.path.dirname(__file__), '..', 'presentation')
FOS = lambda codes: [{"code": c} for c in codes]
FOOT = {"type": "footer", "children": [{"type": "pod", "podId": "ecoComsFooter"}]}
def save(name, d): open(os.path.join(ROOT, name + '.pmd'), 'w').write(json.dumps(d, indent=2, ensure_ascii=False) + '\n')
def note(sid, fid, title, rid, html, color='#0055B7', mark='ⓘ'):
    return {"type": "layoutSection", "id": sid, "children": [{"type": "fieldSet", "id": fid, "title": title, "children": [
        {"type": "richText", "id": rid, "enabled": False,
         "value": '<span style="color:' + color + ';font-size:12px;font-weight:700">' + mark + ' </span><span style="color:#374151;font-size:12px">' + html + '</span>'}]}]}
def nav(*buttons):
    return {"type": "layoutSection", "id": "navSection", "children": [
        {"type": "button", "id": bid, "label": label, "action": "LINK", "taskReference": {"taskId": task}} for bid, label, task in buttons]}
WORKER = {"name": "selectedWorker", "baseUrlType": "COMMON", "url": "/workers/me", "authType": "sso", "bestEffort": "true", "failOnStatusCodes": FOS([400, 403, 429])}
txt = lambda cid, label, value: {"type": "column", "columnId": cid, "label": label, "sortableAndFilterable": "true",
    "cellTemplate": {"type": "text", "id": cid + "Text", "enabled": False, "value": value}}

# ── 1. Template: one row per role, organization and position, ready to export ──
ROWS = ("<% list:flatten(list:flatten((shellRoles.data ?? []).map(r => { (r.roleAssignments ?? [])"
        ".filter(ra => { ra.organization != null && ra.organization.descriptor.startsWith(empty(queryParams.appCode) ? 'X:' : queryParams.appCode) })"
        ".map(ra => { (ra.cf_ZCF_EE_RoleAssignedToAsPositionRestrictions ?? []).map(p => { { 'role': r.role.descriptor ?? '', 'roleWid': r.role.id ?? '', "
        "'org': ra.organization.descriptor ?? '', 'orgWid': ra.organization.id ?? '', 'position': p.descriptor ?? '', "
        "'positionId': (p.descriptor ?? '').substringBefore(' '), 'assigneeWid': p.id ?? '' } }) }) }))) %>")
template = {"id": "bulkRoleTemplate", "securityDomains": ["ManageCOMSShellOrgs"],
  "endPoints": [{"name": "shellRoles", "baseUrlType": "workday-wql", "url": "data", "authType": "sso", "bestEffort": "true",
                 "wqlQuery": {"queryId": "allShellAssignableRolesinTenant"}, "failOnStatusCodes": FOS([400, 429])}],
  "presentation": {"headerSize": "STANDARD", "title": {"type": "title", "label": "ECO-COMS: Bulk Role Changes – Template"},
    "body": {"type": "basicFormLayout", "id": "bulkTemplateForm", "sections": [
      nav(("homeButton", "← Home", "home"), ("uploadButton", "Upload a file →", "bulkRoleChanges")),
      note("aboutSection", "aboutFieldSet", "How to use this template", "aboutRichText",
        "Each row is one position that currently holds a role on a shell organization. Export the grid to Excel (the export icon on the grid), then:<br/>"
        "1. In <b>Action</b>, type <b>REMOVE</b> on the rows to take a position off a role.<br/>"
        "2. To add a position, copy a row of the same role, type <b>ADD</b> in Action and put the new <b>Position ID</b> (for example P-00123) in that column. Leave Assignee WID empty on ADD rows.<br/>"
        "3. Leave Action empty on rows you don't want to change. Keep the columns in this order and don't edit the WID columns.<br/>"
        "4. Save as <b>CSV</b> (Excel: File → Save As → CSV) and upload it on the Bulk Role Changes page. At most 200 rows."),
      {"type": "layoutSection", "id": "gridSection", "children": [{"type": "fieldSet", "id": "templateFieldSet", "title": "Current role assignments", "children": [
        {"type": "grid", "id": "bulkTemplateGrid", "gridType": "LIST", "multiViewStylingEnabled": True, "autoPaging": True, "enabled": False,
         "excelExportEnabled": True, "rowVariableName": "tr", "rows": ROWS,
         "label": "<% 'Role assignments (' + size(" + ROWS[3:-3] + ") + ' positions)' %>",
         "columns": [txt("colAction", "Action", ""), txt("colRole", "Role", "<% tr.role %>"), txt("colRoleWid", "Role WID", "<% tr.roleWid %>"),
                     txt("colOrg", "Organization", "<% tr.org %>"), txt("colOrgWid", "Organization WID", "<% tr.orgWid %>"),
                     txt("colPosition", "Position", "<% tr.position %>"), txt("colPositionId", "Position ID", "<% tr.positionId %>"),
                     txt("colAssigneeWid", "Assignee WID", "<% tr.assigneeWid %>")]}]}]}]},
    "footer": FOOT, "pageType": "VIEW"}}
save('bulkRoleTemplate', template)

# ── 2. Upload: file, effective date, validate-only or real run ──
SUBMIT = """<%
  bulkFileUploader.clearError();
  effectiveDate.clearError();
  confirmRealRunCheckBox.clearError();
  let valid = true;
  if (empty(bulkFileUploader.children)) {
    bulkFileUploader.setError('Choose the CSV file to upload.');
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
MULTI = """<%
  for (var file : self.data.metadata.comsBulkUploads) {
    file.batchRef = batchRefHidden.value;
    file.runMode = realRunCheckBox.value == true ? 'APPLY' : 'VALIDATE';
    file.status = 'Uploaded';
    file.effectiveDate = effectiveDate.value.format('yyyy-MM-dd');
    file.uploadedByName = selectedWorker.descriptor ?? '';
    file.uploadedByWid = selectedWorker.id ?? '';
    file.uploadedAt = date:now().format("yyyy-MM-dd'T'HH:mm:ss'Z'");
  }
  self.data;
%>"""
upload = {"id": "bulkRoleChanges", "securityDomains": ["ManageCOMSShellOrgs"], "include": ["comsValidations.script"],
  "endPoints": [WORKER], "onSubmit": SUBMIT,
  "outboundData": {"outboundEndPoints": [
    {"name": "uploadBulkFile", "baseUrlType": "BUSINESS-OBJECT", "url": "/comsBulkUploadsCollection", "httpMethod": "POST", "authType": "sso",
     "onMultiPartSend": MULTI, "failOnStatusCodes": FOS([400, 403, 429, 500])},
    {"name": "launchBulk", "baseUrlType": "orchestration", "httpMethod": "POST", "authType": "sso",
     "url": "<% '/BulkRoleApply/launch?ref=' + batchRefHidden.value + '&mode=' + (realRunCheckBox.value == true ? 'APPLY' : 'VALIDATE') + '&effectiveDate=' + effectiveDate.value.format('yyyy-MM-dd') + '&changedBy=' + (selectedWorker.descriptor ?? '').urlEncode() + '&changedByWid=' + (selectedWorker.id ?? '') %>",
     "values": [{"outboundPath": "ref", "value": "<% batchRefHidden.value %>"}],
     "failOnStatusCodes": FOS([400, 403, 429])}]},
  "presentation": {"headerSize": "STANDARD", "title": {"type": "title", "label": "ECO-COMS: Bulk Role Changes"},
    "cancelOverride": {"taskId": "home"},
    "body": {"type": "basicFormLayout", "id": "bulkUploadForm", "sections": [
      nav(("templateButton", "← Download the template", "bulkRoleTemplate"), ("resultsButton", "View results →", "bulkRoleResults")),
      note("aboutSection", "aboutFieldSet", "How it works", "aboutRichText",
        "Upload the CSV made from the template. Run it as <b>Validate only</b> first: every row is checked and nothing changes in Workday. "
        "Then upload the same file again with <b>Real run</b> ticked: each ADD or REMOVE row is applied in Workday's Assign Roles, "
        "one row at a time, and each change is written to the Audit Log. A row that Workday rejects is recorded as FAILED and the run carries on. "
        "Both runs work in the background; the results page shows progress. At most 200 rows per file."),
      note("warningSection", "warningFieldSet", "Before a real run", "warningRichText",
        "A real run changes who holds security roles in Workday straight away. Changes that succeed are not undone if later rows fail. Validate first.",
        '#B45309', '⚠'),
      {"type": "layoutSection", "id": "formSection", "children": [{"type": "fieldSet", "id": "uploadFieldSet", "title": "Upload", "children": [
        {"type": "fileUploader", "id": "bulkFileUploader", "label": "CSV file", "fileTypes": "csv", "singular": True,
         "metadata": "<% { 'status': 'Uploaded' } %>", "valueOutBinding": "uploadBulkFile:comsBulkUploads"},
        {"type": "date", "id": "effectiveDate", "label": "Effective Date", "required": True,
         "guide": {"type": "guide", "id": "effectiveDateGuide", "title": "Effective Date", "text": "The date the role changes take effect: a weekday in this year or next. One date applies to every row in the file."},
         "onChange": "<%\n  if (empty(self.value)) { self.clearError(); }\n  else if (!comsValidations.isWeekday(self.value)) { self.setError(comsValidations.errorWeekday()); }\n  else if (!comsValidations.isCurrentOrFutureYear(self.value)) { self.setError(comsValidations.errorYear()); }\n  else { self.clearError(); }\n%>"},
        {"type": "checkBox", "id": "realRunCheckBox", "label": "Real run (make the changes in Workday)", "value": "<% false %>",
         "guide": {"type": "guide", "id": "realRunGuide", "title": "Validate only or real run", "text": "Leave this unticked to validate only: every row is checked and nothing changes. Tick it to apply the ADD and REMOVE rows in Workday."}},
        {"type": "checkBox", "id": "confirmRealRunCheckBox", "label": "I have validated this file and want to apply it", "value": "<% false %>", "onChange": "<% self.clearError() %>"},
        {"type": "hidden", "id": "batchRefHidden", "value": "<% 'BULK' + date:now().format('yyyyMMddHHmmss') + (selectedWorker.id ?? '').substring(0, 6) %>"}]}]}]},
    "footer": FOOT, "pageType": "EDIT"}}
save('bulkRoleChanges', upload)

# ── 3. Results: my uploads and the row results of one of them ──
UPL = "(list:sort((uploadPage0.data ?? []).filter(u => { (u.uploadedByWid ?? '') == (selectedWorker.id ?? '') }), 'uploadedAt', false))"
ACTIVE = "(" + UPL + ".filter(u => { ['Uploaded', 'Queued', 'Running'].contains(u.status ?? '') }))"
REF = "(!empty(queryParams.batch) ? queryParams.batch : (size(" + ACTIVE + ") > 0 ? " + ACTIVE + "[0].batchRef : (size(" + UPL + ") > 0 ? " + UPL + "[0].batchRef : '')))"
SEL = "((uploadPage0.data ?? []).filter(u => { (u.batchRef ?? '') == " + REF + " }))"
MODE = "(size(" + SEL + ") > 0 ? (" + SEL + "[0].runMode ?? '') : '')"
# a validated file that is later applied keeps its VALID rows; show the rows of its latest run only
RES = "(list:flatten([rowPage0.data ?? [], rowPage1.data ?? []]).filter(x => { (x.batchRef ?? '') == " + REF + " && (" + MODE + " == '' || (x.runMode ?? '') == " + MODE + ") }))"
cnt = lambda cond: "size(" + RES + ".filter(x => { " + cond + " }))"
results = {"id": "bulkRoleResults", "securityDomains": ["ManageCOMSShellOrgs"],
  "endPoints": [WORKER,
    {"name": "uploadCount", "baseUrlType": "BUSINESS-OBJECT", "url": "/comsBulkUploads?limit=1", "authType": "sso", "failOnStatusCodes": FOS([400, 403, 429])},
    {"name": "uploadPage0", "baseUrlType": "BUSINESS-OBJECT", "authType": "sso", "isCollection": True, "failOnStatusCodes": FOS([400, 403, 429]),
     "url": "<% let t = uploadCount.total ?? 0; let start = (t - 100) < 0 ? 0 : (t - 100); let cnt = t - start; '/comsBulkUploads?limit=' + (cnt > 0 ? cnt : 1) + '&offset=' + (cnt > 0 ? start : t) %>"},
    {"name": "rowPage0", "baseUrlType": "BUSINESS-OBJECT", "authType": "sso", "isCollection": True, "failOnStatusCodes": FOS([400, 403, 429]),
     "url": "<% '/comsBulkRowResults?limit=100&offset=0&batchRef=' + " + REF + " %>"},
    {"name": "rowPage1", "baseUrlType": "BUSINESS-OBJECT", "authType": "sso", "isCollection": True, "failOnStatusCodes": FOS([429]),
     "url": "<% '/comsBulkRowResults?limit=100&offset=100&batchRef=' + " + REF + " %>"}],
  "presentation": {"headerSize": "STANDARD", "title": {"type": "title", "label": "ECO-COMS: Bulk Role Changes – Results"},
    "body": {"type": "basicFormLayout", "id": "bulkResultsForm", "sections": [
      {"type": "layoutSection", "id": "navSection", "children": [
        {"type": "button", "id": "homeButton", "label": "← Home", "action": "LINK", "taskReference": {"taskId": "home"}},
        {"type": "button", "id": "refreshButton", "label": "↻ Refresh", "action": "LINK",
         "taskReference": {"taskId": "bulkRoleResults", "parameterBindings": {"batch": "<% " + REF + " %>"}}},
        {"type": "button", "id": "uploadButton", "label": "Upload another file", "action": "LINK", "taskReference": {"taskId": "bulkRoleChanges"}},
        {"type": "button", "id": "templateButton", "label": "Template", "action": "LINK", "taskReference": {"taskId": "bulkRoleTemplate"}}]},
      note("aboutSection", "aboutFieldSet", "About this page", "aboutRichText",
        "Your uploads, newest first, and the row results of the selected one (the newest unless you pick another). "
        "A run works in the background: while the status is Uploaded, Queued or Running, click <b>Refresh</b> in a minute to see more rows. "
        "When a validation run shows no INVALID rows, click <b>Apply</b> on that upload to run the same file for real. "
        "<b>VALID</b>/<b>INVALID</b>: validation run, nothing changed. <b>DONE</b>/<b>FAILED</b>: real run."),
      {"type": "layoutSection", "id": "summarySection", "children": [{"type": "cardContainer", "id": "bulkSummaryCardContainer", "layout": "grid", "cards": [
        {"type": "card", "cardId": "CountCard", "parameters": "<% { 'title': 'Rows processed', 'subtitle': 'Selected upload', 'countText': '' + size(" + RES + ") + ' rows' } %>"},
        {"type": "card", "cardId": "CountCard", "parameters": "<% { 'title': 'Succeeded', 'subtitle': 'DONE or VALID', 'countText': '' + " + cnt("x.result == 'DONE' || x.result == 'VALID'") + " + ' rows' } %>"},
        {"type": "card", "cardId": "CountCard", "parameters": "<% { 'title': 'Need attention', 'subtitle': 'FAILED or INVALID', 'countText': '' + " + cnt("x.result == 'FAILED' || x.result == 'INVALID'") + " + ' rows' } %>"}]}]},
      {"type": "layoutSection", "id": "uploadsSection", "children": [{"type": "fieldSet", "id": "uploadsFieldSet", "title": "My uploads", "children": [
        {"type": "grid", "id": "uploadsGrid", "gridType": "LIST", "multiViewStylingEnabled": True, "autoPaging": True, "enabled": False, "excelExportEnabled": True,
         "rowVariableName": "up", "rows": "<% " + UPL + " %>", "label": "<% 'My uploads (' + size(" + UPL + ") + ')' %>",
         "columns": [txt("colUploaded", "Uploaded", "<% (up.uploadedAt ?? '').replace('T', ' ').replace('Z', ' UTC') %>"),
                     txt("colFile", "File", "<% up.fileName ?? up.descriptor ?? '' %>"),
                     txt("colMode", "Run", "<% (up.runMode ?? '') == 'APPLY' ? 'Real run' : 'Validate only' %>"),
                     txt("colStatus", "Status", "<% up.status ?? '' %>"),
                     txt("colEffective", "Effective Date", "<% up.effectiveDate ?? '' %>"),
                     txt("colMessage", "Message", "<% up.statusMessage ?? '' %>"),
                     {"type": "column", "columnId": "colOpen", "label": "Results", "excel": {"enabled": False}, "cellTemplate": {"type": "button", "id": "openResultsButton", "label": "View", "action": "AUXILIARY",
                      "taskReference": {"taskId": "bulkRoleResults", "parameterBindings": {"batch": "<% up.batchRef ?? '' %>"}}}},
                     {"type": "column", "columnId": "colApply", "label": "Apply", "excel": {"enabled": False}, "cellTemplate": {"type": "button", "id": "applyStoredButton", "label": "Apply", "action": "AUXILIARY",
                      "taskReference": {"taskId": "bulkRoleApply", "parameterBindings": {"batch": "<% up.batchRef ?? '' %>"}}}}]}]}]},
      {"type": "layoutSection", "id": "rowsSection", "children": [{"type": "fieldSet", "id": "rowsFieldSet", "title": "<% 'Row results: ' + " + REF + " %>", "children": [
        {"type": "grid", "id": "rowResultsGrid", "gridType": "LIST", "multiViewStylingEnabled": True, "autoPaging": True, "enabled": False, "excelExportEnabled": True,
         "rowVariableName": "rr", "rows": "<% list:sort(" + RES + ", 'timestamp', true) %>", "label": "<% 'Rows (' + size(" + RES + ") + ')' %>",
         "columns": [txt("colResult", "Result", "<% rr.result ?? '' %>"), txt("colAction", "Action", "<% rr.rowAction ?? '' %>"),
                     txt("colRole", "Role", "<% rr.roleName ?? '' %>"), txt("colOrg", "Organization", "<% rr.orgName ?? '' %>"),
                     txt("colPosition", "Position", "<% (rr.positionName ?? '') != '' ? rr.positionName : (rr.positionId ?? '') %>"),
                     txt("colMessage", "Message", "<% rr.message ?? '' %>")]}]}]}]},
    "footer": FOOT, "pageType": "VIEW"}}
save('bulkRoleResults', results)

# ── 4. Apply a validated upload without uploading it again ──
B = "(queryParams.batch ?? '')"
UP = "(size(storedUpload.data ?? []) > 0 ? storedUpload.data[0] : {})"
ROWS4 = "(list:flatten([storedRows0.data ?? [], storedRows1.data ?? []]).filter(x => { (x.runMode ?? '') == 'VALIDATE' }))"
n4 = lambda r: "size(" + ROWS4 + ".filter(x => { x.result == '" + r + "' }))"
APPLY_SUBMIT = """<%
  let up = """ + UP + """;
  confirmApplyCheckBox.clearError();
  let valid = true;
  if ((up.status ?? '') != 'Validated') {
    confirmApplyCheckBox.setError('Only an upload with status Validated can be applied. This one is ' + (up.status ?? 'not found') + '.');
    valid = false;
  } else if (""" + n4('INVALID') + """ > 0) {
    confirmApplyCheckBox.setError('Fix the INVALID rows in the file and upload it again; a file with INVALID rows cannot be applied.');
    valid = false;
  } else if (""" + n4('VALID') + """ == 0) {
    confirmApplyCheckBox.setError('This upload has no VALID rows to apply.');
    valid = false;
  } else if (confirmApplyCheckBox.value != true) {
    confirmApplyCheckBox.setError('Tick this to confirm the real run.');
    valid = false;
  }
  valid;
%>"""
apply = {"id": "bulkRoleApply", "securityDomains": ["ManageCOMSShellOrgs"],
  "endPoints": [WORKER,
    {"name": "storedUpload", "baseUrlType": "BUSINESS-OBJECT", "authType": "sso", "isCollection": True, "failOnStatusCodes": FOS([400, 403, 429]),
     "url": "<% '/comsBulkUploads?limit=1&batchRef=' + " + B + " %>"},
    {"name": "storedRows0", "baseUrlType": "BUSINESS-OBJECT", "authType": "sso", "isCollection": True, "failOnStatusCodes": FOS([400, 403, 429]),
     "url": "<% '/comsBulkRowResults?limit=100&offset=0&batchRef=' + " + B + " %>"},
    {"name": "storedRows1", "baseUrlType": "BUSINESS-OBJECT", "authType": "sso", "isCollection": True, "failOnStatusCodes": FOS([429]),
     "url": "<% '/comsBulkRowResults?limit=100&offset=100&batchRef=' + " + B + " %>"}],
  "onSubmit": APPLY_SUBMIT,
  "outboundData": {"outboundEndPoints": [
    {"name": "markQueued", "baseUrlType": "BUSINESS-OBJECT", "httpMethod": "PATCH", "authType": "sso", "failOnStatusCodes": FOS([400, 403, 429]),
     "url": "<% '/comsBulkUploads/' + (" + UP + ".id ?? '') %>",
     "values": [{"outboundPath": "status", "value": "<% 'Queued' %>"}, {"outboundPath": "runMode", "value": "<% 'APPLY' %>"},
                {"outboundPath": "statusMessage", "value": "<% 'Real run requested by ' + (selectedWorker.descriptor ?? '') %>"}]},
    {"name": "launchBulk", "baseUrlType": "orchestration", "httpMethod": "POST", "authType": "sso", "failOnStatusCodes": FOS([400, 403, 429]),
     "url": "<% '/BulkRoleApply/launch?ref=' + " + B + " + '&mode=APPLY&effectiveDate=' + (" + UP + ".effectiveDate ?? '') + '&changedBy=' + (selectedWorker.descriptor ?? '').urlEncode() + '&changedByWid=' + (selectedWorker.id ?? '') %>",
     "values": [{"outboundPath": "ref", "value": "<% " + B + " %>"}]}]},
  "presentation": {"headerSize": "STANDARD", "title": {"type": "title", "label": "ECO-COMS: Bulk Role Changes – Apply"},
    "cancelOverride": {"taskId": "bulkRoleResults"},
    "body": {"type": "basicFormLayout", "id": "bulkApplyForm", "sections": [
      note("warningSection", "warningFieldSet", "Real run", "warningRichText",
        "OK applies every VALID row of this upload in Workday's Assign Roles, with the effective date chosen when the file was validated. "
        "Changes that succeed are not undone if later rows fail. Each change is written to the Audit Log.", '#B45309', '⚠'),
      {"type": "layoutSection", "id": "detailSection", "children": [{"type": "fieldSet", "id": "detailFieldSet", "title": "Upload", "children": [
        {"type": "text", "id": "fileNameText", "label": "File", "enabled": False, "value": "<% " + UP + ".fileName ?? (" + UP + ".descriptor ?? '') %>"},
        {"type": "text", "id": "batchText", "label": "Batch reference", "enabled": False, "value": "<% " + B + " %>"},
        {"type": "text", "id": "statusText", "label": "Status", "enabled": False, "value": "<% " + UP + ".status ?? 'Not found' %>"},
        {"type": "text", "id": "effectiveDateText", "label": "Effective Date", "enabled": False, "value": "<% " + UP + ".effectiveDate ?? '' %>"},
        {"type": "text", "id": "validRowsText", "label": "VALID rows (will be applied)", "enabled": False, "value": "<% '' + " + n4('VALID') + " %>"},
        {"type": "text", "id": "invalidRowsText", "label": "INVALID rows", "enabled": False, "value": "<% '' + " + n4('INVALID') + " %>"},
        {"type": "checkBox", "id": "confirmApplyCheckBox", "label": "Apply these rows in Workday now", "value": "<% false %>", "onChange": "<% self.clearError() %>"}]}]}]},
    "footer": FOOT, "pageType": "EDIT"}}
save('bulkRoleApply', apply)

# ── AMD: tasks and the upload → results flow ──
amdp = os.path.join(ROOT, 'ecocomsphase_xclw_cm_sync2_vmzvxm.amd')
amd = json.load(open(amdp))
for t in ('bulkRoleTemplate', 'bulkRoleChanges', 'bulkRoleResults', 'bulkRoleApply'):
    if not any(x['id'] == t for x in amd['tasks']):
        amd['tasks'].append({"id": t, "routingPattern": "/" + t, "page": {"id": t}})
amd['flowDefinitions'] = [f for f in amd.get('flowDefinitions', []) if f['id'] not in ('bulkRoleChangesFlow', 'bulkRoleApplyFlow')] + [
  {"id": "bulkRoleApplyFlow", "flowSteps": [
    {"id": "bulkRoleApplyStep", "taskId": "bulkRoleApply", "startsFlow": True, "transitions": [{"order": "a", "value": "bulkRoleApplyResultsStep", "condition": "true"}]},
    {"id": "bulkRoleApplyResultsStep", "taskId": "bulkRoleResults", "endsFlow": True}]},{"id": "bulkRoleChangesFlow", "flowSteps": [
    {"id": "bulkRoleChangesStep", "taskId": "bulkRoleChanges", "startsFlow": True, "transitions": [{"order": "a", "value": "bulkRoleResultsStep", "condition": "true"}]},
    {"id": "bulkRoleResultsStep", "taskId": "bulkRoleResults", "endsFlow": True}]}]
open(amdp, 'w').write(json.dumps(amd, indent=2, ensure_ascii=False) + '\n')

# ── Home: a Bulk role changes section ──
hp = os.path.join(ROOT, 'hubLanding.pmd'); hub = json.load(open(hp))
secs = hub['presentation']['body']['sections']
if not any(s.get('id') == 'bulkSection' for s in secs):
    i = [s.get('id') for s in secs].index('assignableRoleSection')
    secs.insert(i, {"type": "layoutSection", "id": "bulkSection", "children": [{"type": "fieldSet", "id": "bulkFieldSet", "title": "Bulk Role Changes", "children": [
        {"type": "richText", "id": "bulkDesc", "enabled": False, "value": "<% '<span style=\"color:#374151;font-size:13px\">Add or remove many positions on shell organization roles from one CSV file. Validate first, then run it for real.</span>' %>"},
        {"type": "button", "id": "bulkTemplateButton", "label": "Download Template", "action": "AUXILIARY", "taskReference": {"taskId": "bulkRoleTemplate"}},
        {"type": "button", "id": "bulkUploadButton", "label": "Upload File", "action": "PRIMARY", "taskReference": {"taskId": "bulkRoleChanges"}},
        {"type": "button", "id": "bulkResultsButton", "label": "View Results", "action": "AUXILIARY", "taskReference": {"taskId": "bulkRoleResults"}}]}]})
    open(hp, 'w').write(json.dumps(hub, indent=2, ensure_ascii=False) + '\n')
print('ok')
