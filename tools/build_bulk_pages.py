#!/usr/bin/env python3
"""Writes the bulk role change pages (template, template upload, upload, results, apply) and registers them in the AMD."""
import json, os
ROOT = os.path.join(os.path.dirname(__file__), '..', 'presentation')
FOS = lambda codes: [{"code": c} for c in codes]
FOOT = {"type": "footer", "children": [{"type": "pod", "podId": "ecoComsFooter"}]}
def save(name, d): open(os.path.join(ROOT, name + '.pmd'), 'w').write(json.dumps(d, indent=2, ensure_ascii=False) + '\n')
def note(sid, fid, title, rid, html, color='#0055B7', mark='ⓘ'):
    return {"type": "layoutSection", "id": sid, "children": [{"type": "fieldSet", "id": fid, "title": title, "children": [
        {"type": "richText", "id": rid, "enabled": False,
         "value": '<span style="color:' + color + ';font-size:12px;font-weight:700">' + mark + ' </span><span style="color:#374151;font-size:12px">' + html + '</span>'}]}]}
def with_card(section, card_id):
    """Adds a card under a help section's text (the ISC 'Show' pattern: fieldSet, then cards)."""
    section['children'].append({"type": "cardContainer", "id": section['id'].replace('Section', '') + "CardContainer", "layout": "grid",
                                "cards": [{"type": "card", "cardId": card_id}]})
    return section
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
                 "wqlQuery": {"queryId": "allShellAssignableRolesinTenant"}, "failOnStatusCodes": FOS([400, 429])},
                # newest published Excel template (COMSBulkTemplate); the collection is oldest first
                {"name": "templateCount", "baseUrlType": "BUSINESS-OBJECT", "url": "/comsBulkTemplates?limit=1", "authType": "sso",
                 "bestEffort": "true", "failOnStatusCodes": FOS([429])},
                {"name": "latestTemplate", "baseUrlType": "BUSINESS-OBJECT", "authType": "sso", "isCollection": True, "bestEffort": "true",
                 "failOnStatusCodes": FOS([429]),
                 # the newest 100 versions (collection is oldest first); the page shows only the newest by asOf (product owner 2026-11-02:
                 # the attachment collection returned every version despite limit=1, live 2026-11-02)
                 "url": "<% let t = templateCount.total ?? 0; '/comsBulkTemplates?limit=100&offset=' + ((t - 100) > 0 ? (t - 100) : 0) %>"}],
  "presentation": {"headerSize": "STANDARD", "title": {"type": "title", "label": "ECO-COMS: Bulk Role Changes – Template"},
    "body": {"type": "basicFormLayout", "id": "bulkTemplateForm", "sections": [
      nav(("homeButton", "← Home", "home")),
      with_card(note("aboutSection", "aboutFieldSet", "How to Use This Template", "aboutRichText",
        "<b>Easiest:</b> download the <b>Excel template</b> below. It already lists every current role assignment, checks each row as you type "
        "and tells you when the file is ready to save as CSV. Its <b>How to use</b> sheet has the steps.<br/>"
        "<b>Or</b> export the grid below to Excel (the export icon on the grid); each row is one position that holds a role on a shell organization. Then:<br/>"
        "1. In <b>Action</b>, type <b>REMOVE</b> on the rows to take a position off a role.<br/>"
        "2. To add a position, copy a row of the same role, type <b>ADD</b> in Action and put the new <b>Position ID</b> (for example P-00123) in that column. Leave Assignee WID empty on ADD rows.<br/>"
        "3. Leave Action empty on rows you don't want to change. Keep the columns in this order and don't edit the WID columns.<br/>"
        "4. Save as <b>CSV</b> (Excel: File → Save As → CSV) and upload it on the Bulk Role Changes page. Up to 1,000 ADD or REMOVE rows per file."), "BulkNextStepCard"),
      {"type": "layoutSection", "id": "excelSection", "children": [
        {"type": "fieldSet", "id": "excelFieldSet", "title": "Excel Template", "children": [
          {"type": "fileUploader", "id": "templateFileUploader", "label": "Validated Excel template", "enabled": False, "children": [
            {"type": "loop", "on": "<% (size(latestTemplate.data ?? []) == 0 ? [] : list:sort(latestTemplate.data ?? [], 'asOf', false).subList(0, 1)) %>", "as": "tf", "children": [
              {"type": "fileUploaderRow", "id": "templateFileRow", "allowRemove": False,
               "fileName": "<% tf.fileName %>", "fileType": "<% fileType:getFileType(tf.fileName) %>",
               "contentArea": [{"type": "text", "id": "templateInfoText", "label": "Version", "enabled": False,
                                "value": "<% (tf.version ?? '') + (empty(tf.asOf) ? '' : ' · assignments as of ' + tf.asOf) + (empty(tf.rowCount) ? '' : ' · ' + tf.rowCount + ' rows') %>"}],
               "attachment": {"type": "attachmentList", "attachmentAuth": "sso", "attachmentUriTemplate": "[Target]",
                              "attachmentURL": "<% 'https://api.workday.com/apps/ecocomsphase_xclw_cm_sync2_vmzvxm/v1/comsBulkTemplates/' + tf.id %>",
                              "attachmentName": "<% tf.fileName %>",
                              "instanceList": [{"action": "attachment", "descriptor": "<% tf.fileName %>",
                                                "mimeType": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "iconId": "mime_msexcel"}]}}]}]},
          {"type": "text", "id": "noTemplateText", "enabled": False, "visible": "<% size(latestTemplate.data ?? []) == 0 %>",
           "value": "No Excel template has been published in this tenant yet. Use Upload New Template Version, or export the grid below."}]},
        {"type": "button", "id": "uploadTemplateButton", "label": "Upload New Template Version", "action": "AUXILIARY",
         "taskReference": {"taskId": "bulkTemplateUpload"}}]},
      {"type": "layoutSection", "id": "gridSection", "children": [{"type": "fieldSet", "id": "templateFieldSet", "title": "Current Role Assignments", "children": [
        {"type": "grid", "id": "bulkTemplateGrid", "gridType": "LIST", "multiViewStylingEnabled": True, "autoPaging": True, "enabled": False,
         "excelExportEnabled": True, "rowVariableName": "tr", "rows": ROWS,
         "label": "Role Assignments",
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
    bulkFileUploader.setError('Choose the CSV file to upload. Using the Excel template? Open its Role Changes sheet and save it as CSV (File → Save As → CSV) first.');
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
     "url": "<% '/IORC_0037_XFD_SEC_Bulk_Role_Changes_From_CSV/launch?ref=' + batchRefHidden.value + '&mode=' + (realRunCheckBox.value == true ? 'APPLY' : 'VALIDATE') + '&effectiveDate=' + effectiveDate.value.format('yyyy-MM-dd') + '&changedBy=' + (selectedWorker.descriptor ?? '').urlEncode() + '&changedByWid=' + (selectedWorker.id ?? '') %>",
     "values": [{"outboundPath": "ref", "value": "<% batchRefHidden.value %>"}],
     "failOnStatusCodes": FOS([400, 403, 429])}]},
  "presentation": {"headerSize": "STANDARD", "title": {"type": "title", "label": "ECO-COMS: Bulk Role Changes"},
    "cancelOverride": {"taskId": "home"},
    "body": {"type": "basicFormLayout", "id": "bulkUploadForm", "sections": [
      nav(("homeButton", "← Home", "home")),
      with_card(note("aboutSection", "aboutFieldSet", "How It Works", "aboutRichText",
        "Upload the CSV made from the template. Run it as <b>Validate only</b> first: every row is checked and nothing changes in Workday. "
        "Then upload the same file again with <b>Real run</b> ticked: each ADD or REMOVE row is applied in Workday's Assign Roles, "
        "one row at a time, and each change is written to the Audit Log. A row that Workday rejects is recorded as FAILED and the run carries on. "
        "Both runs work in the background; the results page shows progress. Up to 1,000 ADD or REMOVE rows per file; unchanged rows don't count."), "BulkRelatedCard"),
      note("warningSection", "warningFieldSet", "Before You Submit", "warningRichText",
        "A real run changes who holds security roles in Workday straight away. Changes that succeed are not undone if later rows fail. Validate first.",
        '#B45309', '⚠'),
      {"type": "layoutSection", "id": "formSection", "children": [{"type": "fieldSet", "id": "uploadFieldSet", "title": "Upload", "children": [
        {"type": "fileUploader", "id": "bulkFileUploader", "label": "CSV file (from the Excel template: File → Save As → CSV, with the Role Changes sheet open)", "fileTypes": "csv", "singular": True,
         "fileTypesErrorMessage": "Upload a .csv file. In the Excel template, open the Role Changes sheet, then File → Save As → CSV (Comma delimited), and upload that file.",
         "metadata": "<% { 'status': 'Uploaded' } %>", "valueOutBinding": "uploadBulkFile:comsBulkUploads"},
        {"type": "date", "id": "effectiveDate", "label": "Effective Date", "required": True,
         "guide": {"type": "guide", "id": "effectiveDateGuide", "title": "Effective Date", "text": "The date the role changes take effect: a weekday in this year or next. One date applies to every row in the file."},
         "onChange": "<%\n  if (empty(self.value)) { self.clearError(); }\n  else if (!comsValidations.isWeekday(self.value)) { self.setError(comsValidations.errorWeekday()); }\n  else if (!comsValidations.isCurrentOrFutureYear(self.value)) { self.setError(comsValidations.errorYear()); }\n  else { self.clearError(); }\n%>"},
        {"type": "checkBox", "id": "realRunCheckBox", "label": "Real run (make the changes in Workday)", "value": "<% false %>", "onChange": "<% confirmRealRunCheckBox.setVisible(self.value == true); confirmRealRunCheckBox.clearError(); %>",
         "guide": {"type": "guide", "id": "realRunGuide", "title": "Validate only or real run", "text": "Leave this unticked to validate only: every row is checked and nothing changes. Tick it to apply the ADD and REMOVE rows in Workday."}},
        {"type": "checkBox", "id": "confirmRealRunCheckBox", "visible": False, "label": "I have validated this file and want to apply it", "value": "<% false %>", "onChange": "<% self.clearError() %>"},
        {"type": "hidden", "id": "batchRefHidden", "value": "<% 'BULK' + date:now().format('yyyyMMddHHmmss') + (selectedWorker.id ?? '').substring(0, 6) %>"}]}]}]},
    "footer": FOOT, "pageType": "EDIT"}}
save('bulkRoleChanges', upload)

# ── 2b. Upload a new version of the Excel template (COMSBulkTemplate) ──
TEMPLATE_MULTI = """<%
  for (var file : self.data.metadata.comsBulkTemplates) {
    file.version = versionText.value;
    file.notes = notesText.value ?? '';
    file.uploadedByName = selectedWorker.descriptor ?? '';
    file.uploadedAt = date:now().format("yyyy-MM-dd'T'HH:mm:ss'Z'");
  }
  self.data;
%>"""
template_upload = {"id": "bulkTemplateUpload", "securityDomains": ["ManageCOMSShellOrgs"],
  "endPoints": [WORKER],
  "outboundData": {"outboundEndPoints": [
    {"name": "uploadTemplateFile", "baseUrlType": "BUSINESS-OBJECT", "url": "/comsBulkTemplatesCollection", "httpMethod": "POST", "authType": "sso",
     "onMultiPartSend": TEMPLATE_MULTI, "failOnStatusCodes": FOS([400, 403, 429, 500])}]},
  "presentation": {"headerSize": "STANDARD", "title": {"type": "title", "label": "ECO-COMS: Upload Bulk Template Version"},
    "cancelOverride": {"taskId": "bulkRoleTemplate"},
    "body": {"type": "basicFormLayout", "id": "templateUploadForm", "sections": [
      nav(("backButton", "← Download Template", "bulkRoleTemplate")),
      note("aboutSection", "aboutFieldSet", "About This Page", "aboutRichText",
        "Publish a new version of the validated Excel template. Everyone who opens Download Template gets the newest version. "
        "Build it with <b>tools/publish_template.js</b> (pre-filled with every current role assignment) or <b>tools/build_bulk_xlsx.py</b> (blank). "
        "Older versions stay stored."),
      {"type": "layoutSection", "id": "formSection", "children": [{"type": "fieldSet", "id": "templateUploadFieldSet", "title": "Template", "children": [
        {"type": "fileUploader", "id": "templateUploader", "label": "Excel file", "fileTypes": "xlsx", "singular": True, "required": True,
         "metadata": "<% { 'version': '' } %>", "valueOutBinding": "uploadTemplateFile:comsBulkTemplates"},
        {"type": "text", "id": "versionText", "label": "Version", "required": True, "value": "<% 'v' + date:now().format('yyyy-MM-dd') %>"},
        {"type": "text", "id": "notesText", "label": "Notes"}]}]}]},
    "footer": FOOT, "pageType": "EDIT"}}
save('bulkTemplateUpload', template_upload)

# ── 3. Results: my uploads and the row results of one of them ──
UPL = "(list:sort(list:flatten([uploadPage0.data ?? [], runPage0.data ?? []]).filter(u => { (u.uploadedByWid ?? '') == (selectedWorker.id ?? '') }), 'uploadedAt', false))"
ACTIVE = "(" + UPL + ".filter(u => { ['Uploaded', 'Queued', 'Running'].contains(u.status ?? '') }))"
REF = "(!empty(queryParams.batch) ? queryParams.batch : (size(" + ACTIVE + ") > 0 ? " + ACTIVE + "[0].batchRef : (size(" + UPL + ") > 0 ? " + UPL + "[0].batchRef : '')))"
SEL = "(list:flatten([uploadPage0.data ?? [], runPage0.data ?? []]).filter(u => { (u.batchRef ?? '') == " + REF + " }))"
MODE = "(size(" + SEL + ") > 0 ? (" + SEL + "[0].runMode ?? '') : '')"
# a validated file that is later applied keeps its VALID rows; show the rows of its latest run only
RES = "(list:flatten([rowPage0.data ?? [], rowPage1.data ?? []]).filter(x => { (x.batchRef ?? '') == " + REF + " && (" + MODE + " == '' || (x.runMode ?? '') == " + MODE + ") }))"
rows_text = lambda e: "'' + " + e + " + (" + e + " == 1 ? ' row' : ' rows')"
cnt = lambda cond: "size(" + RES + ".filter(x => { " + cond + " }))"
results = {"id": "bulkRoleResults", "securityDomains": ["ManageCOMSShellOrgs"],
  "endPoints": [WORKER,
    {"name": "uploadCount", "baseUrlType": "BUSINESS-OBJECT", "url": "/comsBulkUploads?limit=1", "authType": "sso", "failOnStatusCodes": FOS([400, 403, 429])},
    {"name": "uploadPage0", "baseUrlType": "BUSINESS-OBJECT", "authType": "sso", "isCollection": True, "failOnStatusCodes": FOS([400, 403, 429]),
     "url": "<% let t = uploadCount.total ?? 0; let start = (t - 100) < 0 ? 0 : (t - 100); let cnt = t - start; '/comsBulkUploads?limit=' + (cnt > 0 ? cnt : 1) + '&offset=' + (cnt > 0 ? start : t) %>"},
    # grid edits (COMSBulkRun, from Bulk Edit Role Assignments), newest 100
    {"name": "runCount", "baseUrlType": "BUSINESS-OBJECT", "url": "/comsBulkRuns?limit=1", "authType": "sso", "failOnStatusCodes": FOS([403, 429])},
    {"name": "runPage0", "baseUrlType": "BUSINESS-OBJECT", "authType": "sso", "isCollection": True, "failOnStatusCodes": FOS([403, 429]),
     "url": "<% let t = runCount.total ?? 0; let start = (t - 100) < 0 ? 0 : (t - 100); let cnt = t - start; '/comsBulkRuns?limit=' + (cnt > 0 ? cnt : 1) + '&offset=' + (cnt > 0 ? start : t) %>"},
    {"name": "rowPage0", "baseUrlType": "BUSINESS-OBJECT", "authType": "sso", "isCollection": True, "failOnStatusCodes": FOS([400, 403, 429]),
     "url": "<% '/comsBulkRowResults?limit=100&offset=0&batchRef=' + " + REF + " %>"},
    {"name": "rowPage1", "baseUrlType": "BUSINESS-OBJECT", "authType": "sso", "isCollection": True, "failOnStatusCodes": FOS([429]),
     "url": "<% '/comsBulkRowResults?limit=100&offset=100&batchRef=' + " + REF + " %>"}],
  "presentation": {"headerSize": "STANDARD", "title": {"type": "title", "label": "ECO-COMS: Bulk Role Changes – Results"},
    "body": {"type": "basicFormLayout", "id": "bulkResultsForm", "sections": [
      {"type": "layoutSection", "id": "navSection", "children": [
        {"type": "button", "id": "homeButton", "label": "← Home", "action": "LINK", "taskReference": {"taskId": "home"}}]},
      note("aboutSection", "aboutFieldSet", "About This Page", "aboutRichText",
        "Your uploads and grid edits, newest first, and the row results of the selected one (the newest unless you pick another). "
        "A run works in the background: while the status is Uploaded, Queued or Running, click <b>Refresh</b> in a minute to see more rows. "
        "When a validation run shows no INVALID rows, click <b>Apply</b> on that upload to run the same file for real. "
        "<b>VALID</b>/<b>INVALID</b>: validation run, nothing changed. <b>DONE</b>/<b>FAILED</b>: real run."),
      {"type": "layoutSection", "id": "summarySection", "children": [{"type": "cardContainer", "id": "bulkSummaryCardContainer", "layout": "grid", "cards": [
        {"type": "card", "cardId": "CountCard", "parameters": "<% { 'title': 'Succeeded', 'subtitle': 'DONE or VALID', 'countText': '' + " + cnt("x.result == 'DONE' || x.result == 'VALID'") + " + ' of ' + " + rows_text("size(" + RES + ")") + " } %>"},
        {"type": "card", "cardId": "CountCard", "parameters": "<% { 'title': 'Need Attention', 'subtitle': 'FAILED or INVALID', 'countText': '' + " + cnt("x.result == 'FAILED' || x.result == 'INVALID'") + " + ' of ' + " + rows_text("size(" + RES + ")") + " } %>"},
        {"type": "card", "cardId": "BulkActionsPillCard", "parameters": "<% { 'batch': " + REF + " } %>"}]}]},
      {"type": "layoutSection", "id": "uploadsSection", "children": [{"type": "fieldSet", "id": "uploadsFieldSet", "title": "My Uploads", "children": [
        {"type": "grid", "id": "uploadsGrid", "gridType": "LIST", "multiViewStylingEnabled": True, "autoPaging": True, "enabled": False, "excelExportEnabled": True,
         "rowVariableName": "up", "rows": "<% " + UPL + " %>", "label": "My Uploads",
         "columns": [txt("colUploaded", "Uploaded", "<% (up.uploadedAt ?? '').replace('T', ' ').replace('Z', ' UTC') %>"),
                     txt("colFile", "File or Edit", "<% up.fileName ?? (up.summary ?? (up.descriptor ?? '')) %>"),
                     txt("colMode", "Run", "<% (up.runMode ?? '') == 'APPLY' ? 'Real run' : 'Validate only' %>"),
                     txt("colStatus", "Status", "<% up.status ?? '' %>"),
                     txt("colEffective", "Effective Date", "<% up.effectiveDate ?? '' %>"),
                     txt("colMessage", "Message", "<% up.statusMessage ?? '' %>"),
                     {"type": "column", "columnId": "colOpen", "label": "Results", "excel": {"enabled": False}, "cellTemplate": {"type": "button", "id": "openResultsButton", "label": "View", "action": "AUXILIARY",
                      "taskReference": {"taskId": "bulkRoleResults", "parameterBindings": {"batch": "<% up.batchRef ?? '' %>"}}}},
                     {"type": "column", "columnId": "colApply", "label": "Apply", "excel": {"enabled": False}, "cellTemplate": {"type": "fieldSet", "id": "applyFieldSet", "children": [
                        {"type": "button", "id": "applyStoredButton", "label": "Apply", "action": "AUXILIARY", "visible": "<% (up.status ?? '') == 'Validated' %>",
                         "taskReference": {"taskId": "bulkRoleApply", "parameterBindings": {"batch": "<% up.batchRef ?? '' %>"}}}]}}]}]}]},
      {"type": "layoutSection", "id": "rowsSection", "children": [{"type": "fieldSet", "id": "rowsFieldSet", "title": "<% 'Row results: ' + " + REF + " %>", "children": [
        {"type": "grid", "id": "rowResultsGrid", "gridType": "LIST", "multiViewStylingEnabled": True, "autoPaging": True, "enabled": False, "excelExportEnabled": True,
         "rowVariableName": "rr", "rows": "<% list:sort(" + RES + ", 'timestamp', true) %>", "label": "Rows",
         "columns": [txt("colResult", "Result", "<% rr.result ?? '' %>"), txt("colAction", "Action", "<% rr.rowAction ?? '' %>"),
                     txt("colRole", "Role", "<% rr.roleName ?? '' %>"), txt("colOrg", "Organization", "<% rr.orgName ?? '' %>"),
                     txt("colPosition", "Position", "<% (rr.positionName ?? '') != '' ? rr.positionName : (rr.positionId ?? '') %>"),
                     txt("colRowMessage", "Message", "<% rr.message ?? '' %>")]}]}]}]},
    "footer": FOOT, "pageType": "VIEW"}}
save('bulkRoleResults', results)
for cid, title, pills in [("BulkNextStepCard", "Next Step", [("Upload a file", "bulkRoleChanges"), ("Edit in the app", "bulkRoleGridApps"), ("View results", "bulkRoleResults")]),
                          ("BulkRelatedCard", "Related", [("Edit in the app", "bulkRoleGridApps"), ("Download template", "bulkRoleTemplate"), ("View results", "bulkRoleResults")])]:
    open(os.path.join(ROOT, 'cards', cid + '.card'), 'w').write(json.dumps({"id": cid, "header": {"title": title, "icon": "wd-accent-checkmarked-page"},
        "body": {"type": "pillCard", "pills": [{"label": l, "taskReference": {"taskId": t}} for l, t in pills]}}, indent=2, ensure_ascii=False) + '\n')
actions_card = {"id": "BulkActionsPillCard", "parameters": ["batch"],
  "header": {"title": "Actions", "subtitle": "Refresh while a run is in progress", "icon": "wd-accent-checkmarked-page"},
  "body": {"type": "pillCard", "pills": [
    {"label": "↻ Refresh", "taskReference": {"taskId": "bulkRoleResults", "parameterBindings": {"batch": '<% batch ?? "" %>'}}},
    {"label": "Upload another file", "taskReference": {"taskId": "bulkRoleChanges"}},
    {"label": "Edit in the app", "taskReference": {"taskId": "bulkRoleGridApps"}},
    {"label": "Download template", "taskReference": {"taskId": "bulkRoleTemplate"}}]}}
open(os.path.join(ROOT, 'cards', 'BulkActionsPillCard.card'), 'w').write(json.dumps(actions_card, indent=2, ensure_ascii=False) + '\n')

# ── 4. Apply a validated upload without uploading it again ──
B = "(queryParams.batch ?? '')"
UP = "(size(storedUpload.data ?? []) > 0 ? storedUpload.data[0] : (size(storedRun.data ?? []) > 0 ? storedRun.data[0] : {}))"
GRIDRUN = "(size(storedUpload.data ?? []) == 0 && size(storedRun.data ?? []) > 0)"
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
    {"name": "storedRun", "baseUrlType": "BUSINESS-OBJECT", "authType": "sso", "isCollection": True, "failOnStatusCodes": FOS([400, 403, 429]),
     "url": "<% '/comsBulkRuns?limit=1&batchRef=' + " + B + " %>"},
    {"name": "storedRows0", "baseUrlType": "BUSINESS-OBJECT", "authType": "sso", "isCollection": True, "failOnStatusCodes": FOS([400, 403, 429]),
     "url": "<% '/comsBulkRowResults?limit=100&offset=0&batchRef=' + " + B + " %>"},
    {"name": "storedRows1", "baseUrlType": "BUSINESS-OBJECT", "authType": "sso", "isCollection": True, "failOnStatusCodes": FOS([429]),
     "url": "<% '/comsBulkRowResults?limit=100&offset=100&batchRef=' + " + B + " %>"}],
  "onSubmit": APPLY_SUBMIT,
  "outboundData": {"outboundEndPoints": [
    {"name": "markQueued", "baseUrlType": "BUSINESS-OBJECT", "httpMethod": "PATCH", "authType": "sso", "failOnStatusCodes": FOS([400, 403, 429]),
     "url": "<% (" + GRIDRUN + " ? '/comsBulkRuns/' : '/comsBulkUploads/') + (" + UP + ".id ?? '') %>",
     "values": [{"outboundPath": "status", "value": "<% 'Queued' %>"}, {"outboundPath": "runMode", "value": "<% 'APPLY' %>"},
                {"outboundPath": "statusMessage", "value": "<% 'Real run requested by ' + (selectedWorker.descriptor ?? '') %>"}]},
    {"name": "launchBulk", "baseUrlType": "orchestration", "httpMethod": "POST", "authType": "sso", "failOnStatusCodes": FOS([400, 403, 429]),
     "url": "<% (" + GRIDRUN + " ? '/IORC_0037_XFD_SEC_Bulk_Role_Changes_From_Grid' : '/IORC_0037_XFD_SEC_Bulk_Role_Changes_From_CSV') + '/launch?ref=' + " + B + " + '&mode=APPLY&effectiveDate=' + (" + UP + ".effectiveDate ?? '') + '&changedBy=' + (selectedWorker.descriptor ?? '').urlEncode() + '&changedByWid=' + (selectedWorker.id ?? '') %>",
     "values": [{"outboundPath": "ref", "value": "<% " + B + " %>"}]}]},
  "presentation": {"headerSize": "STANDARD", "title": {"type": "title", "label": "ECO-COMS: Bulk Role Changes – Apply"},
    "cancelOverride": {"taskId": "bulkRoleResults"},
    "body": {"type": "basicFormLayout", "id": "bulkApplyForm", "sections": [
      {"type": "layoutSection", "id": "navSection", "children": [
        {"type": "button", "id": "resultsButton", "label": "← Bulk Role Changes – Results", "action": "LINK", "suppressDiscardDialog": True,
         "taskReference": {"taskId": "bulkRoleResults", "parameterBindings": {"batch": "<% " + B + " %>"}}}]},
      note("warningSection", "warningFieldSet", "Before You Submit", "warningRichText",
        "OK applies every VALID row of this upload in Workday's Assign Roles, with the effective date chosen when the file was validated. "
        "Changes that succeed are not undone if later rows fail. Each change is written to the Audit Log.", '#B45309', '⚠'),
      {"type": "layoutSection", "id": "detailSection", "children": [{"type": "fieldSet", "id": "detailFieldSet", "title": "Upload", "children": [
        {"type": "text", "id": "fileNameText", "label": "File or Edit", "enabled": False, "value": "<% " + UP + ".fileName ?? (" + UP + ".summary ?? (" + UP + ".descriptor ?? '')) %>"},
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
for t in ('bulkRoleTemplate', 'bulkRoleChanges', 'bulkRoleResults', 'bulkRoleApply', 'bulkTemplateUpload'):
    if not any(x['id'] == t for x in amd['tasks']):
        amd['tasks'].append({"id": t, "routingPattern": "/" + t, "page": {"id": t}})
amd['flowDefinitions'] = [f for f in amd.get('flowDefinitions', []) if f['id'] not in ('bulkRoleChangesFlow', 'bulkRoleApplyFlow', 'bulkTemplateUploadFlow')] + [
    {"id": "bulkTemplateUploadFlow", "flowSteps": [
    {"id": "bulkTemplateUploadStep", "taskId": "bulkTemplateUpload", "startsFlow": True, "transitions": [{"order": "a", "value": "bulkTemplateDownloadStep", "condition": "true"}]},
    {"id": "bulkTemplateDownloadStep", "taskId": "bulkRoleTemplate", "endsFlow": True}]},
  {"id": "bulkRoleApplyFlow", "flowSteps": [
    {"id": "bulkRoleApplyStep", "taskId": "bulkRoleApply", "startsFlow": True, "transitions": [{"order": "a", "value": "bulkRoleApplyResultsStep", "condition": "true"}]},
    {"id": "bulkRoleApplyResultsStep", "taskId": "bulkRoleResults", "endsFlow": True}]},{"id": "bulkRoleChangesFlow", "flowSteps": [
    {"id": "bulkRoleChangesStep", "taskId": "bulkRoleChanges", "startsFlow": True, "transitions": [{"order": "a", "value": "bulkRoleResultsStep", "condition": "true"}]},
    {"id": "bulkRoleResultsStep", "taskId": "bulkRoleResults", "endsFlow": True}]}]
open(amdp, 'w').write(json.dumps(amd, indent=2, ensure_ascii=False) + '\n')

# Home's Bulk Role Changes actions are the HomeBulkActionsCard (tools/build_filter_pills.py).
print('ok')

# keep the 'Nothing to show' messages that tools/add_empty_messages.py adds to the results page
import subprocess, sys
subprocess.run([sys.executable, os.path.join(os.path.dirname(__file__), 'add_empty_messages.py')], check=True)

# final UI polish pass (grid labels, About ⓘ, ...); see tools/polish.py
subprocess.run([sys.executable, os.path.join(os.path.dirname(__file__), 'polish.py')], check=True)
