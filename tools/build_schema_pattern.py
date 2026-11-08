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
Server side, IORC_0037_XFD_SEC_Create_Pattern_Shell_Org re-checks prefix, field count, upper case and spaces
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
# an application switched off on Application Patterns (editAppPattern) takes no new patterns (product owner 2026-11-04)
INACTIVE = "((comsPatterns.recordFor(comsApplications.data, queryParams.appCode) ?? {'active': true}).active == false)"
FIELD = lambda i: f"patternField{i + 1}Text"
VALUES = "[" + ", ".join(f"{FIELD(i)}.value" for i in range(MAX_FIELDS)) + "]"
PREFIX = (f"(comsPatterns.prefixCount({SCH}) > 1 ? (empty(prefixDropdown.value) ? '' : prefixDropdown.selectedEntries[0].id)"
          f" : comsPatterns.firstPrefix({SCH}))")
NAME = f"comsPatterns.buildName({APPC}, {PREFIX}, {SCH}, {VALUES})"
# active academic unit codes, for fields whose Workday check is "Academic unit code" (2026-11-07)
UNITS = "(auCodes.data ?? []).map(u => { u.academicUnitCode ?? '' })"


def note(sid, fid, title, rid, html, color='#0055B7', mark='ⓘ', render=None):
    sec = {"type": "layoutSection", "id": sid, "children": [{"type": "fieldSet", "id": fid, "title": title, "children": [
        {"type": "richText", "id": rid, "enabled": False,
         "value": '<span style="color:' + color + ';font-size:12px;font-weight:700">' + mark + ' </span><span style="color:#374151;font-size:12px">' + html + '</span>'}]}]}
    if render: sec["render"] = render
    return sec


FIND = lambda i: f"patternField{i + 1}FindInstanceList"
LK = lambda j: f"comsPatterns.lookupOf(s, {j})"


def recheck_all():
    """es = every field's error (format, academic unit, and for fields with a Workday check one WQL query each through
    wdLookup); te / fe = those errors split between the typed boxes and the Workday pick-lists. Needs s and u first.
    One script call for all fields keeps the page under Workday's 100 KB limit."""
    return ("  let vs = " + VALUES + ";\n"
            "  let qs = vs.map((v, j) => { comsPatterns.fieldQuery(s, j, v, u) });\n"
            "  let rs = qs.map(q => { q == '' ? null : wdLookup.invoke({'q': q, 'lim': '50'}) });\n"
            "  let es = comsPatterns.fieldErrors(s, vs, u, rs);\n"
            "  let te = comsPatterns.textErrors(s, es);\n"
            "  let fe = comsPatterns.findErrors(s, es);\n")


def show_errors(prefix='  '):
    return "".join(f"{prefix}if (te[{j}] != '') {{ {FIELD(j)}.setError(te[{j}]); }} else {{ {FIELD(j)}.clearError(); }}\n"
                   f"{prefix}if (fe[{j}] != '') {{ {FIND(j)}.setError(fe[{j}]); }} else {{ {FIND(j)}.clearError(); }}\n"
                   for j in range(MAX_FIELDS))


def field_on_change(i, target='self', fill='', after=''):
    # Recheck every field, not just this one: a duplicate error set on another field for an earlier
    # name would otherwise stay after the name changes (seen live 2026-11-04). Then flag a duplicate
    # of the current name on this field only.
    return ("<%\n"
            f"  let s = {SCH};\n  let u = {UNITS};\n"
            + fill + recheck_all() + show_errors() +
            f"  let err = es[{i}];\n"
            f"  let pn = {NAME};\n"
            "  patternPreviewText.setValue(pn);\n"
            "  if (err == '' && (existingOrgs.data ?? []).filter(o => { o.code == pn }).size() > 0) {\n"
            f"    {target}.setError('A pattern with this name already exists: ' + pn);\n"
            "  }\n" + after + "%>")


def find_on_change(i):
    # the picked entry's value goes into the field's (hidden) box: a period as its short form, e.g. 2024W1; nothing
    # picked = blank. Then the usual recheck of every field.
    # a new subject clears the course picked for the old one (2026-11-07). Course comes from Subject (2026-11-08,
    # product owner): with no subject or *, Course is any (*) and locked (its list hidden, the read-only box shows it);
    # a real subject opens the Course list on that subject's courses
    fill = (f"  let fv = empty(self.value) ? '' : comsPatterns.pickValue(s, {i}, self.value[0]);\n"
            f"  if (empty(self.value) || fv != '') {{ {FIELD(i)}.setValue(fv); }}\n"
            f"  let realSubject = !empty(self.value) && fv != '' && fv != '*';\n"
            f"  let sc = comsPatterns.pickerKind(s, {i}) == 'courseSubject';\n"
            # a Course field comes after its Subject (both formats); every error is reset by the recheck below
            + "".join(f"  if (sc && comsPatterns.pickerKind(s, {j}) == 'course') {{ {FIND(j)}.setValue([]); {FIELD(j)}.setValue(fv == '*' ? '*' : ''); {FIND(j)}.setVisible(realSubject); {FIELD(j)}.setVisible(!realSubject); }}\n"
                      for j in range(i + 1, MAX_FIELDS)))
    after = (f"  if (!empty(self.value) && fv == '') {{ self.setError(comsPatterns.pickerKind(s, {i}) == 'course' ? 'This course has no number that fits the format: pick another or a wildcard.' : 'This period has no short form (W1, W2, W or S): pick its year or session instead.'); }}\n")
    return field_on_change(i, 'self', fill, after)


# the message for the whole name (duplicate, or Workday refused) goes under the first field, typed or picked
FIRST_ERR = lambda m: (f"if (comsPatterns.pickerKind(s, 0) == '') {{ {FIELD(0)}.setError({m}); }} else {{ {FIND(0)}.setError({m}); }}")


def submit():
    lines = ["<%", f"  let s = {SCH};", f"  let u = {UNITS};", "  let valid = true;", "  prefixDropdown.clearError();", "  effectiveDate.clearError();"]
    lines += [f"  {FIELD(i)}.clearError();\n  {FIND(i)}.clearError();" for i in range(MAX_FIELDS)]
    lines += ["  if (empty(queryParams.appCode) || empty(s)) {", "    valid = false;", "  } else {",
              "    if (comsPatterns.prefixCount(s) > 1 && empty(prefixDropdown.value)) {",
              "      prefixDropdown.setError('Pick a pattern prefix.');", "      valid = false;", "    }"]
    lines += [recheck_all().rstrip("\n"), show_errors("    ").rstrip("\n"),
              "    if (es.filter(e => { e != '' }).size() > 0) { valid = false; }"]
    lines += ["  }",
              "  if (empty(effectiveDate.value)) {", "    effectiveDate.setError('Effective Date is required.');", "    valid = false;",
              "  } else if (!comsValidations.isWeekday(effectiveDate.value)) {", "    effectiveDate.setError(comsValidations.errorWeekday());", "    valid = false;",
              "  } else if (!comsValidations.isCurrentOrFutureYear(effectiveDate.value)) {", "    effectiveDate.setError(comsValidations.errorYear());", "    valid = false;", "  }",
              "  if (valid) {",
              f"    let dupName = {NAME};",
              "    if ((existingOrgs.data ?? []).filter(o => { o.code == dupName }).size() > 0) {",
              "      " + FIRST_ERR("'A pattern with this name already exists: ' + dupName"), "      valid = false;", "    }", "  }",
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
              "      " + FIRST_ERR("'Workday rejected this request, so nothing was created. Check the values and try again.'"),
              "      valid = false;", "    }", "  }", "  valid;", "%>"]
    return "\n".join(lines)


fields = []
KIND = lambda i: f"comsPatterns.pickerKind({SCH}, {i})"
AU = "(auCodes.data ?? [])"
for i in range(MAX_FIELDS):
    # 2026-11-07 (product owner): a field with a Workday check (academic unit, course subject, academic period) is picked
    # from a list, not typed. Click to browse (the field's wildcards, then units by subtype, subjects by first letter,
    # periods by academic year with whole-year and session choices) or type to search Workday. Each list is one query of
    # only the rows it shows (units come from the page's unit list), so it stays quick with tens of thousands of rows.
    fields.append({"type": "instanceList", "id": FIND(i), "multiSelect": False,
                   "label": f"<% comsPatterns.fieldLabel({SCH}, {i}) %>",
                   # a course list shows once a real subject is picked (find_on_change); until then Course is any
                   "visible": f"<% {KIND(i)} != '' && {KIND(i)} != 'course' %>",
                   "helpText": "Click to browse, or type a code or name to search Workday (type * for the wildcards). Leave empty for any.",
                   "values": f"<% comsPatterns.rootFolders({SCH}, {i}, {AU}, wdYears.data ?? []) %>",
                   # one or two WQL steps: a course list first finds the picked subject's WID, then its courses
                   "dynamicMonikerLevels": ("<%\n"
                       "  const sel = self.promptSelections;\n"
                       f"  const q = comsPatterns.levelWql({SCH}, {i}, sel[0], {VALUES});\n"
                       "  const r1 = q == '' ? [] : (wdLookup.invoke({'q': q, 'lim': '2000'}).data ?? []);\n"
                       f"  const q2 = comsPatterns.nextWql({SCH}, {i}, r1);\n"
                       "  const rows = q2 == '' ? r1 : (wdLookup.invoke({'q': q2, 'lim': '2000'}).data ?? []);\n"
                       f"  const leaves = comsPatterns.levelRows({SCH}, {i}, sel[0], {AU}, rows);\n"
                       "  return [leaves, false];\n%>"),
                   "onSearch": ("<%\n"
                       f"  let sq = comsPatterns.searchQuery({SCH}, {i}, event.query, {VALUES});\n"
                       "  let r1 = sq == '' ? [] : (wdLookup.invoke({'q': sq, 'lim': '50'}).data ?? []);\n"
                       f"  let q2 = comsPatterns.nextWql({SCH}, {i}, r1);\n"
                       "  let rows = q2 == '' ? r1 : (wdLookup.invoke({'q': q2, 'lim': '2000'}).data ?? []);\n"
                       f"  comsPatterns.searchRows({SCH}, {i}, event.query, rows);\n%>"),
                   "onChange": find_on_change(i)})
    # the value that goes into the name: typed for ordinary fields, filled from the list (read-only) for checked ones
    # the value that goes into the name: typed for ordinary fields; hidden for checked ones, filled from the list
    # (2026-11-07, product owner: no per-field preview, the Pattern Name Preview shows the whole name)
    fields.append({"type": "text", "id": FIELD(i),
                   "label": f"<% comsPatterns.fieldLabel({SCH}, {i}) %>",
                   "visible": f"<% comsPatterns.fieldCount({SCH}) > {i} && ({KIND(i)} == '' || {KIND(i)} == 'course') %>",
                   "enabled": f"<% {KIND(i)} != 'course' %>",
                   "placeholder": f"<% comsPatterns.fieldCount({SCH}) > {i} ? ({KIND(i)} == 'course' ? 'Any (*): pick a subject first' : ('e.g. ' + {SCH}.fields[{i}].example)) : '' %>",
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
     "url": "<% '/IORC_0037_XFD_SEC_Create_Pattern_Shell_Org/launch?comsAppId=' + aid + '&patternName=' + pn + '&workerId=' + wid + '&attribute1=' + a1 + '&attribute2=' + a2 + '&attribute3=' + a3 + '&attribute4=' + a4 + '&attribute5=' + a5 + '&effectiveDate=' + ed + '&changedBy=' + cb + '&timestamp=' + ts + '&changedByWid=' + cbw %>"},
    # only fetched when this application has a field checked against academic unit codes
    {"name": "auCodes", "baseUrlType": "workday-wql", "url": "data", "authType": "sso", "bestEffort": "true",
     "wqlQuery": {"queryId": "academicUnitCodes"}, "failOnStatusCodes": FOS([429]),
     "exclude": f"<% !comsPatterns.needsUnits({SCH}) %>"},
    # one WQL query per lookup (2026-11-07): q comes from comsPatterns (lookupWql / treeWql / searchWql), which strips
    # quotes and backslashes from typed text first
    {"name": "wdLookup", "baseUrlType": "workday-wql", "authType": "sso", "deferred": "true",
     "url": "<% 'data?limit=' + lim + '&query=' + string:pathEncode(q) %>"},
    # academic years for the period picker's folders, only when this application has a field checked against periods
    {"name": "wdYears", "baseUrlType": "workday-wql", "authType": "sso", "bestEffort": "true", "failOnStatusCodes": FOS([429]),
     "url": "data?limit=1000&query=SELECT%20academicYear%2C%20startDate%20FROM%20academicYears%20ORDER%20BY%20startDate",
     "exclude": f"<% !comsPatterns.needsPeriods({SCH}) %>"},
    {"name": "verifyPattern", "baseUrlType": "workday-wql", "authType": "sso", "deferred": "true",
     "url": "<% 'data?limit=' + lim + '&query=SELECT%20workdayID%2C%20code%20FROM%20topLevelOrganizations%20WHERE%20code%20contains%20%27X%3A%27' %>"}],
  "onSubmit": submit(),
  "presentation": {
    "headerSize": "STANDARD",
    "title": {"type": "title", "label": "<% empty(queryParams.appCode) ? 'ECO-COMS: Add Shell Org Pattern' : ('ECO-COMS: Add Shell Org Pattern · ' + queryParams.appCode) %>", "enabled": True},
    "cancelOverride": {"taskId": "shellOrgManager"},
    # nothing to submit until an application with a pattern schema is chosen
    "standardEditButtonsHidden": f"<% empty(queryParams.appCode) || empty({SCH}) || {INACTIVE} %>",
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
      {"type": "layoutSection", "id": "inactiveSection", "render": f"<% !empty(queryParams.appCode) && {INACTIVE} %>", "children": [
        {"type": "fieldSet", "id": "inactiveFieldSet", "title": "Application Inactive", "children": [
          {"type": "text", "id": "inactiveText", "label": "Status", "enabled": False,
           "value": f"<% (queryParams.appCode ?? '') + ' is inactive, so it takes no new patterns. Reactivate it on Maintain Application Pattern (Edit, Active) to add one.' %>"}]}]},
      {"type": "layoutSection", "id": "noSchemaSection", "render": f"<% !empty(queryParams.appCode) && empty({SCH}) && !{INACTIVE} %>", "children": [
        {"type": "fieldSet", "id": "noSchemaFieldSet", "title": "No Pattern Format", "children": [
          {"type": "text", "id": "noSchemaText", "label": "Pattern Format", "enabled": False,
           "value": f"<% 'No pattern format is set up for ' + (queryParams.appCode ?? '') + ' yet. Add it to the application record (patternSchema), then come back.' %>"}]}]},
      {"type": "layoutSection", "id": "formSection", "render": f"<% !empty(queryParams.appCode) && !empty({SCH}) && !{INACTIVE} %>", "children": [
        {"type": "fieldSet", "id": "patternDetailsFieldSet", "title": "Pattern Details", "children": [
          {"type": "text", "id": "applicationText", "label": "Application", "enabled": False,
           "value": f"<% {APPC} + ' · ' + ((comsPatterns.recordFor(comsApplications.data, queryParams.appCode) ?? {{'name': ''}}).name ?? '') %>"},
          {"type": "text", "id": "formatGuideText", "label": "Format", "enabled": False, "value": f"<% comsPatterns.formatGuide({SCH}) %>"},
          {"type": "dropdown", "id": "prefixDropdown", "label": "Pattern Prefix", "values": f"<% comsPatterns.prefixOptions({SCH}) %>",
           "visible": f"<% comsPatterns.prefixCount({SCH}) > 1 %>",
           "onChange": "<%\n  self.clearError();\n  let s = " + SCH + ";\n  let u = " + UNITS + ";\n" + recheck_all() + show_errors()
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
                    # no Add Pattern for an application switched off on Application Patterns
                    k['render'] = "<% (comsApplications.data ?? []).filter(a => { a.appId == (queryParams.appCode ?? '') && a.active == false }).size() == 0 %>"
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
# Add Pattern always sends X:SHELL (IORC_0037_XFD_SEC_Create_Pattern_Shell_Org template).
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
