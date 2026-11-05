#!/usr/bin/env python3
"""Application Patterns setup (product owner 2026-11-04: "make the application pattern schema record configurable in
its own page; change patterns for existing applications and add new ones; the form picks up patterns from this page").

Each application's pattern format already lives on its COMSApplication record (namePrefix + patternSchema JSON
{"prefixes": [...], "fields": [{fieldLabel, regex, hint, example, blankIsWildcard}]}) and the Add Pattern form
(newSchemaPattern, tools/build_schema_pattern.py) already reads it. Until now the records could only be changed through
tools/pattern_schemas.json + the seed-apps e2e task. These pages make them editable in the app:

  appPatternSetup  VIEW  list of applications with their format; Add Application, Edit per row
  editAppPattern   EDIT  ?recordId=<id> edits a record, without it adds one. OK writes the record (POST or PATCH) and an
                         audit record (Application Pattern / ADD or UPDATE), then returns to the list (flow).

Validation (onSubmit, plus live checks and a live example name):
  - Application ID (new only): required, X: + capitals/digits, optional (...) part, e.g. X:BPMS(AOC); not already set up
  - Name: required, at most 100 characters
  - Prefixes: at least one; capitals, digits and _ only; no repeats
  - Fields: 1 to 7 rows (the Add Pattern form has 7 boxes); each needs a label (unique, no ':'), a format (regex) and an
    example; the example must match the format and have no ':' or spaces
Server side, AddShellOrgPattern re-checks prefix, field count, upper case and spaces against the saved record.
Secured by Manage: COMS Application Setup (the record's own domain). Idempotent.
"""
import json, os

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'presentation')
FOS = lambda codes: [{"code": c} for c in codes]
FOOT = {"type": "footer", "children": [{"type": "pod", "podId": "ecoComsFooter"}]}
DOMAIN = "ManageCOMSApplicationSetup"
MAX_FIELDS = 7
load = lambda n: json.load(open(os.path.join(ROOT, n), encoding='utf-8'))
def save(n, d): open(os.path.join(ROOT, n), 'w', encoding='utf-8').write(json.dumps(d, indent=2, ensure_ascii=False) + '\n')

SCRIPT = '''/* Application Patterns setup (tools/build_app_patterns.py). Pure functions; each check returns '' or an error. */
var recordById = function(apps, id) {
  let m = (apps ?? []).filter(a => { a.id == id });
  empty(id) || empty(m) ? null : m[0];
};

var schemaOf = function(rec) {
  (empty(rec) || empty(rec.patternSchema)) ? null : json:parse(rec.patternSchema);
};

var fieldRows = function(rec) {
  let s = schemaOf(rec);
  empty(s) ? [{ 'fieldLabel': '', 'regex': '', 'hint': '', 'example': '', 'blankIsWildcard': false }] : s.fields;
};

var prefixText = function(rec) {
  let s = schemaOf(rec);
  empty(s) ? (empty(rec) ? '' : (rec.namePrefix ?? '')) : s.prefixes.join(', ');
};

var prefixList = function(text) {
  empty(text) ? [] : text.split(',').map(p => { p.trim() }).filter(p => { !empty(p) });
};

/* Application codes from Workday's X: organizations (as on Add Shell Org) that have no record here yet. */
var newAppOptions = function(orgs, apps) {
  let have = (apps ?? []).map(a => { a.appId ?? '' });
  (orgs ?? []).map(o => { let c = o.code ?? ''; c.substringAfter(':').contains(':') ? (c.substringBefore(':') + ':' + c.substringAfter(':').substringBefore(':')) : c })
    .filter(c => { c.startsWith('X:') && !have.contains(c) }).distinct().sort().map(c => { { 'id': c, 'descriptor': c } });
};

var appIdError = function(appId, apps, isNew) {
  if (!isNew) {
    '';
  } else if (empty(appId)) {
    'Choose the application.';
  } else if ((apps ?? []).filter(a => { a.appId == appId }).size() > 0) {
    appId + ' is already set up. Edit it from the list instead.';
  } else {
    '';
  }
};

var nameError = function(name) {
  empty(name) ? 'Name is required.' : (name.length() > 100 ? 'Keep the name to 100 characters or fewer.' : '');
};

var prefixError = function(text) {
  let ps = prefixList(text);
  if (ps.size() == 0) {
    'Add at least one prefix, e.g. ORG. Separate several with commas.';
  } else if (ps.filter(p => { !validate:match('[A-Z0-9_]+', p) }).size() > 0) {
    'Prefixes use capital letters, digits and _ only (e.g. ORG, CP, PATTERN).';
  } else if (ps.distinct().size() != ps.size()) {
    'Each prefix can appear only once.';
  } else {
    '';
  }
};

var rowError = function(r, n) {
  let where = 'Field ' + n + ': ';
  if (empty(r.fieldLabel)) {
    where + 'a label is required.';
  } else if (r.fieldLabel.contains(':')) {
    where + 'the label cannot contain a colon.';
  } else if (empty(r.regex)) {
    where + 'a format is required (a regular expression, e.g. [A-Z]{2,4}).';
  } else if (empty(r.example)) {
    where + 'an example value is required.';
  } else if (r.example.contains(':') || r.example.contains(' ')) {
    where + 'the example cannot contain a colon or spaces.';
  } else if (!validate:match(r.regex, r.example)) {
    where + 'the example ' + r.example + ' does not match the format ' + r.regex + '.';
  } else {
    '';
  }
};

var fieldsError = function(rows) {
  if (rows.size() == 0) {
    'Add at least one field.';
  } else if (rows.size() > 7) {
    'At most 7 fields: the Add Pattern form has 7 boxes.';
  } else if (rows.map(r => { r.fieldLabel }).distinct().size() != rows.size()) {
    'Each field needs its own label.';
  } else {
    let errs = rows.map((r, i) => { rowError(r, i + 1) }).filter(e => { e != '' });
    errs.size() == 0 ? '' : errs[0];
  }
};

var schemaJson = function(prefixTextValue, rows) {
  json:stringify({ 'prefixes': prefixList(prefixTextValue), 'fields': rows });
};

var exampleName = function(appId, prefixTextValue, rows) {
  let ps = prefixList(prefixTextValue);
  (empty(appId) ? 'X:APP' : appId) + ':' + (ps.size() == 0 ? 'PREFIX' : ps[0]) + ':' + rows.map(r => { empty(r.example) ? '*' : r.example }).join(':');
};

var summary = function(rec) {
  let s = schemaOf(rec);
  empty(s) ? 'No pattern format yet' : (s.prefixes.join(' / ') + ': ' + s.fields.map(f => { f.fieldLabel }).join(', '));
};

{
  "recordById": recordById,
  "schemaOf": schemaOf,
  "fieldRows": fieldRows,
  "prefixText": prefixText,
  "prefixList": prefixList,
  "newAppOptions": newAppOptions,
  "appIdError": appIdError,
  "nameError": nameError,
  "prefixError": prefixError,
  "rowError": rowError,
  "fieldsError": fieldsError,
  "schemaJson": schemaJson,
  "exampleName": exampleName,
  "summary": summary
}
'''
open(os.path.join(ROOT, 'scripts', 'comsAppSetup.script'), 'w', encoding='utf-8').write(SCRIPT)

INFO = lambda html: '<span style="color:#0055B7;font-size:12px;font-weight:700">ⓘ </span><span style="color:#374151;font-size:12px">' + html + '</span>'
APPS_EP = {"name": "comsApplications", "baseUrlType": "BUSINESS-OBJECT", "url": "/comsApplications?limit=100", "authType": "sso",
           "isCollection": True, "failOnStatusCodes": FOS([400, 403, 429])}
txt = lambda cid, label, value: {"type": "column", "columnId": cid, "label": label, "sortableAndFilterable": "true",
                                 "cellTemplate": {"type": "text", "id": cid + "Text", "enabled": False, "value": value}}

# ---- list page ----
setup = {"id": "appPatternSetup", "securityDomains": [DOMAIN], "include": ["comsAppSetup.script"],
  "endPoints": [APPS_EP],
  "presentation": {"pageType": "VIEW", "headerSize": "STANDARD", "title": {"type": "title", "label": "ECO-COMS: Application Patterns"},
    "body": {"type": "basicFormLayout", "id": "appPatternSetupForm", "sections": [
      {"type": "layoutSection", "id": "navSection", "children": [
        {"type": "button", "label": "← Home", "taskReference": {"taskId": "home"}, "action": "LINK"}]},
      {"type": "layoutSection", "id": "aboutSection", "children": [{"type": "fieldSet", "id": "aboutFieldSet", "title": "About This Page", "children": [
        {"type": "richText", "id": "aboutRichText", "enabled": False, "value": INFO(
          "Each application's shell org pattern format: its prefixes and its fields. The <b>Add Shell Org Pattern</b> form reads "
          "these, so a change here shows up there straight away. <b>Edit</b> changes an application's format; "
          "<b>Add Application</b> sets up a new one. Existing patterns keep their names; a new format only applies to new patterns.")}]}]},
      {"type": "layoutSection", "id": "appsSection", "children": [{"type": "fieldSet", "id": "appsFieldSet", "title": "Applications", "children": [
        {"type": "button", "id": "addApplicationButton", "label": "Add Application", "action": "PRIMARY",
         "taskReference": {"taskId": "editAppPattern"}},
        {"type": "grid", "id": "appPatternsGrid", "label": "Application Pattern Formats", "rowVariableName": "ap", "readOnly": True,
         "rows": "<% list:sort((comsApplications.data ?? []).filter(a => { !empty(a.appId) }), 'appId', true) %>",
         "columns": [
           txt("colAppId", "Application ID", "<% ap.appId ?? '' %>"),
           txt("colAppName", "Name", "<% ap.name ?? '' %>"),
           txt("colFormat", "Pattern Format", "<% comsAppSetup.summary(ap) %>"),
           txt("colExample", "Example", "<% let s = comsAppSetup.schemaOf(ap); empty(s) ? '' : comsAppSetup.exampleName(ap.appId, s.prefixes.join(','), s.fields) %>"),
           txt("colActive", "Status", "<% ap.active == false ? 'Inactive' : 'Active' %>"),
           {"type": "column", "columnId": "colEdit", "label": "Edit", "cellTemplate": {
             "type": "button", "id": "editAppButton", "label": "Edit", "action": "AUXILIARY",
             "taskReference": {"taskId": "editAppPattern", "parameterBindings": {"recordId": "<% ap.id %>"}}}}]}]}]}]},
    "footer": FOOT}}
save('appPatternSetup.pmd', setup)

# ---- edit page ----
REC = "comsAppSetup.recordById(comsApplications.data, queryParams.recordId)"
NEW = "empty(queryParams.recordId)"
CHOSEN = "(empty(appIdDropdown.value) ? '' : appIdDropdown.selectedEntries[0].id)"
APPID = f"({NEW} ? {CHOSEN} : ({REC} ?? {{'appId': ''}}).appId)"
ROWS = ("fieldsGrid.rows.map(r => { { 'fieldLabel': (r.childrenMap.colFieldLabel.value ?? '').trim(), "
        "'regex': (r.childrenMap.colRegex.value ?? '').trim(), 'hint': (r.childrenMap.colHint.value ?? '').trim(), "
        "'example': (r.childrenMap.colExample.value ?? '').trim(), 'blankIsWildcard': r.childrenMap.colBlank.value == true } })")
# An error OK puts on the Fields line has no box of its own to clear it, and Workday refuses OK while any error shows
# (live 2026-11-04: the page stayed stuck after the row was fixed), so every table edit clears it; OK re-checks.
PREVIEW = f"exampleNameText.setValue(comsAppSetup.exampleName({APPID}, prefixesText.value ?? '', {ROWS}));"
FIELDS_TOUCHED = "fieldsCheckText.clearError(); " + PREVIEW
cell = lambda cid, label, key, kind="text": {"type": "column", "columnId": cid, "label": label, "cellTemplate": {
    "type": kind, "id": cid + ("CheckBox" if kind == "checkBox" else "Text"),
    "value": f"<% fr.{key} ?? {'false' if kind == 'checkBox' else chr(39) * 2} %>", "onChange": "<% " + FIELDS_TOUCHED + " %>"}}
OUT = lambda path, value: {"outboundPath": path, "value": value}
SCHEMA = f"comsAppSetup.schemaJson(prefixesText.value ?? '', {ROWS})"
PREFIXES = "comsAppSetup.prefixList(prefixesText.value ?? '').join(',')"
STAMP = "date:now().format(\"yyyy-MM-dd'T'HH:mm:ss'Z'\")"
submit = ("<%\n"
          "  appIdDropdown.clearError();\n  appNameText.clearError();\n  prefixesText.clearError();\n  fieldsCheckText.clearError();\n"
          "  let valid = true;\n"
          f"  let e1 = comsAppSetup.appIdError({CHOSEN}, comsApplications.data, {NEW});\n"
          "  if (e1 != '') { appIdDropdown.setError(e1); valid = false; }\n"
          "  let e2 = comsAppSetup.nameError((appNameText.value ?? '').trim());\n"
          "  if (e2 != '') { appNameText.setError(e2); valid = false; }\n"
          "  let e3 = comsAppSetup.prefixError(prefixesText.value ?? '');\n"
          "  if (e3 != '') { prefixesText.setError(e3); valid = false; }\n"
          f"  let e4 = comsAppSetup.fieldsError({ROWS});\n"
          "  if (e4 != '') { fieldsCheckText.setError(e4); valid = false; }\n"
          "  valid;\n%>")
edit = {"id": "editAppPattern", "securityDomains": [DOMAIN], "include": ["comsAppSetup.script"],
  "endPoints": [APPS_EP,
    {"name": "existingOrgs", "baseUrlType": "workday-wql", "url": "data", "authType": "sso", "bestEffort": "true",
     "wqlQuery": {"queryId": "customOrganizations"}, "failOnStatusCodes": FOS([400, 429])},
    {"name": "selectedWorker", "baseUrlType": "COMMON", "url": "/workers/me", "authType": "sso", "bestEffort": "true", "failOnStatusCodes": FOS([400, 403, 429])}],
  "outboundData": {"outboundEndPoints": [
    {"name": "postApplication", "baseUrlType": "BUSINESS-OBJECT", "url": "/comsApplications", "httpMethod": "POST", "authType": "sso",
     "exclude": f"<% !{NEW} %>", "failOnStatusCodes": FOS([400, 403, 429, 500]), "values": [
       OUT("appId", f"<% {CHOSEN} %>"), OUT("name", "<% (appNameText.value ?? '').trim() %>"),
       OUT("description", "<% (appDescriptionText.value ?? '').trim() %>"),
       OUT("orgType", f"<% {CHOSEN} %>"), OUT("orgSubtype", "X:SHELL"),
       OUT("namePrefix", f"<% {PREFIXES} %>"), OUT("patternSchema", f"<% {SCHEMA} %>"),
       OUT("active", "<% appActiveCheckBox.value == true %>")]},
    {"name": "patchApplication", "baseUrlType": "BUSINESS-OBJECT", "url": "<% '/comsApplications/' + (queryParams.recordId ?? '') %>",
     "httpMethod": "PATCH", "authType": "sso", "exclude": f"<% {NEW} %>", "failOnStatusCodes": FOS([400, 403, 404, 429, 500]), "values": [
       OUT("name", "<% (appNameText.value ?? '').trim() %>"), OUT("description", "<% (appDescriptionText.value ?? '').trim() %>"),
       OUT("namePrefix", f"<% {PREFIXES} %>"), OUT("patternSchema", f"<% {SCHEMA} %>"),
       OUT("active", "<% appActiveCheckBox.value == true %>")]},
    {"name": "postAudit", "baseUrlType": "BUSINESS-OBJECT", "url": "/comsAuditLogs", "httpMethod": "POST", "authType": "sso",
     "failOnStatusCodes": FOS([400, 403, 429, 500]), "values": [
       OUT("timestamp", f"<% {STAMP} %>"), OUT("objectType", "Application Pattern"),
       OUT("action", f"<% {NEW} ? 'ADD' : 'UPDATE' %>"),
       OUT("coReferenceId", f"<% {APPID} %>"), OUT("coName", f"<% {APPID} %>"),
       OUT("triggeredBy", "<% selectedWorker.descriptor ?? '' %>"), OUT("changedByWid", "<% selectedWorker.id ?? '' %>"),
       OUT("details", f"<% 'Pattern format for ' + {APPID} + ': ' + {PREFIXES}.replace(',', ' / ') + ' + ' + {ROWS}.map(r => {{ r.fieldLabel }}).join(', ') + (appActiveCheckBox.value == true ? '' : ' (inactive)') %>")]}]},
  "onSubmit": submit,
  "presentation": {"pageType": "EDIT", "headerSize": "STANDARD",
    "title": {"type": "title", "label": f"<% {NEW} ? 'ECO-COMS: Add Application' : ('ECO-COMS: Edit Pattern Format · ' + ({REC} ?? {{'appId': ''}}).appId) %>"},
    "cancelOverride": {"taskId": "appPatternSetup"},
    "body": {"type": "basicFormLayout", "id": "editAppPatternForm", "sections": [
      {"type": "layoutSection", "id": "aboutSection", "children": [{"type": "fieldSet", "id": "aboutFieldSet", "title": "About This Page", "children": [
        {"type": "richText", "id": "aboutRichText", "enabled": False, "value": INFO(
          "A pattern name is <b>APPLICATION:PREFIX:field:field:…</b>. Set the prefixes the application may use and its fields, "
          "in order. Each field has a label (shown on the Add Pattern form), a format (a regular expression the value must match, "
          "e.g. <b>[A-Z]{2,4}</b>), a hint shown when a value doesn't match, and an example that matches the format. "
          "Tick <b>Blank means any</b> when a field may be left empty (it becomes *). Existing patterns keep their names. "
          "A new application also needs an organization type of the same name in Workday before its patterns can be created.")}]}]},
      {"type": "layoutSection", "id": "appSection", "children": [{"type": "fieldSet", "id": "appFieldSet", "title": "Application", "children": [
        # a new application gets an editable ID; an existing one shows it read-only (the ID can't change: patterns are named after it)
        {"type": "text", "id": "appIdShownText", "label": "Application ID", "enabled": False, "visible": f"<% !{NEW} %>",
         "value": f"<% ({REC} ?? {{'appId': ''}}).appId ?? '' %>"},
        {"type": "dropdown", "id": "appIdDropdown", "label": "Application ID", "visible": f"<% {NEW} %>",
         "helpText": "Applications in Workday that don't have a pattern format here yet.",
         "values": "<% comsAppSetup.newAppOptions(existingOrgs.data, comsApplications.data) %>",
         "onChange": f"<%\n  let e = comsAppSetup.appIdError({CHOSEN}, comsApplications.data, {NEW});\n  if (e != '') {{ self.setError(e); }} else {{ self.clearError(); }}\n  {PREVIEW}\n%>"},
        {"type": "text", "id": "appNameText", "label": "Name", "required": True, "value": f"<% ({REC} ?? {{'name': ''}}).name ?? '' %>",
         "onChange": "<%\n  let e = comsAppSetup.nameError((self.value ?? '').trim());\n  if (e != '') { self.setError(e); } else { self.clearError(); }\n%>"},
        {"type": "text", "id": "appDescriptionText", "label": "Description", "value": f"<% ({REC} ?? {{'description': ''}}).description ?? '' %>"},
        {"type": "checkBox", "id": "appActiveCheckBox", "label": "Active (shown on the Add Pattern form)",
         "value": f"<% ({REC} ?? {{'active': true}}).active != false %>"}]}]},
      {"type": "layoutSection", "id": "formatSection", "children": [{"type": "fieldSet", "id": "formatFieldSet", "title": "Pattern Format", "children": [
        {"type": "text", "id": "prefixesText", "label": "Prefixes", "required": True, "placeholder": "e.g. ORG, or CP, PRIV for several",
         "value": f"<% comsAppSetup.prefixText({REC}) %>",
         "onChange": f"<%\n  let e = comsAppSetup.prefixError(self.value ?? '');\n  if (e != '') {{ self.setError(e); }} else {{ self.clearError(); }}\n  {PREVIEW}\n%>"},
        {"type": "readOnlyText", "id": "exampleNameText", "label": "Example Pattern Name",
         # page-load value from the saved record; fields are declared below, so they can't be read here yet
         "value": f"<% let s = comsAppSetup.schemaOf({REC}); empty(s) ? '' : comsAppSetup.exampleName(({REC}).appId, s.prefixes.join(','), s.fields) %>"},
        {"type": "text", "id": "fieldsCheckText", "label": "Fields", "enabled": False,
         "value": f"<% 'Up to {MAX_FIELDS} fields, in the order they appear in the name. Add a row with +.' %>"},
        {"type": "grid", "id": "fieldsGrid", "label": "Fields", "rowVariableName": "fr",
         "onRowAdd": "<% " + FIELDS_TOUCHED + " %>", "onRowRemove": "<% " + FIELDS_TOUCHED + " %>",
         "rows": f"<% comsAppSetup.fieldRows({REC}) %>",
         "columns": [
           cell("colFieldLabel", "Label", "fieldLabel"),
           cell("colRegex", "Format (regular expression)", "regex"),
           cell("colHint", "Hint", "hint"),
           cell("colExample", "Example", "example"),
           cell("colBlank", "Blank means any (*)", "blankIsWildcard", "checkBox")]}]}]}]},
    "footer": FOOT}}
save('editAppPattern.pmd', edit)

# ---- AMD: tasks + flow back to the list ----
amd_name = [f for f in os.listdir(ROOT) if f.endswith('.amd')][0]
amd = load(amd_name)
for tid in ('appPatternSetup', 'editAppPattern'):
    if not any(t['id'] == tid for t in amd['tasks']):
        amd['tasks'].append({"id": tid, "routingPattern": "/" + tid, "page": {"id": tid}})
amd['flowDefinitions'] = [f for f in amd.get('flowDefinitions', []) if f['id'] != 'editAppPatternFlow'] + [{"id": "editAppPatternFlow", "flowSteps": [
    {"id": "editAppPatternStep", "taskId": "editAppPattern", "startsFlow": True, "transitions": [{"order": "a", "value": "appPatternSetupStep", "condition": "true"}]},
    {"id": "appPatternSetupStep", "taskId": "appPatternSetup", "endsFlow": True}]}]
save(amd_name, amd)

# ---- entry points: a pill on the hub's Shell Organizations card and on Shell Org Manager's Quick Actions ----
for card in ('HomeShellOrgActionsCard.card', 'ShellOrgQuickActionsCard.card'):
    p = os.path.join('cards', card)
    d = load(p)
    pills = d['body']['pills']
    if not any(x.get('taskReference', {}).get('taskId') == 'appPatternSetup' for x in pills):
        pills.append({"label": "Application Patterns", "taskReference": {"taskId": "appPatternSetup"}})
    save(p, d)

print('Application Patterns pages written')
