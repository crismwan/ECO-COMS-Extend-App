#!/usr/bin/env python3
"""Schema-driven Add Pattern page (newSchemaPattern) for every application, Clockwork included.

Architect's brief: the Appian COMS was built for one shape of pattern; the rebuild is schema-driven, so a
new tool is a new application record, not a new page. Each COMSApplication record (seeded from
tools/pattern_schemas.json by the e2e task seed-apps-apply) holds:
  namePrefix     allowed prefixes, comma-separated (the orchestration checks these)
  patternSchema  JSON {"prefixes": [...], "fields": [{fieldLabel, regex, hint, example, blankIsWildcard}]}
The page has up to MAX_FIELDS generic fields; labels, examples, visibility and checks come from the
selected application's schema at page load (?appCode=...). Without ?appCode it lists every application
code in Workday plus every configured record, with its pattern format.

Clockwork moved onto this page on 2026-11-02 (product owner: "match all applications"); its old wizard
(createShellOrgPatternWizard / newShellOrgPattern) was retired.
Server side, AddShellOrgPattern re-checks prefix, field count, upper case and spaces
(tools/patch_pattern_orchestrations.py).
"""
import json, os
from app_grid import app_columns
ROOT = os.path.join(os.path.dirname(__file__), '..', 'presentation')
MAX_FIELDS = 7
FOS = lambda codes: [{"code": c} for c in codes]
PICKER = 'schemaPatternApps'   # VIEW page listing the applications (product owner 2026-11-02: match Shell Org Manager)
FOOT = {"type": "footer", "children": [{"type": "pod", "podId": "ecoComsFooter"}]}

APPC = "(queryParams.appCode ?? '')"
SCH = "comsPatterns.schemaFor(comsApplications.data, queryParams.appCode)"
FIELD = lambda i: f"patternField{i + 1}Text"
VALUES = "[" + ", ".join(f"{FIELD(i)}.value" for i in range(MAX_FIELDS)) + "]"
PREFIX = (f"(comsPatterns.prefixCount({SCH}) > 1 ? (empty(prefixDropdown.value) ? '' : prefixDropdown.selectedEntries[0].id)"
          f" : comsPatterns.firstPrefix({SCH}))")
NAME = f"comsPatterns.buildName({APPC}, {PREFIX}, {SCH}, {VALUES})"


def note(sid, fid, title, rid, html, color='#0055B7', mark='ⓘ', render=None):
    sec = {"type": "layoutSection", "id": sid, "children": [{"type": "fieldSet", "id": fid, "title": title, "children": [
        {"type": "richText", "id": rid, "enabled": False,
         "value": '<span style="color:' + color + ';font-size:12px;font-weight:700">' + mark + ' </span><span style="color:#374151;font-size:12px">' + html + '</span>'}]}]}
    if render: sec["render"] = render
    return sec


def field_on_change(i):
    # Recheck every field, not just this one: a duplicate error set on another field for an earlier
    # name would otherwise stay after the name changes (seen live 2026-11-04). Then flag a duplicate
    # of the current name on this field only.
    recheck = "".join(
        f"  let e{j} = comsPatterns.checkField(s, {j}, {FIELD(j)}.value);\n"
        f"  if (e{j} != '') {{ {FIELD(j)}.setError(e{j}); }} else {{ {FIELD(j)}.clearError(); }}\n"
        for j in range(MAX_FIELDS))
    return ("<%\n"
            f"  let s = {SCH};\n"
            + recheck +
            f"  let err = e{i};\n"
            f"  let pn = {NAME};\n"
            "  patternPreviewText.setValue(pn);\n"
            "  if (err == '' && (existingOrgs.data ?? []).filter(o => { o.code == pn }).size() > 0) {\n"
            "    self.setError('A pattern with this name already exists: ' + pn);\n"
            "  }\n%>")


def submit():
    lines = ["<%", f"  let s = {SCH};", "  let valid = true;", "  prefixDropdown.clearError();", "  effectiveDate.clearError();"]
    lines += [f"  {FIELD(i)}.clearError();" for i in range(MAX_FIELDS)]
    lines += ["  if (empty(queryParams.appCode) || empty(s)) {", "    valid = false;", "  } else {",
              "    if (comsPatterns.prefixCount(s) > 1 && empty(prefixDropdown.value)) {",
              "      prefixDropdown.setError('Pick a pattern prefix.');", "      valid = false;", "    }"]
    for i in range(MAX_FIELDS):
        lines += [f"    let e{i + 1} = comsPatterns.checkField(s, {i}, {FIELD(i)}.value);",
                  f"    if (e{i + 1} != '') {{ {FIELD(i)}.setError(e{i + 1}); valid = false; }}"]
    lines += ["  }",
              "  if (empty(effectiveDate.value)) {", "    effectiveDate.setError('Effective Date is required.');", "    valid = false;",
              "  } else if (!comsValidations.isWeekday(effectiveDate.value)) {", "    effectiveDate.setError(comsValidations.errorWeekday());", "    valid = false;",
              "  } else if (!comsValidations.isCurrentOrFutureYear(effectiveDate.value)) {", "    effectiveDate.setError(comsValidations.errorYear());", "    valid = false;", "  }",
              "  if (valid) {",
              f"    let dupName = {NAME};",
              "    if ((existingOrgs.data ?? []).filter(o => { o.code == dupName }).size() > 0) {",
              f"      {FIELD(0)}.setError('A pattern with this name already exists: ' + dupName);", "      valid = false;", "    }", "  }",
              "  if (valid) {",
              f"    let rec = comsPatterns.recordFor(comsApplications.data, queryParams.appCode);",
              f"    let pn = {NAME};",
              f"    let v = {VALUES};",
              "    launchAddShellOrgPattern.invoke({'cbw': selectedWorker.id ?? '', 'cb': (selectedWorker.descriptor ?? '').urlEncode(), "
              "'ts': date:now().format(\"yyyy-MM-dd'T'HH:mm:ss'Z'\").urlEncode(), 'aid': rec.id, 'pn': pn.urlEncode(), 'wid': selectedWorker.id ?? '', "
              + ", ".join(f"'a{k + 1}': comsPatterns.cell(v[{k}]).urlEncode()" for k in range(5))
              + ", 'ed': effectiveDate.value.format('yyyy-MM-dd')});",
              "    let created = (verifyPattern.invoke({'lim': '10000'}).data ?? []).filter(o => { o.code == pn }).size() > 0;",
              "    if (!created) {",
              f"      {FIELD(0)}.setError('Workday rejected this request, so nothing was created. Check the values and try again.');",
              "      valid = false;", "    }", "  }", "  valid;", "%>"]
    return "\n".join(lines)


fields = []
for i in range(MAX_FIELDS):
    fields.append({"type": "text", "id": FIELD(i),
                   "label": f"<% comsPatterns.fieldLabel({SCH}, {i}) %>",
                   "visible": f"<% comsPatterns.fieldCount({SCH}) > {i} %>",
                   "placeholder": f"<% comsPatterns.fieldCount({SCH}) > {i} ? ('e.g. ' + {SCH}.fields[{i}].example) : '' %>",
                   "onChange": field_on_change(i)})

PICK_ROWS = "(comsApplications.data ?? []).filter(x => { !empty(x.patternSchema) && x.active != false }).map(x => { x.appId }).distinct().sort().map(a => { {'appCode': a} })"
txt = lambda cid, label, value: {"type": "column", "columnId": cid, "label": label,
                                 "cellTemplate": {"type": "text", "id": cid + "Text", "enabled": False, "value": value}}

page = {"id": "newSchemaPattern", "securityDomains": ["ManageCOMSShellOrgs"], "include": ["comsValidations.script", "comsPatterns.script"],
  "endPoints": [
    {"name": "selectedWorker", "baseUrlType": "COMMON", "url": "/workers/me", "authType": "sso", "failOnStatusCodes": FOS([400, 403, 429])},
    {"name": "comsApplications", "baseUrlType": "BUSINESS-OBJECT", "url": "/comsApplications?limit=100", "authType": "sso",
     "isCollection": True, "failOnStatusCodes": FOS([400, 403, 429])},
    {"name": "existingOrgs", "baseUrlType": "workday-wql", "url": "data", "authType": "sso", "bestEffort": "true",
     "failOnStatusCodes": FOS([400, 403, 500]), "wqlQuery": {"queryId": "customOrganizations"}},
    {"name": "launchAddShellOrgPattern", "baseUrlType": "orchestration", "authType": "sso", "deferred": "true",
     "url": "<% '/AddShellOrgPattern/launch?comsAppId=' + aid + '&patternName=' + pn + '&workerId=' + wid + '&attribute1=' + a1 + '&attribute2=' + a2 + '&attribute3=' + a3 + '&attribute4=' + a4 + '&attribute5=' + a5 + '&effectiveDate=' + ed + '&changedBy=' + cb + '&timestamp=' + ts + '&changedByWid=' + cbw %>"},
    {"name": "verifyPattern", "baseUrlType": "workday-wql", "authType": "sso", "deferred": "true",
     "url": "<% 'data?limit=' + lim + '&query=SELECT%20workdayID%2C%20code%20FROM%20topLevelOrganizations%20WHERE%20code%20contains%20%27X%3A%27' %>"}],
  "onSubmit": submit(),
  "presentation": {
    "headerSize": "STANDARD",
    "title": {"type": "title", "label": "<% empty(queryParams.appCode) ? 'ECO-COMS: Add Shell Org Pattern' : ('ECO-COMS: Add Shell Org Pattern · ' + queryParams.appCode) %>", "enabled": True},
    "cancelOverride": {"taskId": "shellOrgManager"},
    # nothing to submit until an application with a pattern schema is chosen
    "standardEditButtonsHidden": f"<% empty(queryParams.appCode) || empty({SCH}) %>",
    "body": {"type": "basicFormLayout", "id": "schemaPatternForm", "sections": [
      {"type": "layoutSection", "id": "navSection", "children": [
        {"type": "button", "id": "backButton", "label": "← Shell Org Manager", "action": "LINK", "suppressDiscardDialog": True, "taskReference": {"taskId": "shellOrgManager"}},
        {"type": "button", "id": "changeAppButton", "label": "Choose another application", "action": "LINK", "suppressDiscardDialog": True,
         "render": "<% !empty(queryParams.appCode) %>", "taskReference": {"taskId": PICKER}}]},
      note("aboutSection", "aboutFieldSet", "About This Page", "aboutRichText",
        "Create a shell org pattern for any application. Each application has its own pattern format: a prefix and its own fields "
        "(e.g. Subject and Course for Assessment Outcomes, one Role Name for most tools). The form below shows that application's fields, "
        "checks each value as you type, and builds the name as <b>APPLICATION:PREFIX:field:field</b>. A blank field becomes * (any). "
        "Submitting creates a live organization (subtype X:SHELL) in Workday; it can be inactivated later but not deleted."),
      # the application list lives on its own VIEW page (PICKER): edit pages draw grids with cell borders
      {"type": "layoutSection", "id": "pickSection", "render": "<% empty(queryParams.appCode) %>", "children": [
        {"type": "fieldSet", "id": "pickFieldSet", "title": "Choose an Application", "children": [
          {"type": "text", "id": "pickText", "label": "Application", "enabled": False, "value": "<% 'No application chosen yet.' %>"},
          {"type": "button", "id": "pickAppButton", "label": "Choose an Application", "action": "PRIMARY", "suppressDiscardDialog": True,
           "taskReference": {"taskId": PICKER}}]}]},
      {"type": "layoutSection", "id": "noSchemaSection", "render": f"<% !empty(queryParams.appCode) && empty({SCH}) %>", "children": [
        {"type": "fieldSet", "id": "noSchemaFieldSet", "title": "No Pattern Format", "children": [
          {"type": "text", "id": "noSchemaText", "label": "Pattern Format", "enabled": False,
           "value": f"<% 'No pattern format is set up for ' + (queryParams.appCode ?? '') + ' yet. Add it to the application record (patternSchema), then come back.' %>"}]}]},
      {"type": "layoutSection", "id": "formSection", "render": f"<% !empty(queryParams.appCode) && !empty({SCH}) %>", "children": [
        {"type": "fieldSet", "id": "patternDetailsFieldSet", "title": "Pattern Details", "children": [
          {"type": "text", "id": "applicationText", "label": "Application", "enabled": False,
           "value": f"<% {APPC} + ' · ' + ((comsPatterns.recordFor(comsApplications.data, queryParams.appCode) ?? {{'name': ''}}).name ?? '') %>"},
          {"type": "text", "id": "formatGuideText", "label": "Format", "enabled": False, "value": f"<% comsPatterns.formatGuide({SCH}) %>"},
          {"type": "dropdown", "id": "prefixDropdown", "label": "Pattern Prefix", "values": f"<% comsPatterns.prefixOptions({SCH}) %>",
           "visible": f"<% comsPatterns.prefixCount({SCH}) > 1 %>",
           "onChange": "<%\n  self.clearError();\n  let s = " + SCH + ";\n" + "".join(
               f"  let e{j} = comsPatterns.checkField(s, {j}, {FIELD(j)}.value);\n"
               f"  if (e{j} != '') {{ {FIELD(j)}.setError(e{j}); }} else {{ {FIELD(j)}.clearError(); }}\n" for j in range(MAX_FIELDS))
               + f"  patternPreviewText.setValue({NAME});\n%>"},
          {"type": "readOnlyText", "id": "patternPreviewText", "label": "Pattern Name Preview",
           # page-load value: the fields are declared further down, so they can't be referenced here yet
           "value": f"<% comsPatterns.buildName({APPC}, comsPatterns.prefixCount({SCH}) > 1 ? '' : comsPatterns.firstPrefix({SCH}), {SCH}, ['', '', '', '', '', '', '']) %>"}]},
        {"type": "fieldSet", "id": "patternFieldsFieldSet", "title": "Pattern Fields", "children": fields + [
          {"type": "date", "id": "effectiveDate", "label": "Effective Date", "required": True,
           "onChange": "<%\n  if (empty(self.value)) { self.clearError(); }\n  else if (!comsValidations.isWeekday(self.value)) { self.setError(comsValidations.errorWeekday()); }\n  else if (!comsValidations.isCurrentOrFutureYear(self.value)) { self.setError(comsValidations.errorYear()); }\n  else { self.clearError(); }\n%>"}]}]}]},
    "footer": FOOT, "pageType": "EDIT"}}
open(os.path.join(ROOT, 'newSchemaPattern.pmd'), 'w').write(json.dumps(page, indent=2, ensure_ascii=False) + '\n')

picker = {"id": PICKER, "securityDomains": ["ManageCOMSShellOrgs"], "include": ["comsPatterns.script"],
  "endPoints": [{"name": "comsApplications", "baseUrlType": "BUSINESS-OBJECT", "url": "/comsApplications?limit=100", "authType": "sso",
                 "isCollection": True, "failOnStatusCodes": FOS([400, 403, 429])}],
  "presentation": {"headerSize": "STANDARD", "title": {"type": "title", "label": "ECO-COMS: Add Shell Org Pattern"},
    "body": {"type": "basicFormLayout", "id": "schemaPatternAppsForm", "sections": [
      {"type": "layoutSection", "id": "navSection", "children": [
        {"type": "button", "id": "backButton", "label": "← Shell Org Manager", "action": "LINK", "taskReference": {"taskId": "shellOrgManager"}}]},
      note("aboutSection", "aboutFieldSet", "About This Page", "aboutRichText",
        "Choose the application to add a shell org pattern for. Each application has its own pattern format (shown below); "
        "<b>Add Pattern</b> opens a form with that application's fields."),
      {"type": "layoutSection", "id": "pickSection", "children": [
        {"type": "fieldSet", "id": "pickFieldSet", "title": "Choose an Application", "children": [
          {"type": "grid", "id": "appPickGrid", "rowVariableName": "pa", "label": "Applications", "rows": "<% " + PICK_ROWS + " %>",
           "columns": app_columns("pa", "newSchemaPattern", {"appCode": "<% pa.appCode %>"}, "Add Pattern")}]}]}]},
    "footer": FOOT, "pageType": "VIEW"}}
open(os.path.join(ROOT, PICKER + '.pmd'), 'w').write(json.dumps(picker, indent=2, ensure_ascii=False) + '\n')

# AMD: task + flow to the existing pattern success page
amdp = os.path.join(ROOT, 'ecocomsphase_xclw_cm_sync2_vmzvxm.amd')
amd = json.load(open(amdp))
if not any(x['id'] == PICKER for x in amd['tasks']):
    amd['tasks'].append({"id": PICKER, "routingPattern": "/" + PICKER, "page": {"id": PICKER}})
if not any(x['id'] == 'newSchemaPattern' for x in amd['tasks']):
    amd['tasks'].append({"id": "newSchemaPattern", "routingPattern": "/newSchemaPattern", "page": {"id": "newSchemaPattern"}})
amd['flowDefinitions'] = [f for f in amd.get('flowDefinitions', []) if f['id'] != 'newSchemaPatternFlow'] + [
    {"id": "newSchemaPatternFlow", "flowSteps": [
        {"id": "newSchemaPatternStep", "taskId": "newSchemaPattern", "startsFlow": True, "transitions": [{"order": "a", "value": "newSchemaPatternDoneStep", "condition": "true"}]},
        {"id": "newSchemaPatternDoneStep", "taskId": "newShellOrgPatternSuccess", "endsFlow": True}]}]
open(amdp, 'w').write(json.dumps(amd, indent=2, ensure_ascii=False) + '\n')

# Shell Org Manager (one application selected): one Add Pattern button for every application, this page
p = os.path.join(ROOT, 'shellOrgManager.pmd')
d = json.load(open(p))
def som(n):
    if isinstance(n, dict):
        kids = n.get('children')
        if isinstance(kids, list) and any(isinstance(k, dict) and k.get('id') == 'addPatternBtn' for k in kids):
            for k in kids:
                if isinstance(k, dict) and k.get('id') == 'addPatternBtn':
                    k['taskReference'] = {"taskId": "newSchemaPattern", "parameterBindings": {"appCode": "<% queryParams.appCode ?? '' %>"}}
                    k.pop('visible', None)
            kids[:] = [k for k in kids if not (isinstance(k, dict) and k.get('id') == 'addSchemaPatternBtn')]
        for v in n.values(): som(v)
    elif isinstance(n, list):
        for v in n: som(v)
som(d)
open(p, 'w').write(json.dumps(d, indent=2, ensure_ascii=False) + '\n')

# Quick Actions card: a pill for the other applications' pattern form
p = os.path.join(ROOT, 'cards', 'ShellOrgQuickActionsCard.card')
d = json.load(open(p))
pills = d['body']['pills']
for x in pills:
    if x.get('taskReference') == {"taskId": "newSchemaPattern"}: x['taskReference'] = {"taskId": PICKER}
if not any(x.get('taskReference', {}).get('taskId') == PICKER for x in pills):
    pills.append({"label": "Add Pattern (Other Apps)", "taskReference": {"taskId": PICKER}})
open(p, 'w').write(json.dumps(d, indent=2, ensure_ascii=False) + '\n')
print('newSchemaPattern written; Shell Org Manager and Quick Actions updated')

# Add Shell Org: the organization subtype is a choice, X:META or X:SHELL (product owner 2026-11-02).
# Add Pattern always sends X:SHELL (AddShellOrgPattern template).
p = os.path.join(ROOT, 'newShellOrg.pmd')
d = json.load(open(p))
for e in d['endPoints']:
    if e['name'] == 'launchAddShellOrg' and '&orgSubtype=' not in e['url']:
        e['url'] = e['url'].replace("'&orgType=' + ot + ", "'&orgType=' + ot + '&orgSubtype=' + st + ")
if "'st':" not in d['onSubmit']:
    d['onSubmit'] = d['onSubmit'].replace("'ot': lot, ", "'ot': lot, 'st': orgSubtypeDropdown.selectedEntries[0].id, ")
    d['onSubmit'] = d['onSubmit'].replace(
        "  if (empty(effectiveDate.value)) {",
        "  if (empty(orgSubtypeDropdown.value)) {\n    orgSubtypeDropdown.setError('Pick the organization subtype: X:META or X:SHELL.');\n    valid = false;\n  }\n  if (empty(effectiveDate.value)) {", 1)
SUBTYPE = {"type": "dropdown", "id": "orgSubtypeDropdown", "label": "Organization Subtype", "required": True,
           "instanceList": [{"id": "X:META", "descriptor": "X:META"}, {"id": "X:SHELL", "descriptor": "X:SHELL"}],
           "helpText": "X:META for an application's meta organization (e.g. X:CLW), X:SHELL for a shell organization roles are assigned on.",
           "onChange": "<% self.clearError(); %>"}
def add_subtype(n):
    if isinstance(n, dict):
        kids = n.get('children')
        if isinstance(kids, list):
            ids = [k.get('id') if isinstance(k, dict) else None for k in kids]
            if 'selectedApplicationId' in ids:
                if 'orgSubtypeDropdown' in ids:
                    kids[ids.index('orgSubtypeDropdown')] = SUBTYPE
                else:
                    kids.insert(ids.index('selectedApplicationId') + 1, SUBTYPE)
        for v in n.values(): add_subtype(v)
    elif isinstance(n, list):
        for v in n: add_subtype(v)
add_subtype(d['presentation'])
open(p, 'w').write(json.dumps(d, indent=2, ensure_ascii=False) + '\n')
print('newShellOrg: Organization Subtype pick-list')

# Shell Org Manager, Application Patterns tab (product owner 2026-11-02): only applications with pattern-form
# fields declared (a patternSchema record, plus Clockwork's own form); each one's patterns use its own prefixes.
p = os.path.join(ROOT, 'shellOrgManager.pmd')
d = json.load(open(p))
if not any(e['name'] == 'comsApplications' for e in d['endPoints']):
    d['endPoints'].append({"name": "comsApplications", "baseUrlType": "BUSINESS-OBJECT", "url": "/comsApplications?limit=100", "authType": "sso",
                           "isCollection": True, "failOnStatusCodes": FOS([400, 403, 429])})
APPS_WITH_FORM = "(comsApplications.data ?? []).filter(a => { !empty(a.patternSchema) })"
CLW_PATTERNS = ("(shellOrgPatterns.data ?? []).filter(p => { (p.code ?? '').startsWith('X:') && (p.code ?? '').contains(':PATTERN:') })"
                ".filter(p => { p.code.startsWith((queryParams.appCode ?? '') + ':PATTERN') })")
PREFS = ("((comsApplications.data ?? []).filter(a => { a.appId == (queryParams.appCode ?? '') }).map(a => { a.namePrefix ?? '' }).join(',')).split(',')")
SCHEMA_PATTERNS = ("(allShellOrgs.data ?? []).filter(o => { " + PREFS + ".filter(pf => { !empty(pf) && (o.code ?? '').startsWith((queryParams.appCode ?? '') + ':' + pf + ':') }).size() > 0 })")
PATTERNS = "(empty(queryParams.appCode) ? [] : ((queryParams.appCode == 'X:CLW') ? " + CLW_PATTERNS + " : " + SCHEMA_PATTERNS + "))"
ABOUT = ('<span style="color:#0055B7;font-size:12px;font-weight:700">ⓘ </span><span style="color:#374151;font-size:12px">'
         'A <b>pattern</b> is a Custom Organization (subtype X:SHELL) whose code follows its application\'s own format: '
         '<b>&lt;application&gt;:&lt;prefix&gt;:&lt;field&gt;:&lt;field&gt;…</b>. Each application sets its prefixes and fields; <b>*</b> means any. '
         'Roles assigned on a pattern apply to everything it matches. Only applications with a pattern format appear below: '
         'use <b>Manage</b> to see an application\'s patterns and <b>Add Pattern</b> to create one. Patterns can be inactivated but not deleted.</span>')
def tab(n):
    if isinstance(n, dict):
        i = n.get('id')
        if i == 'patternsAboutRichText':
            n['value'] = ABOUT
        elif i == 'appsGrid':
            n['rows'] = "<% " + APPS_WITH_FORM + ".map(a => { a.appId }).distinct().sort().map(appCode => { {'appCode': appCode} }) %>"
            n['columns'] = app_columns('app', 'shellOrgManager', {"appCode": "<% app.appCode %>", "appName": "<% app.appCode %>"}, 'Manage')
        elif i == 'patternsGrid':
            n['rows'] = "<% " + PATTERNS + " %>"
            n['visible'] = "<% !empty(queryParams.appCode) && size(" + PATTERNS + ") > 0 %>"
        elif i == 'patternsEmptyText':
            n['visible'] = "<% !empty(queryParams.appCode) && size(" + PATTERNS + ") == 0 %>"
        for v in n.values(): tab(v)
    elif isinstance(n, list):
        for v in n: tab(v)
tab(d['presentation'])
if 'comsPatterns.script' not in d.get('include', []):
    d['include'] = d.get('include', []) + ['comsPatterns.script']
open(p, 'w').write(json.dumps(d, indent=2, ensure_ascii=False) + '\n')
print('shellOrgManager: patterns tab lists applications with a pattern format')
