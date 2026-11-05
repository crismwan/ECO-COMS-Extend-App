#!/usr/bin/env python3
"""Add New Shell Organization: X:META organizations for a new application (product owner 2026-11-05:
"Application ID should not be required for X:META org sub type because it could be a net new application.
And the organization code should contain X: as the prefix"). Idempotent; runs after build_schema_pattern.py.

* Organization Subtype comes first, because it decides whether Application is needed.
* X:SHELL: Application required.
* With an application (either subtype), the name always starts with its ID (product owner 2026-11-05): the code
  can be the part after it (ORG:ANY) or the full name (X:CLW:ORG:ANY); another X: prefix is refused.
* X:META: Application optional.
    - picked: as before, <application>:<code>.
    - left blank (a new application): the Organization Code is the whole name and must be X: plus one
      part, upper case, no spaces (e.g. X:NEWAPP). The code is also sent as the organization type
      (orgType), because each application has its own organization type named after its code; Workday
      rejects the request if that type doesn't exist yet.
* AddShellOrg re-checks the same rules (tools/patch_pattern_orchestrations.py, CheckOrgName).
"""
import json, os

P = os.path.join(os.path.dirname(__file__), '..', 'presentation', 'newShellOrg.pmd')
d = json.load(open(P))

META = "((!empty(orgSubtypeDropdown.value)) ? (orgSubtypeDropdown.selectedEntries[0].id == 'X:META') : false)"
APP = "((!empty(selectedApplicationId.value)) ? (selectedApplicationId.selectedEntries[0].descriptor ?? '') : '')"
PREVIEW = (f"let pa = {APP};\n  let pc = (organizationCode.value ?? '').trim();\n"
           f"  orgNamePreview.setValue(pa != '' ? (pc.startsWith(pa + ':') ? pc : (pa + ':' + pc)) : "
           f"({META} ? (pc != '' ? pc : 'Enter the new application code, e.g. X:NEWAPP') : 'Select an application above'));")
# error for a code under an existing application ('' when fine): the name must start with the application ID
APP_CODE_ERR = ("(oc == ac + ':' ? ('Add the part after ' + ac + ':, e.g. ORG:ANY.') : "
                "((oc.startsWith('X:') && !oc.startsWith(ac + ':')) ? ('With ' + ac + ' selected, the name must start with ' + ac + ':. Enter the part after it (e.g. ORG:ANY) or the full name (e.g. ' + ac + ':ORG:ANY).') : "
                "(oc.contains(' ') ? 'The code can\\'t contain spaces.' : '')))")
# error for a new application's code ('' when fine)
NEW_CODE_ERR = ("(!oc.startsWith('X:') ? 'A new application\\'s code starts with X:, e.g. X:NEWAPP.' : "
                "(oc.substring(2) == '' || oc.substring(2).contains(':') ? 'Use X: plus one part, e.g. X:NEWAPP.' : "
                "(oc.contains(' ') ? 'The code can\\'t contain spaces.' : "
                "(oc.upperCase() != oc ? 'Use upper case, e.g. X:NEWAPP.' : ''))))")


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


# 1. subtype first
kids = holder(d['presentation'], 'selectedApplicationId')
ids = [k.get('id') for k in kids]
if ids.index('orgSubtypeDropdown') > ids.index('selectedApplicationId'):
    st = kids.pop(ids.index('orgSubtypeDropdown'))
    kids.insert(ids.index('selectedApplicationId'), st)

st = find(d, 'orgSubtypeDropdown')
st['helpText'] = ("X:META for an application's meta organization (e.g. X:CLW), including a new application's. "
                  "X:SHELL for a shell organization roles are assigned on.")
st['onChange'] = ("<%\n  self.clearError();\n  organizationCode.clearError();\n"
                  f"  selectedApplicationId.setRequired(!{META});\n"
                  f"  if ({META}) {{ selectedApplicationId.clearError(); }}\n  {PREVIEW}\n%>")

app = find(d, 'selectedApplicationId')
app['required'] = f"<% !{META} %>"
app['helpText'] = ("Select the application this organization belongs to. "
                   "For X:META, leave it blank to add a new application's organization.")
app['onChange'] = f"<%\n  selectedApplicationId.clearError();\n  organizationCode.clearError();\n  {PREVIEW}\n%>"

code = find(d, 'organizationCode')
code['placeholder'] = "e.g. ORG:ANY, or X:NEWAPP for a new application"
code['helpText'] = ("With an application, the name starts with its ID: enter the part after it (ORG:ANY) or the full name (X:CLW:ORG:ANY). "
                    "X:META without an application: the new application's code, starting with X: (e.g. X:NEWAPP).")
code['guide']['text'] = ("With an application, the name always starts with its ID: enter the part after it or the full name "
                         "(ORG:ANY or X:CLW:ORG:ANY both give X:CLW:ORG:ANY). For a new application (subtype X:META, no application), enter its code "
                         "starting with X: (e.g. X:NEWAPP); its organization type of the same name must already exist in Workday. "
                         "No spaces. Must be unique.")
code['onChange'] = f"<%\n  self.clearError();\n  {PREVIEW}\n%>"

prev = find(d, 'orgNamePreview')
prev['value'] = (f"<% {APP} != '' ? ({APP} + ':' + (organizationCode.value ?? '')) : "
                 f"({META} ? 'Enter the new application code, e.g. X:NEWAPP' : 'Select an application above') %>")

# 2. About text
about = None
def walk(n):
    global about
    if isinstance(n, dict):
        if isinstance(n.get('value'), str) and 'Add a new Shell Organization to Workday.' in n['value']: about = n
        for v in n.values(): walk(v)
    elif isinstance(n, list):
        for v in n: walk(v)
walk(d['presentation'])
if about:
    about['value'] = ('<span style="color:#0055B7;font-size:12px;font-weight:700">ⓘ </span><span style="color:#374151;font-size:12px">'
                      'Add a new organization to Workday. Pick the subtype, the application and the Organization Code: the name is '
                      '<b>ApplicationCode:OrganizationCode</b>: with an application selected the name always starts with its ID '
                      '(enter ORG:ANY or X:CLW:ORG:ANY). For a <b>new application</b>, pick X:META, '
                      'leave Application blank and enter its code starting with <b>X:</b> (e.g. X:NEWAPP). Its organization type '
                      'of the same name must already exist in Workday.</span>')

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
  if (oc == '') {{
    organizationCode.setError('Organization Code is required.');
    valid = false;
  }} else {{
    let codeErr = ac != '' ? {APP_CODE_ERR} : (meta ? {NEW_CODE_ERR} : '');
    let orgName = ac != '' ? (oc.startsWith(ac + ':') ? oc : (ac + ':' + oc)) : oc;
    let dupes = (existingOrgs.data ?? []).filter(o => {{ o.code == orgName }});
    if (codeErr != '') {{
      organizationCode.setError(codeErr);
      valid = false;
    }} else if (dupes.size() > 0) {{
      let dupeName = (!empty(dupes[0].organizationByName)) ? (dupes[0].organizationByName.descriptor ?? orgName) : orgName;
      organizationCode.setError('An organization with this code already exists: ' + dupeName);
      valid = false;
    }}
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
    let lname = ac != '' ? (oc.startsWith(ac + ':') ? oc : (ac + ':' + oc)) : oc;
    let lot = ac != '' ? ac : oc;
    let lcode = ac != '' ? lname.substringAfter(ac + ':') : oc;
    launchAddShellOrg.invoke({{'cbw': selectedWorker.id ?? '', 'cb': (selectedWorker.descriptor ?? '').urlEncode(), 'ts': date:now().format("yyyy-MM-dd'T'HH:mm:ss'Z'").urlEncode(), 'ac': lot.urlEncode(), 'ot': lot.urlEncode(), 'st': orgSubtypeDropdown.selectedEntries[0].id, 'on': lname.urlEncode(), 'oc': lcode.urlEncode(), 'wid': selectedWorker.id ?? '', 'ed': effectiveDate.value.format('yyyy-MM-dd')}});
    let created = (verifyShellOrg.invoke({{'lim': '10000'}}).data ?? []).filter(o => {{ o.code == lname }}).size() > 0;
    if (!created) {{
      organizationCode.setError((ac == '' && meta) ? ('Workday rejected this request, so nothing was created. For a new application, check that the organization type ' + oc + ' exists in Workday.') : 'Workday rejected this request, so nothing was created. Check the values and try again.');
      valid = false;
    }}
  }}
  valid;
%>"""

open(P, 'w').write(json.dumps(d, indent=2, ensure_ascii=False) + '\n')
print('newShellOrg: subtype first; X:META may leave Application blank (code = X:NEWAPP, the whole name and type)')
