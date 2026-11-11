#!/usr/bin/env python3
"""Add New Shell Organization naming (product owner 2026-11-05). Idempotent; runs after build_schema_pattern.py.

Requests:
  "Application ID should not be required for X:META org sub type because it could be a net new application.
   And the organization code should contain X: as the prefix"
  "if an existing application is being selected when X:META is added, ensure the prefix is the application id.
   For completely new one without application id selected then start with X:"
  "if application id is used then the organization code should be enclosed in brackets after prefix similar to
   some application id structures"

Rules (one place: presentation/scripts/comsShellOrg.script, shared by the preview and OK):
* Organization Subtype comes first, because it decides whether Application is needed.
* X:SHELL: Application required; name APP:CODE (the full name APP:CODE may be typed; another X: prefix is refused).
* X:META with an application: name APP(CODE), like X:LLIS(CPE) (a bracketed application gives its base: X:BPMS(AOC)
  -> X:BPMS(NEW)). X:META without an application: the code as typed (any code, no spaces; 2026-11-06).
* For X:META the name is also the organization type: every application-level organization in Workday has an
  organization type of the same name (probe 2026-11-05), which must exist before the create.
* IORC_0037_XFD_SEC_Create_Application_Shell_Org's CheckOrgName re-checks the same rules (tools/patch_pattern_orchestrations.py).
* The launch no longer sends comsAppId (IORC_0037_XFD_SEC_Create_Application_Shell_Org doesn't use it), so the bracketed application ID isn't repeated
  in the query string the API gateway scores.
"""
import json, os

P = os.path.join(os.path.dirname(__file__), '..', 'presentation', 'newShellOrg.pmd')
d = json.load(open(P))

META = "((!empty(orgSubtypeDropdown.value)) ? (orgSubtypeDropdown.selectedEntries[0].id == 'X:META') : false)"
APP = "((!empty(selectedApplicationId.value)) ? (selectedApplicationId.selectedEntries[0].descriptor ?? '') : '')"
PREVIEW = f"orgNamePreview.setValue(comsShellOrg.preview({APP}, organizationCode.value ?? '', {META}));"
# the code's format is checked as it changes, and again when the subtype or application changes (2026-11-08: a lower-case
# code under X:META only showed its error at OK on Review & Submit, a step after the field)
CODECHECK = (f"let ce = (organizationCode.value ?? '').trim() == '' ? '' : comsShellOrg.codeError({APP}, organizationCode.value ?? '', {META});\n"
             "  if (ce == '') { organizationCode.clearError(); } else { organizationCode.setError(ce); }")


def find(n, wid):
    if isinstance(n, dict):
        if n.get('id') == wid: return n
        for v in n.values():
            r = find(v, wid)
            if r: return r
    elif isinstance(n, list):
        for v in n:
            r = find(v, wid)
            if r: return r


def holder(n, wid):
    if isinstance(n, dict):
        kids = n.get('children')
        if isinstance(kids, list) and any(isinstance(k, dict) and k.get('id') == wid for k in kids): return kids
        for v in n.values():
            r = holder(v, wid)
            if r is not None: return r
    elif isinstance(n, list):
        for v in n:
            r = holder(v, wid)
            if r is not None: return r


if 'comsShellOrg.script' not in d['include']:
    d['include'].append('comsShellOrg.script')

# launch URL: no comsAppId
for e in d['endPoints']:
    if e['name'] == 'launchAddShellOrg':
        e['url'] = e['url'].replace("'/IORC_0037_XFD_SEC_Create_Application_Shell_Org/launch?comsAppId=' + ac + '&orgType=' + ot", "'/IORC_0037_XFD_SEC_Create_Application_Shell_Org/launch?orgType=' + ot")

# one-code lookup for the duplicate and "was it created" checks (live 2026-11-10: the eager existingOrgs list didn't
# catch X:ADM:AAP:ANY on OK, so the checks ask WQL for that one code instead of searching a page list)
ORG_BY_CODE = {"name": "orgByCode", "baseUrlType": "workday-wql", "authType": "sso", "deferred": "true",
               "url": "<% 'data?limit=5&query=' + string:pathEncode('SELECT workdayID, code, organizationByName FROM topLevelOrganizations WHERE code = \\'' + c + '\\'') %>"}
if not any(e['name'] == 'orgByCode' for e in d['endPoints']):
    d['endPoints'].append(dict(ORG_BY_CODE))

# 1. subtype first
kids = holder(d['presentation'], 'selectedApplicationId')
ids = [k.get('id') for k in kids]
if ids.index('orgSubtypeDropdown') > ids.index('selectedApplicationId'):
    st = kids.pop(ids.index('orgSubtypeDropdown'))
    kids.insert(ids.index('selectedApplicationId'), st)

st = find(d, 'orgSubtypeDropdown')
st['helpText'] = ("X:META for an application-level organization: under an application it is APP(CODE), e.g. X:LLIS(CPE); "
                  "without one, a new application named by its code. X:SHELL for a shell organization roles are assigned on (APP:CODE).")
st['onChange'] = ("<%\n  self.clearError();\n"
                  f"  selectedApplicationId.setRequired(!{META});\n"
                  f"  if ({META}) {{ selectedApplicationId.clearError(); }}\n  {CODECHECK}\n  {PREVIEW}\n%>")

app = find(d, 'selectedApplicationId')
app['required'] = f"<% !{META} %>"
app['helpText'] = ("Select the application this organization belongs to. "
                   "For X:META, leave it blank to add a new application.")
app['onChange'] = f"<%\n  selectedApplicationId.clearError();\n  {CODECHECK}\n  {PREVIEW}\n%>"

code = find(d, 'organizationCode')
code['placeholder'] = "e.g. ORG:ANY, NEW, or NEWAPP"
code['helpText'] = ("X:SHELL: the part after the application (ORG:ANY gives X:CLW:ORG:ANY). "
                    "X:META with an application: the part in brackets, so NEW gives X:LLIS(NEW). "
                    "X:META without one: the new application code, used as typed.")
code['guide']['text'] = ("X:SHELL: enter the part after the application, or the full name (ORG:ANY or X:CLW:ORG:ANY both give "
                         "X:CLW:ORG:ANY). X:META with an application: enter the part that goes in brackets, so NEW gives X:LLIS(NEW). "
                         "X:META without an application: enter the new application code; it is used exactly as typed. "
                         "For X:META the organization type of the same name must already exist in Workday. No spaces. Must be unique.")
code['onChange'] = f"<%\n  {CODECHECK}\n  {PREVIEW}\n%>"

prev = find(d, 'orgNamePreview')
prev['value'] = f"<% comsShellOrg.preview({APP}, organizationCode.value ?? '', {META}) %>"

# 2. About text (match the original wording and every later version)
about = None
def walk(n):
    global about
    if isinstance(n, dict):
        v = n.get('value')
        if isinstance(v, str) and ('Add a new Shell Organization to Workday.' in v or 'Add a new organization to Workday.' in v): about = n
        for x in n.values(): walk(x)
    elif isinstance(n, list):
        for x in n: walk(x)
walk(d['presentation'])
if about:
    about['value'] = ('<span style="color:#0055B7;font-size:12px;font-weight:700">ⓘ </span><span style="color:#374151;font-size:12px">'
                      'Add a new organization to Workday. Pick the subtype first. <b>X:SHELL</b>: pick the application; the name is '
                      '<b>Application:Code</b> (e.g. X:CLW:ORG:ANY). <b>X:META</b> with an application: the name is '
                      '<b>Application(Code)</b>, for example X:LLIS(CPE). <b>X:META</b> without an application (a new application): enter its '
                      'code; it is used exactly as typed. For X:META, an organization type of the same name must already '
                      'exist in Workday.</span>')

# 3. OK checks and launch
d['onSubmit'] = f"""<%
  effectiveDate.clearError();
  orgSubtypeDropdown.clearError();
  organizationCode.clearError();
  selectedApplicationId.clearError();
  let valid = true;
  let meta = {META};
  let ac = {APP};
  let oc = (organizationCode.value ?? '').trim();
  if (empty(orgSubtypeDropdown.value)) {{
    orgSubtypeDropdown.setError('Pick the organization subtype: X:META or X:SHELL.');
    valid = false;
  }}
  if (ac == '' && !meta) {{
    selectedApplicationId.setError('Please select an application. Only X:META can be added without one (a new application).');
    valid = false;
  }}
  let codeErr = comsShellOrg.codeError(ac, oc, meta);
  let orgName = comsShellOrg.orgName(ac, oc, meta);
  let q = orgName.replace('\\'', '').replace('\\\\', '');
  let found = (codeErr == '' && q != '') ? (orgByCode.invoke({{'c': q}}).data ?? []) : [];
  if (codeErr != '') {{
    organizationCode.setError(codeErr);
    valid = false;
  }} else if (found.size() > 0) {{
    let dupe = found[0];
    let dupeName = (!empty(dupe.organizationByName)) ? (dupe.organizationByName.descriptor ?? orgName) : orgName;
    organizationCode.setError('An organization with this code already exists: ' + dupeName);
    valid = false;
  }}
  if (empty(effectiveDate.value)) {{
    effectiveDate.setError('Effective Date is required.');
    valid = false;
  }} else {{
    if (!comsValidations.isWeekday(effectiveDate.value)) {{
      effectiveDate.setError(comsValidations.errorWeekday());
      valid = false;
    }} else if (!comsValidations.isCurrentOrFutureYear(effectiveDate.value)) {{
      effectiveDate.setError(comsValidations.errorYear());
      valid = false;
    }}
  }}
  if (valid) {{
    let lname = comsShellOrg.orgName(ac, oc, meta);
    let lot = comsShellOrg.orgType(ac, oc, meta);
    let lcode = comsShellOrg.orgCode(ac, oc, meta);
    launchAddShellOrg.invoke({{'cbw': selectedWorker.id ?? '', 'cb': (selectedWorker.descriptor ?? '').urlEncode(), 'ts': date:now().format("yyyy-MM-dd'T'HH:mm:ss'Z'").urlEncode(), 'ot': lot.urlEncode(), 'st': orgSubtypeDropdown.selectedEntries[0].id, 'on': lname.urlEncode(), 'oc': lcode.urlEncode(), 'wid': selectedWorker.id ?? '', 'ed': effectiveDate.value.format('yyyy-MM-dd')}});
    let created = (orgByCode.invoke({{'c': lname.replace('\\'', '').replace('\\\\', '')}}).data ?? []).map(o => {{ o.code ?? '' }}).indexOf(lname) >= 0;
    if (!created) {{
      organizationCode.setError(meta ? ('Workday rejected this request, so nothing was created. Check that the organization type ' + lot + ' exists in Workday.') : 'Workday rejected this request, so nothing was created. Check the values and try again.');
      valid = false;
    }}
  }}
  valid;
%>"""

open(P, 'w').write(json.dumps(d, indent=2, ensure_ascii=False) + '\n')
print('newShellOrg: subtype first; X:SHELL APP:CODE, X:META APP(CODE) or a new application code as typed (comsShellOrg.script)')
