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
Server side, IORC_0037_XFD_SEC_Create_Pattern_Shell_Org re-checks prefix, field count, upper case and spaces against the saved record.
Secured by Manage: COMS Application Setup (the record's own domain). Idempotent.
"""
import json, os, sys
sys.path.insert(0, os.path.dirname(__file__))
from app_grid import app_columns

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'presentation')
FOS = lambda codes: [{"code": c} for c in codes]
FOOT = {"type": "footer", "children": [{"type": "pod", "podId": "ecoComsFooter"}]}
DOMAIN = "ManageCOMSApplicationSetup"
MAX_FIELDS = 7
load = lambda n: json.load(open(os.path.join(ROOT, n), encoding='utf-8'))
def save(n, d): open(os.path.join(ROOT, n), 'w', encoding='utf-8').write(json.dumps(d, indent=2, ensure_ascii=False) + '\n')

SCRIPT = '''/* Application Patterns setup (tools/build_app_patterns.py). Pure functions; each check returns '' or an error. */
/* ---- Field rules (2026-11-07). A rule (type, length, characters or values, option) compiles to the regular expression
   every check already uses; a regex the builder could have written reads back as a rule, and anything else stays an
   advanced regular expression. Mirrors test/rules.js, which the static checks run over the real formats. ---- */
var bs = function() {
  '%5C'.urlDecode();
};

var tr = function(s) {
  (s ?? '').trim();
};

var isChars = function(t) {
  t == 'upper' || t == 'upperDigits' || t == 'digits';
};

var optFirst = function(o) {
  o == 'first' || o == 'firstStar';
};

var optEnding = function(o) {
  (o == 'star' || o == 'firstStar') ? 'star' : (o == 'campus' ? 'campus' : ((o == 'letter' || o == 'letterShorter') ? 'letter' : ''));
};

var optShorter = function(o) {
  o == 'shorter' || o == 'letterShorter';
};

var optionId = function(first, ending, shorter) {
  if (first && ending == 'star' && !shorter) {
    'firstStar';
  } else if (first && ending == '' && !shorter) {
    'first';
  } else if (first) {
    '';
  } else if (ending == 'letter' && shorter) {
    'letterShorter';
  } else if (shorter && ending == '') {
    'shorter';
  } else if (shorter) {
    '';
  } else if (ending == '') {
    'none';
  } else {
    ending;
  }
};

var endingText = function(e) {
  e == 'star' ? (bs() + '*?') : (e == 'campus' ? '(_[A-Z])?' : (e == 'letter' ? '[A-Z]?' : ''));
};

var esc = function(v) {
  v.replace('*', bs() + '*').replace('.', bs() + '.').replace('+', bs() + '+');
};

var unesc = function(v) {
  v.replace(bs() + '*', '*').replace(bs() + '.', '.').replace(bs() + '+', '+');
};

var num = function(s) {
  validate:match('[0-9]+', tr(s)) ? tr(s).toInt() : 0;
};

var lo = function(len) {
  num(tr(len).contains('-') ? tr(len).substringBefore('-') : len);
};

var hi = function(len) {
  tr(len).contains('-') ? num(tr(len).substringAfter('-')) : lo(len);
};

var quant = function(len) {
  empty(tr(len)) ? '+' : (tr(len).contains('-') ? ('{' + lo(len) + ',' + hi(len) + '}') : ('{' + lo(len) + '}'));
};

var restQuant = function(len) {
  empty(tr(len)) ? '*' : (tr(len).contains('-') ? ('{' + (lo(len) - 1) + ',' + (hi(len) - 1) + '}') : ('{' + (lo(len) - 1) + '}'));
};

var baseOf = function(t) {
  t == 'upper' ? 'A-Z' : (t == 'upperDigits' ? 'A-Z0-9' : '0-9');
};

var extraOf = function(x) {
  (x ?? '').replace(' ', '');
};

var classOf = function(t, extra) {
  let x = extraOf(extra);
  '[' + baseOf(t) + x.replace('-', '') + (x.contains('-') ? '-' : '') + ']';
};

var listValues = function(text) {
  empty(tr(text)) ? [] : text.split(',').map(v => { v.trim() }).filter(v => { !empty(v) });
};

var ruleBody = function(t, len, values, o) {
  if (isChars(t)) {
    let main = (optFirst(o) && !empty(extraOf(values))) ? ('[' + baseOf(t) + ']' + classOf(t, values) + restQuant(len)) : (classOf(t, values) + quant(len));
    (optShorter(o) ? (classOf(t, values) + '{1,' + (hi(len) - 1) + '}' + bs() + '*|') : '') + main + endingText(optEnding(o));
  } else if (t == 'any') {
    '[^: ]' + quant(len);
  } else if (t == 'list') {
    '(' + listValues(values).map(v => { esc(v) }).join('|') + ')';
  } else if (t == 'fixed') {
    esc(tr(values));
  } else {
    '';
  }
};

var compileRule = function(t, len, values, o, blank) {
  (blank == true ? (bs() + '*|') : '') + ruleBody(t, len, values, o);
};

var lengthOk = function(len) {
  let l = tr(len);
  if (empty(l)) {
    true;
  } else if (validate:match('[0-9]+', l)) {
    num(l) > 0;
  } else if (validate:match('[0-9]+ *- *[0-9]+', l)) {
    lo(l) > 0 && lo(l) <= hi(l);
  } else {
    false;
  }
};

var lengthError = function(t, len, o) {
  if ((isChars(t) || t == 'any') && !lengthOk(len)) {
    'the length must be a number (3) or a range (2-6).';
  } else if (isChars(t) && optShorter(o) && (empty(tr(len)) || hi(len) < 2)) {
    'a shorter start then * needs a length of 2 or more.';
  } else {
    '';
  }
};

var valuesError = function(t, values, o) {
  if (isChars(t) && !validate:match('[-_.*/+]*', extraOf(values))) {
    'extra characters can only be - _ . * / +';
  } else if (isChars(t) && optFirst(o) && empty(extraOf(values))) {
    '"starts with a letter or digit" only matters with extra characters such as - or _.';
  } else if (t == 'list' && listValues(values).size() < 2) {
    'list at least two values, separated by commas (e.g. V, O, S).';
  } else if (t == 'list' && listValues(values).filter(v => { !validate:match('[A-Z0-9_.*/+-]+', v) }).size() > 0) {
    'list values use capital letters, digits and - _ . * / + only.';
  } else if (t == 'fixed' && !validate:match('[A-Z0-9_.*/+-]+', tr(values))) {
    'the fixed text uses capital letters, digits and - _ . * / + only.';
  } else {
    '';
  }
};

var ruleError = function(t, len, values, o) {
  let a = lengthError(t, len, o);
  a != '' ? a : valuesError(t, values, o);
};

var lengthWords = function(len) {
  empty(tr(len)) ? 'one or more' : (tr(len).contains('-') ? ('' + lo(len) + ' to ' + hi(len)) : ('' + lo(len)));
};

var charWords = function(t) {
  t == 'upper' ? 'capital letters' : (t == 'upperDigits' ? 'capital letters or digits' : (t == 'digits' ? 'digits' : 'characters (no colons or spaces)'));
};

var endWords = function(e) {
  e == 'star' ? '; may end with * to match many' : (e == 'campus' ? '; may end with _ and a campus letter (e.g. _V)' : (e == 'letter' ? '; may end with a capital letter' : ''));
};

var hintFor = function(t, len, values, o, blank) {
  let x = extraOf(values);
  let core = '';
  if (isChars(t)) {
    core = lengthWords(len) + ' ' + charWords(t) + (empty(x) ? '' : (', or any of ' + x))
      + ((optFirst(o) && !empty(x)) ? ', starting with a letter or digit' : '') + endWords(optEnding(o))
      + (optShorter(o) ? ('; or the first 1 to ' + (hi(len) - 1) + ' followed by * (e.g. 1*)') : '');
  } else if (t == 'any') {
    core = lengthWords(len) + ' ' + charWords(t);
  } else if (t == 'list') {
    core = 'one of ' + listValues(values).join(', ');
  } else if (t == 'fixed') {
    core = 'always ' + tr(values);
  }
  empty(core) ? '' : (core.capitalize() + (blank == true ? '. Leave blank for any.' : '.'));
};

var asRule = function(t, len, values, o, regex, blank) {
  if (empty(t) || t == 'regex' || empty(o)) {
    null;
  } else if (ruleError(t, len, values, o) != '') {
    null;
  } else if (compileRule(t, len, values, o, blank) != regex) {
    null;
  } else {
    let m = { 'ruleType': t, 'ruleLength': len, 'ruleValues': values, 'ruleOption': o };
    m;
  }
};

var lenFrom = function(q, plus) {
  if (q == '+' || (q == '*' && plus == 1)) {
    '';
  } else if (!(q.startsWith('{') && q.endsWith('}') && q.length() > 2)) {
    'x';
  } else {
    let m = q.substring(1, q.length() - 1);
    m.contains(',') ? ('' + (num(m.substringBefore(',')) + plus) + '-' + (num(m.substringAfter(',')) + plus)) : ('' + (num(m) + plus));
  }
};

var typeOf = function(inner) {
  inner.startsWith('A-Z0-9') ? 'upperDigits' : (inner.startsWith('A-Z') ? 'upper' : (inner.startsWith('0-9') ? 'digits' : ''));
};

var parseChars = function(body, r, blank) {
  let sep = bs() + '*|';
  let shorter = body.contains(sep) && body.substringBefore(sep).contains('{1,');
  let b1 = shorter ? body.substringAfter(sep) : body;
  let ending = b1.endsWith(endingText('star')) ? 'star' : (b1.endsWith(endingText('campus')) ? 'campus' : (b1.endsWith(endingText('letter')) ? 'letter' : ''));
  let b = ending == '' ? b1 : b1.substring(0, b1.length() - endingText(ending).length());
  let c1 = b.substringAfter('[').substringBefore(']');
  let rest = b.substringAfter(']');
  let first = rest.startsWith('[');
  let inner = first ? rest.substringAfter('[').substringBefore(']') : c1;
  let q = first ? rest.substringAfter(']') : rest;
  let t = typeOf(inner);
  let extra = t == 'upperDigits' ? inner.substring(6) : (empty(t) ? '' : inner.substring(3));
  let o = optionId(first, ending, shorter);
  empty(o) ? null : asRule(t, lenFrom(q, first ? 1 : 0), extra, o, r, blank);
};

var parseRegex = function(regex, blank) {
  let r = tr(regex);
  let body = (blank == true && r.startsWith(bs() + '*|')) ? r.substring(3) : r;
  let rule = null;
  if (body == '[^: ]+' || (body.startsWith('[^: ]{') && body.endsWith('}'))) {
    rule = asRule('any', lenFrom(body.substring(5), 0), '', 'none', r, blank);
  } else if (body.startsWith('[') && body.contains(']')) {
    rule = parseChars(body, r, blank);
  } else if (body.startsWith('(') && body.endsWith(')') && body.length() > 2) {
    rule = asRule('list', '', body.substring(1, body.length() - 1).split('|').map(v => { unesc(v) }).join(', '), 'none', r, blank);
  } else if (!empty(body)) {
    rule = asRule('fixed', '', unesc(body), 'none', r, blank);
  }
  if (empty(rule)) {
    let m = { 'ruleType': 'regex', 'ruleLength': '', 'ruleValues': '', 'ruleOption': 'none' };
    m;
  } else {
    rule;
  }
};

/* A stored field's rule: the saved rule, or (formats saved before rules existed) the regex read back as a rule. */
var ruleOf = function(f) {
  if (!empty(f.ruleType) && f.ruleType != 'regex') {
    let m = { 'ruleType': f.ruleType, 'ruleLength': f.ruleLength ?? '', 'ruleValues': f.ruleValues ?? '', 'ruleOption': f.ruleOption ?? 'none' };
    m;
  } else if (f.ruleType == 'regex') {
    let m = { 'ruleType': 'regex', 'ruleLength': '', 'ruleValues': '', 'ruleOption': 'none' };
    m;
  } else {
    parseRegex(f.regex, f.blankIsWildcard == true);
  }
};

var fieldRow = function(f) {
  let p = ruleOf(f);
  let m = { 'fieldLabel': f.fieldLabel ?? '', 'regex': f.regex ?? '', 'hint': f.hint ?? '', 'example': f.example ?? '',
    'blankIsWildcard': f.blankIsWildcard == true, 'optionalField': f.optionalField == true,
    'ruleType': p.ruleType, 'ruleLength': p.ruleLength, 'ruleValues': p.ruleValues, 'ruleOption': p.ruleOption,
    'lookup': empty(f.lookup) ? 'none' : f.lookup };
  m;
};

/* One grid row as it is saved: in rule mode the regex and (when left blank) the hint come from the rule. */
var rowOf = function(label, t, len, vals, o, regex, hint, example, blank, optional, lookup) {
  let tt = empty(t) ? 'regex' : t;
  let oo = empty(o) ? 'none' : o;
  let isRule = tt != 'regex';
  let m = { 'fieldLabel': tr(label), 'regex': isRule ? compileRule(tt, tr(len), tr(vals), oo, blank == true) : tr(regex),
    'hint': empty(tr(hint)) ? hintFor(tt, tr(len), tr(vals), oo, blank == true) : tr(hint), 'example': tr(example),
    'blankIsWildcard': blank == true, 'optionalField': optional == true,
    'ruleType': tt, 'ruleLength': isRule ? tr(len) : '', 'ruleValues': isRule ? tr(vals) : '', 'ruleOption': isRule ? oo : 'none',
    'lookup': empty(lookup) ? 'none' : lookup };
  m;
};

var recordById = function(apps, id) {
  let m = (apps ?? []).filter(a => { a.id == id });
  empty(id) || empty(m) ? null : m[0];
};

var schemaOf = function(rec) {
  (empty(rec) || empty(rec.patternSchema)) ? null : json:parse(rec.patternSchema);
};

var fieldRows = function(rec) {
  let s = schemaOf(rec);
  empty(s) ? [rowOf('', 'upperDigits', '', '', 'none', '', '', '', false, false, 'none')] : s.fields.map(f => { fieldRow(f) });
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

var rowError = function(r, n, units) {
  let where = 'Field ' + n + ': ';
  if (empty(r.fieldLabel)) {
    where + 'a label is required.';
  } else if (r.fieldLabel.contains(':')) {
    where + 'the label cannot contain a colon.';
  } else if (r.ruleType != 'regex' && ruleError(r.ruleType, r.ruleLength, r.ruleValues, r.ruleOption) != '') {
    where + ruleError(r.ruleType, r.ruleLength, r.ruleValues, r.ruleOption);
  } else if (empty(r.regex)) {
    where + 'a format is required (a regular expression, e.g. [A-Z]{2,4}).';
  } else if (empty(r.example)) {
    where + 'an example value is required.';
  } else if (r.example.contains(':') || r.example.contains(' ')) {
    where + 'the example cannot contain a colon or spaces.';
  } else if (!validate:match(r.regex, r.example)) {
    where + 'the example ' + r.example + ' does not match the format ' + r.regex + '.';
  } else if (r.lookup == 'academicUnitCode' && (units ?? []).size() > 0 && r.example != '*' && !units.contains(r.example)) {
    where + 'the example ' + r.example + ' is not the code of an active academic unit in Workday (e.g. MATH).';
  } else {
    '';
  }
};

var fieldsError = function(rows, units) {
  if (rows.size() == 0) {
    'Add at least one field.';
  } else if (rows.size() > 7) {
    'At most 7 fields: the Add Pattern form has 7 boxes.';
  } else if (rows.map(r => { r.fieldLabel }).distinct().size() != rows.size()) {
    'Each field needs its own label.';
  } else if (rows.filter((r, i) => { r.optionalField == true && rows.subList(i, rows.size()).filter(x => { x.optionalField != true }).size() > 0 }).size() > 0) {
    'Only the last fields can be optional: a field after an optional one must be optional too.';
  } else if (rows.filter(r => { r.optionalField == true && r.blankIsWildcard == true }).size() > 0) {
    'An optional field is left off when blank, so it cannot also be Blank = any (*).';
  } else if (rows.filter(r => { r.optionalField != true }).size() == 0) {
    'At least the first field must be required (not optional).';
  } else {
    let errs = rows.map((r, i) => { rowError(r, i + 1, units) }).filter(e => { e != '' });
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
  empty(s) ? '' : (s.prefixes.join(' / ') + ': ' + s.fields.map(f => { f.fieldLabel }).join(', '));
};

/* The list's Example column: the stored full example if any (saved by the earlier text-box version), else built from the fields. */
var exampleOf = function(appId, rec) {
  let s = schemaOf(rec);
  empty(s) ? '' : (empty(s.example) ? exampleName(appId, s.prefixes.join(','), s.fields) : s.example);
};

/* Copy from: every other application that has a format. */
var copyOptions = function(apps, appId) {
  list:sort((apps ?? []).filter(a => { !empty(a.patternSchema) && a.appId != appId }), 'appId', true)
    .map(a => { { 'id': a.id, 'descriptor': a.appId + ' · ' + summary(a) } });
};

{
  "parseRegex": parseRegex,
  "compileRule": compileRule,
  "hintFor": hintFor,
  "lengthError": lengthError,
  "valuesError": valuesError,
  "ruleError": ruleError,
  "fieldRow": fieldRow,
  "rowOf": rowOf,
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
  "summary": summary,
  "exampleOf": exampleOf,
  "copyOptions": copyOptions
}
'''
open(os.path.join(ROOT, 'scripts', 'comsAppSetup.script'), 'w', encoding='utf-8').write(SCRIPT)

INFO = lambda html: '<span style="color:#0055B7;font-size:12px;font-weight:700">ⓘ </span><span style="color:#374151;font-size:12px">' + html + '</span>'
APPS_EP = {"name": "comsApplications", "baseUrlType": "BUSINESS-OBJECT", "url": "/comsApplications?limit=100", "authType": "sso",
           "isCollection": True, "failOnStatusCodes": FOS([400, 403, 429])}
txt = lambda cid, label, value: {"type": "column", "columnId": cid, "label": label, "sortableAndFilterable": "true",
                                 "cellTemplate": {"type": "text", "id": cid + "Text", "enabled": False, "value": value}}

# ---- list page ----
setup = {"id": "appPatternSetup", "securityDomains": [DOMAIN], "include": ["comsAppSetup.script", "comsPatterns.script"],
  "endPoints": [APPS_EP],
  "presentation": {"pageType": "VIEW", "headerSize": "STANDARD", "title": {"type": "title", "label": "ECO-COMS: Maintain Application Pattern"},
    "body": {"type": "basicFormLayout", "id": "appPatternSetupForm", "sections": [
      {"type": "layoutSection", "id": "navSection", "children": [
        {"type": "button", "label": "← Home", "taskReference": {"taskId": "home"}, "action": "LINK"},
        {"type": "button", "id": "shellOrgManagerButton", "label": "← Shell Org Manager", "taskReference": {"taskId": "shellOrgManager"}, "action": "LINK"}]},
      {"type": "layoutSection", "id": "aboutSection", "children": [{"type": "fieldSet", "id": "aboutFieldSet", "title": "About This Page", "children": [
        {"type": "richText", "id": "aboutRichText", "enabled": False, "value": INFO(
          "Each application's shell org pattern format: its prefixes and its fields. The <b>Add Shell Org Pattern</b> form reads "
          "these, so a change here shows up there straight away. <b>Edit</b> changes an application's format; "
          "<b>Add Application</b> sets up one that isn't listed yet. Existing patterns keep their names; a new format only applies to new patterns.")}]}]},
      {"type": "layoutSection", "id": "appsSection", "children": [{"type": "fieldSet", "id": "appsFieldSet", "title": "Applications", "children": [
        {"type": "button", "id": "addApplicationButton", "label": "Add Application", "action": "PRIMARY",
         "taskReference": {"taskId": "editAppPattern"}},
        # every add and edit is in the Audit Log as Change Type "Application Pattern" (product owner 2026-11-05)
        {"type": "button", "id": "changeHistoryButton", "label": "View Change History", "action": "AUXILIARY",
         "taskReference": {"taskId": "auditLogViewer", "parameterBindings": {"changeType": "Application Pattern"}}},
        # Same columns as every other application grid (tools/app_grid.py; product owner 2026-11-02 and 2026-11-05: grids
        # in one format): Application ID as a link, Name, Pattern Format, this page's Example and Status, then the action.
        {"type": "grid", "id": "appPatternsGrid", "label": "Application Pattern Formats", "rowVariableName": "ap",
         "rows": "<% list:sort((comsApplications.data ?? []).filter(a => { !empty(a.appId) }), 'appId', true).map(a => { {'appCode': a.appId, 'rec': a} }) %>",
         "columns": (lambda cols: cols[:-1] + [
           {"type": "column", "columnId": "colExample", "label": "Example", "cellTemplate": {"type": "text", "id": "colExampleText", "enabled": False,
            "value": "<% comsAppSetup.exampleOf(ap.appCode, ap.rec) %>"}},
           # Status drawn as on Shell Org Manager's status columns
           {"type": "column", "columnId": "colActive", "label": "Status", "excel": {"value": "<% ap.rec.active == false ? 'Inactive' : 'Active' %>"},
            "cellTemplate": {"type": "richText", "id": "colActiveRichText", "enabled": False, "value":
              "<% ap.rec.active == false ? '<span style=\"color:#6b7280;font-weight:600;font-size:12px\">\u25cb Inactive</span>' : '<span style=\"color:#065f46;font-weight:600;font-size:12px\">\u2713 Active</span>' %>"}},
           cols[-1]])(app_columns("ap", "editAppPattern", {"recordId": "<% ap.rec.id %>"}, "Edit"))}]}]}]},
    "footer": FOOT}}
save('appPatternSetup.pmd', setup)

# ---- edit page: only the pattern format and its example change (product owner 2026-11-04) ----
# the record arrives as recordId (Edit buttons, links) or taskObjectId (the record's related action, whose route
# App Builder only accepts when the parameter has the task's own name: "/editAppPattern/{taskObjectId}")
RID = "(queryParams.recordId ?? queryParams.taskObjectId ?? '')"
REC = f"comsAppSetup.recordById(comsApplications.data, {RID})"
NEW = f"empty({RID})"
CHOSEN = "(empty(appIdDropdown.value) ? '' : appIdDropdown.selectedEntries[0].id)"
APPID = f"({NEW} ? {CHOSEN} : ({REC} ?? {{'appId': ''}}).appId)"
DD = lambda col: f"(empty(r.childrenMap.{col}.value) ? '' : r.childrenMap.{col}.value[0])"
ROWS = ("fieldsGrid.rows.map(r => { comsAppSetup.rowOf(r.childrenMap.colFieldLabel.value, "
        f"{DD('colRule')}, r.childrenMap.colLength.value, r.childrenMap.colValues.value, {DD('colOption')}, "
        "r.childrenMap.colRegex.value, r.childrenMap.colHint.value, r.childrenMap.colExample.value, "
        f"r.childrenMap.colBlank.value == true, r.childrenMap.colOptional.value == true, {DD('colLookup')}) }})")
# active academic unit codes (Workday's Code field, e.g. MATH) for fields checked against them
UNITS = "(auCodes.data ?? []).map(u => { u.academicUnitCode ?? '' })"
SRC = "comsAppSetup.recordById(comsApplications.data, copyFromDropdown.selectedEntries[0].id)"
# An error OK puts on the Fields line has no box of its own to clear it, and Workday refuses OK while any error shows
# (live 2026-11-04: the page stayed stuck after the row was fixed), so every table edit clears it; OK re-checks.
PREVIEW = f"exampleNameText.setValue(comsAppSetup.exampleName({APPID}, prefixesText.value ?? '', {ROWS}));"
FIELDS_TOUCHED = "fieldsCheckText.clearError(); " + PREVIEW
cell = lambda cid, label, key, kind="text": {"type": "column", "columnId": cid, "label": label, "cellTemplate": {
    "type": kind, "id": cid + ("CheckBox" if kind == "checkBox" else "Text"),
    "value": f"<% fr.{key} ?? {'false' if kind == 'checkBox' else chr(39) * 2} %>", "onChange": "<% " + FIELDS_TOUCHED + " %>"}}
RULE_TYPES = [("upper", "Capital letters"), ("upperDigits", "Capital letters and digits"), ("digits", "Digits"),
              ("list", "One of a list"), ("fixed", "Fixed text"), ("any", "Any text"), ("regex", "Regular expression (advanced)")]
RULE_OPTIONS = [("none", "None"), ("first", "Starts with a letter or digit"), ("star", "May end with *"),
                ("firstStar", "Starts with a letter or digit, may end with *"),
                ("campus", "May end with _ and a campus letter (e.g. _V)"), ("letter", "May end with a capital letter (e.g. 100A)"),
                ("shorter", "Or a shorter start then * (e.g. 1*)"),
                ("letterShorter", "May end with a capital letter, or a shorter start then *")]
LOOKUPS = [("none", "None"), ("academicUnitCode", "Academic unit code"),
           # 2026-11-07: each value looked up on its own (WQL courseSubjects / academicPeriods), for tens of thousands of rows
           ("courseSubject", "Course subject abbreviation (e.g. CHEM)"),
           ("academicPeriod", "Academic period (e.g. 2024W1 = a 2024-25 Winter Term 1 period)"),
           # the picked subject's courses (WQL courseDefinitions); needs a Course subject field in the same format
           ("course", "Course of the picked subject (listed from Workday)")]
# a field's example must exist in Workday when its check is a course subject or an academic period: one query per example
EXAMPLES_MISSING = ("ROWS.filter(r => { comsPatterns.lookupWql(r.lookup, r.example) != '' }).filter(r => { "
                    "let x = wdLookup.invoke({'q': comsPatterns.lookupWql(r.lookup, r.example), 'lim': '50'}); "
                    "comsPatterns.lookupMiss(r.lookup, r.example, x.total ?? (0 - 1), x.data ?? []) })")
# A rule setting changed (cell onChange; the row's other cells are reachable by id): recheck the rule, write its regex
# into the Format cell (read-only while a rule is in use), and keep the hint in step unless someone wrote their own.
# Regular expression mode unlocks the Format cell and keeps whatever regex is there: rule -> regex loses nothing.
# Regex -> a rule type: when the regex reads back as that type, its length and characters are filled in.
RULE_CHANGED = ("<%\n"
  "  let t = empty(colRuleDropdown.value) ? 'regex' : colRuleDropdown.value[0];\n"
  "  let o = empty(colOptionDropdown.value) ? 'none' : colOptionDropdown.value[0];\n"
  "  let blank = colBlankCheckBox.value == true;\n"
  "  let was = comsAppSetup.parseRegex(colRegexText.value ?? '', blank);\n"
  "  let wasHint = comsAppSetup.hintFor(was.ruleType, was.ruleLength, was.ruleValues, was.ruleOption, blank);\n"
  "  let fill = t != 'regex' && was.ruleType == t && empty(colLengthText.value) && empty(colValuesText.value);\n"
  "  let len = fill ? was.ruleLength : (colLengthText.value ?? '');\n"
  "  let vals = fill ? was.ruleValues : (colValuesText.value ?? '');\n"
  "  if (fill) { colLengthText.setValue(len); colValuesText.setValue(vals); }\n"
  "  let lenErr = t == 'regex' ? '' : comsAppSetup.lengthError(t, len, o);\n"
  "  let valErr = t == 'regex' ? '' : comsAppSetup.valuesError(t, vals, o);\n"
  "  if (lenErr != '') { colLengthText.setError(lenErr); } else { colLengthText.clearError(); }\n"
  "  if (valErr != '') { colValuesText.setError(valErr); } else { colValuesText.clearError(); }\n"
  "  colRegexText.setEnabled(t == 'regex');\n"
  "  if (t != 'regex' && lenErr == '' && valErr == '') {\n"
  "    colRegexText.setValue(comsAppSetup.compileRule(t, len, vals, o, blank));\n"
  "    if (empty(colHintText.value) || colHintText.value == wasHint) { colHintText.setValue(comsAppSetup.hintFor(t, len, vals, o, blank)); }\n"
  "  }\n  " + FIELDS_TOUCHED + "\n%>")
pick = lambda cid, label, key, choices, default, on_change: {"type": "column", "columnId": cid, "label": label, "cellTemplate": {
    "type": "dropdown", "id": cid + "Dropdown", "instanceList": [{"id": i, "descriptor": d} for i, d in choices],
    "selectedValues": f"<% [fr.{key} ?? '{default}'] %>", "onChange": on_change}}
OUT = lambda path, value: {"outboundPath": path, "value": value}
SCHEMA = f"comsAppSetup.schemaJson(prefixesText.value ?? '', {ROWS})"
PREFIXES = "comsAppSetup.prefixList(prefixesText.value ?? '').join(',')"
STAMP = "date:now().format(\"yyyy-MM-dd'T'HH:mm:ss'Z'\")"
submit = ("<%\n"
          "  appIdDropdown.clearError();\n  appNameText.clearError();\n  prefixesText.clearError();\n  fieldsCheckText.clearError();\n"
          "  let valid = true;\n"
          f"  let e1 = comsAppSetup.appIdError({CHOSEN}, comsApplications.data, {NEW});\n"
          "  if (e1 != '') { appIdDropdown.setError(e1); valid = false; }\n"
          f"  let e2 = {NEW} ? comsAppSetup.nameError((appNameText.value ?? '').trim()) : '';\n"
          "  if (e2 != '') { appNameText.setError(e2); valid = false; }\n"
          "  let e3 = comsAppSetup.prefixError(prefixesText.value ?? '');\n"
          "  if (e3 != '') { prefixesText.setError(e3); valid = false; }\n"
          f"  let e4 = comsAppSetup.fieldsError({ROWS}, {UNITS});\n"
          "  if (e4 != '') { fieldsCheckText.setError(e4); valid = false; }\n"
          "  if (e4 == '') {\n"
          f"    let miss = {EXAMPLES_MISSING.replace('ROWS', ROWS)};\n"
          "    if (miss.size() > 0) { fieldsCheckText.setError(comsPatterns.lookupMessage(miss[0].lookup, miss[0].fieldLabel + ' (example)', miss[0].example)); valid = false; }\n"
          "  }\n"
          "  valid;\n%>")
edit = {"id": "editAppPattern", "securityDomains": [DOMAIN], "include": ["comsAppSetup.script", "comsPatterns.script"],
  "endPoints": [APPS_EP,
    {"name": "existingOrgs", "baseUrlType": "workday-wql", "url": "data", "authType": "sso", "bestEffort": "true",
     "wqlQuery": {"queryId": "customOrganizations"}, "failOnStatusCodes": FOS([400, 429])},
    {"name": "selectedWorker", "baseUrlType": "COMMON", "url": "/workers/me", "authType": "sso", "bestEffort": "true", "failOnStatusCodes": FOS([400, 403, 429])},
    # a failed list only switches the code check off (bestEffort, 400 left out): the rest of the page still works
    {"name": "auCodes", "baseUrlType": "workday-wql", "url": "data", "authType": "sso", "bestEffort": "true",
     "wqlQuery": {"queryId": "academicUnitCodes"}, "failOnStatusCodes": FOS([429])},
    {"name": "wdLookup", "baseUrlType": "workday-wql", "authType": "sso", "deferred": "true",
     "url": "<% 'data?limit=' + lim + '&query=' + string:pathEncode(q) %>"}],
  "outboundData": {"outboundEndPoints": [
    {"name": "postApplication", "baseUrlType": "BUSINESS-OBJECT", "url": "/comsApplications", "httpMethod": "POST", "authType": "sso",
     "exclude": f"<% !{NEW} %>", "failOnStatusCodes": FOS([400, 403, 429, 500]), "values": [
       OUT("appId", f"<% {CHOSEN} %>"), OUT("name", "<% (appNameText.value ?? '').trim() %>"),
       OUT("orgType", f"<% {CHOSEN} %>"), OUT("orgSubtype", "X:SHELL"),
       OUT("namePrefix", f"<% {PREFIXES} %>"), OUT("patternSchema", f"<% {SCHEMA} %>"), OUT("active", "<% appActiveCheckBox.value == true %>")]},
    {"name": "patchApplication", "baseUrlType": "BUSINESS-OBJECT", "url": f"<% '/comsApplications/' + {RID} %>",
     "httpMethod": "PATCH", "authType": "sso", "exclude": f"<% {NEW} %>", "failOnStatusCodes": FOS([400, 403, 404, 429, 500]), "values": [
       OUT("namePrefix", f"<% {PREFIXES} %>"), OUT("patternSchema", f"<% {SCHEMA} %>"), OUT("active", "<% appActiveCheckBox.value == true %>")]},
    {"name": "postAudit", "baseUrlType": "BUSINESS-OBJECT", "url": "/comsAuditLogs", "httpMethod": "POST", "authType": "sso",
     "failOnStatusCodes": FOS([400, 403, 429, 500]), "values": [
       OUT("timestamp", f"<% {STAMP} %>"), OUT("objectType", "Application Pattern"),
       OUT("action", f"<% {NEW} ? 'ADD' : 'UPDATE' %>"),
       OUT("coReferenceId", f"<% {APPID} %>"), OUT("coName", f"<% {APPID} %>"),
       OUT("triggeredBy", "<% selectedWorker.descriptor ?? '' %>"), OUT("changedByWid", "<% selectedWorker.id ?? '' %>"),
       OUT("details", f"<% 'Pattern format for ' + {APPID} + ': ' + {PREFIXES}.replace(',', ' / ') + ': ' + {ROWS}.map(r => {{ r.fieldLabel }}).join(', ') + (appActiveCheckBox.value == true ? '' : ' (inactive)') %>")]}]},
  "onSubmit": submit,
  "presentation": {"pageType": "EDIT", "headerSize": "STANDARD",
    "title": {"type": "title", "label": f"<% {NEW} ? 'ECO-COMS: Add Application' : ('ECO-COMS: Edit Pattern Format · ' + ({REC} ?? {{'appId': ''}}).appId) %>"},
    "cancelOverride": {"taskId": "appPatternSetup"},
    "body": {"type": "basicFormLayout", "id": "editAppPatternForm", "sections": [
      {"type": "layoutSection", "id": "navSection", "children": [
        {"type": "button", "id": "appPatternsBackButton", "label": "← Maintain Application Pattern", "action": "LINK", "suppressDiscardDialog": True,
         "taskReference": {"taskId": "appPatternSetup"}},
        {"type": "button", "id": "shellOrgManagerBackButton", "label": "← Shell Org Manager", "action": "LINK", "suppressDiscardDialog": True,
         "taskReference": {"taskId": "shellOrgManager"}}]},
      {"type": "layoutSection", "id": "aboutSection", "children": [{"type": "fieldSet", "id": "aboutFieldSet", "title": "About This Page", "children": [
        {"type": "richText", "id": "aboutRichText", "enabled": False, "value": INFO(
          "A pattern name is <b>APPLICATION:PREFIX:field:field:…</b>. Set the prefixes the application may use, then its fields "
          "in order (up to 7). Each field has a label (shown on the Add Pattern form) and a <b>rule</b>: pick a type such as "
          "<b>Capital letters</b>, a <b>length</b> (3, or a range such as 2-6), extra <b>characters</b> (e.g. - _) or the "
          "<b>values</b> of a list, and an <b>option</b> such as <i>may end with *</i>. The rule writes the <b>format</b> "
          "(a regular expression) for you; pick <b>Regular expression (advanced)</b> to edit the format by hand, and pick a rule "
          "type again to switch back. <b>Workday check</b> also requires the value to exist in Workday (Academic unit code: "
          "e.g. MATH, the Department of Mathematics). Leave the hint blank to use the rule's own description. "
          "Tick <b>Blank = any</b> when a field may be left empty (it becomes *). <b>Copy from</b> fills the prefixes and "
          "fields from another application. Existing patterns keep their names. An <b>inactive</b> application takes no new patterns.")}]}]},
      {"type": "layoutSection", "id": "appSection", "children": [{"type": "fieldSet", "id": "appFieldSet", "title": "Application", "children": [
        # an existing application's ID and name are shown, not edited (patterns are named after the ID)
        {"type": "text", "id": "appIdShownText", "label": "Application ID", "enabled": False, "visible": f"<% !{NEW} %>",
         "value": f"<% ({REC} ?? {{'appId': ''}}).appId ?? '' %>"},
        {"type": "dropdown", "id": "appIdDropdown", "label": "Application ID", "visible": f"<% {NEW} %>", "required": True,
         "helpText": "Applications in Workday that aren't set up here yet.",
         "values": "<% comsAppSetup.newAppOptions(existingOrgs.data, comsApplications.data) %>",
         "onChange": f"<%\n  let e = comsAppSetup.appIdError({CHOSEN}, comsApplications.data, {NEW});\n  if (e != '') {{ self.setError(e); }} else {{ self.clearError(); }}\n  {PREVIEW}\n%>"},
        {"type": "text", "id": "appNameText", "label": "Name", "required": f"<% {NEW} %>", "enabled": f"<% {NEW} %>",
         "value": f"<% ({REC} ?? {{'name': ''}}).name ?? '' %>",
         "onChange": "<%\n  let e = comsAppSetup.nameError((self.value ?? '').trim());\n  if (e != '') { self.setError(e); } else { self.clearError(); }\n%>"},
        # product owner 2026-11-04: where to reactivate (X:CLW was inactive by default: a yes/no field left unset is stored as no)
        {"type": "checkBox", "id": "appActiveCheckBox", "label": "Active",
         "helpText": "Untick to stop new patterns for this application (existing ones stay). Inactive applications are hidden from Add Pattern.",
         "value": f"<% ({REC} ?? {{'active': true}}).active != false %>"},
        # Add only: the list comes from Workday's X: application organizations, so a missing one is created in Workday first
        # (product owner 2026-11-04: "create a shell organization with X:META sub org type"). Add Shell Org can't do it:
        # it only adds <existing application>:<code> organizations, and the new one needs its own organization type.
        {"type": "richText", "id": "missingAppRichText", "enabled": False, "render": f"<% {NEW} %>", "value": (
          '<span style="color:#B45309;font-size:12px;font-weight:700">⚠ Application not in the list? </span>'
          '<span style="color:#374151;font-size:12px">The list shows applications that already have an organization in '
          'Workday and no pattern format here yet. For a new application, first set it up in Workday:<br>'
          '<b>1.</b> An organization type named after the application ID (e.g. <b>X:NEWAPP</b>), added by the Workday '
          'configuration team.<br>'
          '<b>2.</b> Its organization: <b>Create Custom Organization</b> with that type, code <b>X:NEWAPP</b> and '
          'organization subtype <b>X:META</b>.<br>'
          'Then reopen <b>Add Application</b> and pick it. (Add Shell Org adds organizations under an application '
          'that already exists, so it can\'t create this one.)</span>')}]}]},
      {"type": "layoutSection", "id": "formatSection", "children": [{"type": "fieldSet", "id": "formatFieldSet", "title": "Pattern Format", "children": [
        {"type": "dropdown", "id": "copyFromDropdown", "label": "Copy from",
         "helpText": "Fills the prefixes and fields below from another application. You can still change them.",
         "values": f"<% comsAppSetup.copyOptions(comsApplications.data, {APPID}) %>",
         # grid setRows (developer.workday.com "grid" methods: refreshes an editable grid's rows)
         "onChange": (f"<%\n  if (!empty(self.value)) {{\n    prefixesText.setValue(comsAppSetup.prefixText({SRC}));\n"
                      f"    fieldsGrid.setRows(comsAppSetup.fieldRows({SRC}));\n"
                      f"    exampleNameText.setValue(comsAppSetup.exampleName({APPID}, comsAppSetup.prefixText({SRC}), comsAppSetup.fieldRows({SRC})));\n  }}\n"
                      "  prefixesText.clearError();\n  fieldsCheckText.clearError();\n%>")},
        {"type": "text", "id": "prefixesText", "label": "Prefixes", "required": True, "placeholder": "e.g. ORG, or CP, PRIV for several",
         "value": f"<% comsAppSetup.prefixText({REC}) %>",
         "onChange": f"<%\n  let e = comsAppSetup.prefixError(self.value ?? '');\n  if (e != '') {{ self.setError(e); }} else {{ self.clearError(); }}\n  {PREVIEW}\n%>"},
        {"type": "text", "id": "fieldsCheckText", "label": "Field rules", "enabled": False,
         "value": f"<% 'Up to {MAX_FIELDS} fields, in the order they appear in the name. Add a row with +.' %>"},
        {"type": "grid", "id": "fieldsGrid", "label": "Fields", "rowVariableName": "fr",
         "onRowAdd": "<% " + FIELDS_TOUCHED + " %>", "onRowRemove": "<% " + FIELDS_TOUCHED + " %>",
         "rows": f"<% comsAppSetup.fieldRows({REC}) %>",
         "columns": [
           cell("colFieldLabel", "Label", "fieldLabel"),
           pick("colRule", "Rule", "ruleType", RULE_TYPES, "regex", RULE_CHANGED),
           dict(cell("colLength", "Length", "ruleLength"), cellTemplate=dict(cell("colLength", "Length", "ruleLength")["cellTemplate"], onChange=RULE_CHANGED)),
           dict(cell("colValues", "Characters or values", "ruleValues"), cellTemplate=dict(cell("colValues", "Characters or values", "ruleValues")["cellTemplate"], onChange=RULE_CHANGED)),
           pick("colOption", "Option", "ruleOption", RULE_OPTIONS, "none", RULE_CHANGED),
           # written by the rule; editable only in Regular expression mode
           dict(cell("colRegex", "Format (regular expression)", "regex"),
                cellTemplate=dict(cell("colRegex", "Format (regular expression)", "regex")["cellTemplate"], enabled="<% (fr.ruleType ?? 'regex') == 'regex' %>")),
           cell("colHint", "Hint", "hint"),
           cell("colExample", "Example", "example"),
           pick("colLookup", "Workday check", "lookup", LOOKUPS, "none", "<% " + FIELDS_TOUCHED + " %>"),
           dict(cell("colBlank", "Blank = any (*)", "blankIsWildcard", "checkBox"),
                cellTemplate=dict(cell("colBlank", "Blank = any (*)", "blankIsWildcard", "checkBox")["cellTemplate"], onChange=RULE_CHANGED)),
           cell("colOptional", "Optional at end", "optionalField", "checkBox")]},
        {"type": "readOnlyText", "id": "exampleNameText", "label": "Example Pattern Name",
         # page-load value from the saved record (the grid's rows aren't built yet at load); PREVIEW updates it as fields change
         "value": f"<% let s = comsAppSetup.schemaOf({REC}); empty(s) ? 'Appears here as you fill in the prefixes and fields.' : comsAppSetup.exampleName(({REC}).appId, s.prefixes.join(','), s.fields) %>"}]}]}]},
    "footer": FOOT}}
save('editAppPattern.pmd', edit)

# ---- AMD: tasks + flow back to the list ----
amd_name = [f for f in os.listdir(ROOT) if f.endswith('.amd')][0]
amd = load(amd_name)
for tid in ('appPatternSetup', 'editAppPattern'):
    if not any(t['id'] == tid for t in amd['tasks']):
        amd['tasks'].append({"id": tid, "routingPattern": "/" + tid, "page": {"id": tid}})
# Related action "Maintain Application Pattern" on each application record (model/MaintainApplicationPattern.task):
# its routePath /editAppPattern/{taskObjectId} gets the record's WID, which this route hands the page as
# queryParams.taskObjectId (same name as the task's, so App Builder's Page Route picker accepts it) (developer.workday.com "Add Tasks with Business Object Context"; Workday's
# capitalProjectPlanning sample uses the same two-route pattern).
amd['tasks'] = [t for t in amd['tasks'] if t['id'] != 'editAppPatternRecord'] + [
    {"id": "editAppPatternRecord", "routingPattern": "/editAppPattern/{taskObjectId}", "page": {"id": "editAppPattern"}}]
amd['flowDefinitions'] = [f for f in amd.get('flowDefinitions', []) if f['id'] != 'editAppPatternFlow'] + [{"id": "editAppPatternFlow", "flowSteps": [
    {"id": "editAppPatternStep", "taskId": "editAppPattern", "startsFlow": True, "transitions": [{"order": "a", "value": "appPatternSetupStep", "condition": "true"}]},
    {"id": "appPatternSetupStep", "taskId": "appPatternSetup", "endsFlow": True}]}]
amd['flowDefinitions'] = [f for f in amd['flowDefinitions'] if f['id'] != 'editAppPatternRecordFlow'] + [{"id": "editAppPatternRecordFlow", "flowSteps": [
    {"id": "editAppPatternRecordStep", "taskId": "editAppPatternRecord", "startsFlow": True, "transitions": [{"order": "a", "value": "appPatternSetupRecordStep", "condition": "true"}]},
    {"id": "appPatternSetupRecordStep", "taskId": "appPatternSetup", "endsFlow": True}]}]
save(amd_name, amd)
task = {"id": 15, "name": "MaintainApplicationPattern", "label": "Maintain Application Pattern",
        "securityDomains": [DOMAIN], "routePath": "/editAppPattern/{taskObjectId}", "businessObject": "COMSApplication"}
open(os.path.join(os.path.dirname(__file__), '..', 'model', 'MaintainApplicationPattern.task'), 'w').write(json.dumps(task, indent=2) + '\n')

# ---- entry points: a pill on the hub's Shell Organizations card and on Shell Org Manager's Quick Actions ----
for card in ('HomeShellOrgActionsCard.card', 'ShellOrgQuickActionsCard.card'):
    p = os.path.join('cards', card)
    d = load(p)
    pills = d['body']['pills']
    if not any(x.get('taskReference', {}).get('taskId') == 'appPatternSetup' for x in pills):
        pills.append({"label": "Maintain Application Pattern", "taskReference": {"taskId": "appPatternSetup"}})
    for x in pills:
        if x.get('taskReference', {}).get('taskId') == 'appPatternSetup': x['label'] = "Maintain Application Pattern"
    save(p, d)

print('Application Patterns pages written')
