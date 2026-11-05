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

SCRIPT = '''/* Application Patterns setup (tools/build_app_patterns.py). Pure functions; each check returns '' or an error.
   A format is written as on the list: PREFIX / PREFIX: Field, Field. An example is a full name: APP:PREFIX:value:value. */
var recordById = function(apps, id) {
  let m = (apps ?? []).filter(a => { a.id == id });
  empty(id) || empty(m) ? null : m[0];
};

var schemaOf = function(rec) {
  (empty(rec) || empty(rec.patternSchema)) ? null : json:parse(rec.patternSchema);
};

var parts = function(text, sep) {
  empty(text) ? [] : text.split(sep).map(p => { p.trim() }).filter(p => { !empty(p) });
};

var prefixesOf = function(formatText) {
  let t = (formatText ?? '').trim();
  t.contains(':') ? parts(t.substringBefore(':'), '/') : [];
};

var labelsOf = function(formatText) {
  let t = (formatText ?? '').trim();
  t.contains(':') ? parts(t.substringAfter(':'), ',') : [];
};

var summary = function(rec) {
  let s = schemaOf(rec);
  empty(s) ? '' : (s.prefixes.join(' / ') + ': ' + s.fields.map(f => { f.fieldLabel }).join(', '));
};

var exampleName = function(appId, rec) {
  let s = schemaOf(rec);
  empty(s) ? '' : (empty(s.example) ? ((appId ?? '') + ':' + s.prefixes[0] + ':' + s.fields.map(f => { empty(f.example) ? '*' : f.example }).join(':')) : s.example);
};

/* The same example with another application's ID in front (Copy from). */
var exampleFor = function(appId, src) {
  let ex = exampleName(src.appId, src);
  (empty(appId) || empty(ex)) ? ex : (appId + ':' + ex.substringAfter(src.appId + ':'));
};

/* Applications in Workday (X: organization codes, as on Add Shell Org) without a record here yet. */
var newAppOptions = function(orgs, apps) {
  let have = (apps ?? []).map(a => { a.appId ?? '' });
  (orgs ?? []).map(o => { let c = o.code ?? ''; c.substringAfter(':').contains(':') ? (c.substringBefore(':') + ':' + c.substringAfter(':').substringBefore(':')) : c })
    .filter(c => { c.startsWith('X:') && !have.contains(c) }).distinct().sort().map(c => { { 'id': c, 'descriptor': c } });
};

var copyOptions = function(apps, appId) {
  list:sort((apps ?? []).filter(a => { !empty(a.patternSchema) && a.appId != appId }), 'appId', true)
    .map(a => { { 'id': a.id, 'descriptor': a.appId + ' · ' + summary(a) } });
};

/* A field's rules (format, hint, blank means any): this record's field of that name, else any application's,
   else the standard Role Name rule. */
var knownField = function(label, apps, rec) {
  let own = schemaOf(rec);
  let mine = empty(own) ? [] : own.fields.filter(f => { f.fieldLabel == label });
  let others = list:flatten((apps ?? []).filter(a => { !empty(a.patternSchema) }).map(a => { json:parse(a.patternSchema).fields }))
    .filter(f => { f.fieldLabel == label });
  let std = { 'fieldLabel': label, 'regex': '[*]|[A-Z0-9][A-Z0-9_-]{0,29}[*]?', 'example': 'ANY', 'blankIsWildcard': true,
              'hint': 'Capital letters, digits, _ or - (up to 30), optionally ending in * (e.g. ANY). Leave blank for any (*).' };
  !empty(mine) ? mine[0] : (!empty(others) ? others[0] : std);
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

var formatError = function(formatText) {
  let t = (formatText ?? '').trim();
  let ps = prefixesOf(t);
  let ls = labelsOf(t);
  if (empty(t)) {
    'Enter the pattern format, e.g. ORG: Role Name.';
  } else if (!t.contains(':')) {
    'Put a colon between the prefixes and the fields, e.g. ORG: Role Name.';
  } else if (t.substringAfter(':').contains(':')) {
    'Use one colon only: prefixes before it, fields after it.';
  } else if (ps.size() == 0) {
    'Add a prefix before the colon, e.g. ORG. Separate several with /.';
  } else if (ps.filter(p => { !validate:match('[A-Z0-9_]+', p) }).size() > 0) {
    'Prefixes use capital letters, digits and _ only (e.g. ORG, CP, PATTERN).';
  } else if (ps.distinct().size() != ps.size()) {
    'Each prefix can appear only once.';
  } else if (ls.size() == 0) {
    'Add a field after the colon, e.g. Role Name. Separate several with commas.';
  } else if (ls.size() > 7) {
    'At most 7 fields: the Add Pattern form has 7 boxes.';
  } else if (ls.distinct().size() != ls.size()) {
    'Each field needs its own name.';
  } else if (ls.filter(l => { l.length() > 40 }).size() > 0) {
    'Keep each field name to 40 characters or fewer.';
  } else {
    '';
  }
};

var valuesOf = function(appId, example) {
  let rest = (example ?? '').trim().substringAfter(appId + ':');
  rest.contains(':') ? rest.substringAfter(':').split(':') : [];
};

var exampleError = function(appId, example, formatText, apps, rec) {
  let ex = (example ?? '').trim();
  let ps = prefixesOf(formatText);
  let ls = labelsOf(formatText);
  if (empty(ex)) {
    'Enter an example pattern name, e.g. ' + (empty(appId) ? 'X:APP' : appId) + ':ORG:ANY.';
  } else if (ex.contains(' ')) {
    'The example cannot contain spaces.';
  } else if (empty(appId) || formatError(formatText) != '') {
    '';
  } else if (!ex.startsWith(appId + ':')) {
    'The example must start with ' + appId + ':';
  } else {
    let pre = ex.substringAfter(appId + ':').substringBefore(':');
    let vals = valuesOf(appId, ex);
    let bad = ls.filter((l, i) => { i < vals.size() && !validate:match(knownField(l, apps, rec).regex, vals[i]) });
    if (!ps.contains(pre)) {
      'After ' + appId + ': the example needs one of the prefixes (' + ps.join(', ') + '), not ' + pre + '.';
    } else if (vals.size() != ls.size()) {
      'The example needs ' + ls.size() + ' value(s) after ' + pre + ', one for each field (' + ls.join(', ') + '). Use * for any. It has ' + vals.size() + '.';
    } else if (bad.size() > 0) {
      bad[0] + ': ' + knownField(bad[0], apps, rec).hint;
    } else {
      '';
    }
  }
};

var fieldFor = function(label, value, apps, rec) {
  let k = knownField(label, apps, rec);
  let f = { 'fieldLabel': label, 'regex': k.regex, 'hint': k.hint, 'example': empty(value) ? k.example : value, 'blankIsWildcard': k.blankIsWildcard == true };
  f;
};

var schemaJson = function(appId, formatText, example, apps, rec) {
  let vals = valuesOf(appId, example);
  let fields = labelsOf(formatText).map((l, i) => { fieldFor(l, i < vals.size() ? vals[i] : '', apps, rec) });
  json:stringify({ 'prefixes': prefixesOf(formatText), 'fields': fields, 'example': (example ?? '').trim() });
};

{
  "recordById": recordById,
  "schemaOf": schemaOf,
  "prefixesOf": prefixesOf,
  "labelsOf": labelsOf,
  "summary": summary,
  "exampleName": exampleName,
  "exampleFor": exampleFor,
  "newAppOptions": newAppOptions,
  "copyOptions": copyOptions,
  "knownField": knownField,
  "appIdError": appIdError,
  "nameError": nameError,
  "formatError": formatError,
  "exampleError": exampleError,
  "schemaJson": schemaJson
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
          "<b>Add Application</b> sets up one that isn't listed yet. Existing patterns keep their names; a new format only applies to new patterns.")}]}]},
      {"type": "layoutSection", "id": "appsSection", "children": [{"type": "fieldSet", "id": "appsFieldSet", "title": "Applications", "children": [
        {"type": "button", "id": "addApplicationButton", "label": "Add Application", "action": "PRIMARY",
         "taskReference": {"taskId": "editAppPattern"}},
        {"type": "grid", "id": "appPatternsGrid", "label": "Application Pattern Formats", "rowVariableName": "ap", "readOnly": True,
         "rows": "<% list:sort((comsApplications.data ?? []).filter(a => { !empty(a.appId) }), 'appId', true) %>",
         "columns": [
           txt("colAppId", "Application ID", "<% ap.appId ?? '' %>"),
           txt("colAppName", "Name", "<% ap.name ?? '' %>"),
           txt("colFormat", "Pattern Format", "<% comsAppSetup.summary(ap) %>"),
           txt("colExample", "Example", "<% comsAppSetup.exampleName(ap.appId, ap) %>"),
           txt("colActive", "Status", "<% ap.active == false ? 'Inactive' : 'Active' %>"),
           {"type": "column", "columnId": "colEdit", "label": "Edit", "cellTemplate": {
             "type": "button", "id": "editAppButton", "label": "Edit", "action": "AUXILIARY",
             "taskReference": {"taskId": "editAppPattern", "parameterBindings": {"recordId": "<% ap.id %>"}}}}]}]}]}]},
    "footer": FOOT}}
save('appPatternSetup.pmd', setup)

# ---- edit page: only the pattern format and its example change (product owner 2026-11-04) ----
REC = "comsAppSetup.recordById(comsApplications.data, queryParams.recordId)"
NEW = "empty(queryParams.recordId)"
CHOSEN = "(empty(appIdDropdown.value) ? '' : appIdDropdown.selectedEntries[0].id)"
APPID = f"({NEW} ? {CHOSEN} : ({REC} ?? {{'appId': ''}}).appId)"
FMT = "(formatText.value ?? '')"
EX = "(exampleText.value ?? '')"
SRC = "comsAppSetup.recordById(comsApplications.data, copyFromDropdown.selectedEntries[0].id)"
# Cross-field: the example is checked against the format and the ID, so every box that feeds it rechecks it.
CHECK_FMT = f"let ef = comsAppSetup.formatError({FMT}); if (ef != '') {{ formatText.setError(ef); }} else {{ formatText.clearError(); }}"
CHECK_EX = (f"let ee = comsAppSetup.exampleError({APPID}, {EX}, {FMT}, comsApplications.data, {REC}); "
            "if (ee != '') { exampleText.setError(ee); } else { exampleText.clearError(); }")
OUT = lambda path, value: {"outboundPath": path, "value": value}
SCHEMA = f"comsAppSetup.schemaJson({APPID}, {FMT}, {EX}, comsApplications.data, {REC})"
PREFIXES = f"comsAppSetup.prefixesOf({FMT}).join(',')"
STAMP = "date:now().format(\"yyyy-MM-dd'T'HH:mm:ss'Z'\")"
submit = ("<%\n"
          "  appIdDropdown.clearError();\n  appNameText.clearError();\n  formatText.clearError();\n  exampleText.clearError();\n"
          "  let valid = true;\n"
          f"  let e1 = comsAppSetup.appIdError({CHOSEN}, comsApplications.data, {NEW});\n"
          "  if (e1 != '') { appIdDropdown.setError(e1); valid = false; }\n"
          f"  let e2 = {NEW} ? comsAppSetup.nameError((appNameText.value ?? '').trim()) : '';\n"
          "  if (e2 != '') { appNameText.setError(e2); valid = false; }\n"
          f"  let e3 = comsAppSetup.formatError({FMT});\n"
          "  if (e3 != '') { formatText.setError(e3); valid = false; }\n"
          f"  let e4 = comsAppSetup.exampleError({APPID}, {EX}, {FMT}, comsApplications.data, {REC});\n"
          "  if (e4 != '') { exampleText.setError(e4); valid = false; }\n"
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
       OUT("orgType", f"<% {CHOSEN} %>"), OUT("orgSubtype", "X:SHELL"),
       OUT("namePrefix", f"<% {PREFIXES} %>"), OUT("patternSchema", f"<% {SCHEMA} %>"), OUT("active", "<% true %>")]},
    {"name": "patchApplication", "baseUrlType": "BUSINESS-OBJECT", "url": "<% '/comsApplications/' + (queryParams.recordId ?? '') %>",
     "httpMethod": "PATCH", "authType": "sso", "exclude": f"<% {NEW} %>", "failOnStatusCodes": FOS([400, 403, 404, 429, 500]), "values": [
       OUT("namePrefix", f"<% {PREFIXES} %>"), OUT("patternSchema", f"<% {SCHEMA} %>")]},
    {"name": "postAudit", "baseUrlType": "BUSINESS-OBJECT", "url": "/comsAuditLogs", "httpMethod": "POST", "authType": "sso",
     "failOnStatusCodes": FOS([400, 403, 429, 500]), "values": [
       OUT("timestamp", f"<% {STAMP} %>"), OUT("objectType", "Application Pattern"),
       OUT("action", f"<% {NEW} ? 'ADD' : 'UPDATE' %>"),
       OUT("coReferenceId", f"<% {APPID} %>"), OUT("coName", f"<% {APPID} %>"),
       OUT("triggeredBy", "<% selectedWorker.descriptor ?? '' %>"), OUT("changedByWid", "<% selectedWorker.id ?? '' %>"),
       OUT("details", f"<% 'Pattern format for ' + {APPID} + ': ' + {FMT}.trim() + ' (example ' + {EX}.trim() + ')' %>")]}]},
  "onSubmit": submit,
  "presentation": {"pageType": "EDIT", "headerSize": "STANDARD",
    "title": {"type": "title", "label": f"<% {NEW} ? 'ECO-COMS: Add Application' : ('ECO-COMS: Edit Pattern Format · ' + ({REC} ?? {{'appId': ''}}).appId) %>"},
    "cancelOverride": {"taskId": "appPatternSetup"},
    "body": {"type": "basicFormLayout", "id": "editAppPatternForm", "sections": [
      {"type": "layoutSection", "id": "aboutSection", "children": [{"type": "fieldSet", "id": "aboutFieldSet", "title": "About This Page", "children": [
        {"type": "richText", "id": "aboutRichText", "enabled": False, "value": INFO(
          "Write the format as on the list: the prefixes, a colon, then the fields in order, e.g. <b>CP: Subject, Course</b> "
          "(several prefixes: <b>COMM / PRIV: Role Name</b>). The example is a full pattern name with one value per field, "
          "e.g. <b>X:BPMS(AOC):CP:MECH_V:1*</b>; use * for any. <b>Copy from</b> fills both from another application. "
          "A field keeps its rules (allowed characters, hint) from a field of the same name; a new field name gets the "
          "Role Name rules. Existing patterns keep their names.")}]}]},
      {"type": "layoutSection", "id": "appSection", "children": [{"type": "fieldSet", "id": "appFieldSet", "title": "Application", "children": [
        # an existing application's ID and name are shown, not edited (patterns are named after the ID)
        {"type": "text", "id": "appIdShownText", "label": "Application ID", "enabled": False, "visible": f"<% !{NEW} %>",
         "value": f"<% ({REC} ?? {{'appId': ''}}).appId ?? '' %>"},
        {"type": "dropdown", "id": "appIdDropdown", "label": "Application ID", "visible": f"<% {NEW} %>", "required": True,
         "helpText": "Applications in Workday that aren't set up here yet.",
         "values": "<% comsAppSetup.newAppOptions(existingOrgs.data, comsApplications.data) %>",
         "onChange": f"<%\n  let e = comsAppSetup.appIdError({CHOSEN}, comsApplications.data, {NEW});\n  if (e != '') {{ self.setError(e); }} else {{ self.clearError(); }}\n  {CHECK_EX}\n%>"},
        {"type": "text", "id": "appNameText", "label": "Name", "required": f"<% {NEW} %>", "enabled": f"<% {NEW} %>",
         "value": f"<% ({REC} ?? {{'name': ''}}).name ?? '' %>",
         "onChange": "<%\n  let e = comsAppSetup.nameError((self.value ?? '').trim());\n  if (e != '') { self.setError(e); } else { self.clearError(); }\n%>"}]}]},
      {"type": "layoutSection", "id": "formatSection", "children": [{"type": "fieldSet", "id": "formatFieldSet", "title": "Pattern Format", "children": [
        {"type": "dropdown", "id": "copyFromDropdown", "label": "Copy from",
         "helpText": "Fills the format and example from another application. You can still change them.",
         "values": f"<% comsAppSetup.copyOptions(comsApplications.data, {APPID}) %>",
         "onChange": (f"<%\n  if (!empty(self.value)) {{\n    formatText.setValue(comsAppSetup.summary({SRC}));\n"
                      f"    exampleText.setValue(comsAppSetup.exampleFor({APPID}, {SRC}));\n  }}\n  {CHECK_FMT}\n  {CHECK_EX}\n%>")},
        {"type": "text", "id": "formatText", "label": "Pattern Format", "required": True, "placeholder": "e.g. CP: Subject, Course",
         "value": f"<% comsAppSetup.summary({REC}) %>",
         "onChange": f"<%\n  {CHECK_FMT}\n  {CHECK_EX}\n%>"},
        {"type": "text", "id": "exampleText", "label": "Example", "required": True, "placeholder": "e.g. X:BPMS(AOC):CP:MECH_V:1*",
         "value": f"<% let r = {REC}; empty(r) ? '' : comsAppSetup.exampleName(r.appId, r) %>",
         "onChange": f"<%\n  {CHECK_EX}\n%>"}]}]}]},
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
