#!/usr/bin/env python3
"""Submit Assignable Role Request / AAA Role Request: choose what the role is enabled for first, then search only
that list (product owner 2026-11-05: "Yes continue" on "choose the type first, then search within it").

* New dropdown enabledForTypeDropdown before the two pickers: Functional Unit Hierarchy or Academic Unit. Left blank,
  the request is for the whole university (Academic Unit - University of British Columbia), as before.
* Only the matching picker shows; switching clears the other one, so "Cannot select both" can't happen any more.
* Nothing that is saved changes: the request still gets the same enabledFor / FUH / Academic Unit fields from the
  two pickers, and AAA Role Request still builds the role name from which one is picked.
* OK: a type picked but nothing searched and picked gives an error on that picker.

Rollback: `python3 tools/enabled_for_choice.py --off` removes the dropdown and puts both pickers back as they were
(always visible). Remove the step from rebuild_all.sh to keep it off.
"""
import json, os, re, sys

R = os.path.join(os.path.dirname(__file__), '..', 'presentation')
PAGES = ['assignableRoleManager', 'adminProvisioning']
OFF = '--off' in sys.argv
TYPE = "((!empty(enabledForTypeDropdown.value)) ? enabledForTypeDropdown.selectedEntries[0].id : '')"
UNI = 'Academic Unit - University of British Columbia'
MARK = '/* enabled-for choice */'
MARK_END = '/* enabled-for choice end */'

HELP_OLD = '<b>Functional Unit Hierarchy</b>: Limits where the role applies to one Functional Unit Hierarchy. Pick either an FUH or an Academic Unit, not both. Leave both empty for the whole university (Academic Unit - University of British Columbia).<br/><b>Academic Unit</b>: Limits where the role applies to one Academic Unit. Pick either an Academic Unit or an FUH, not both. Leave both empty for the whole university.'
HELP_NEW = '<b>Enabled For</b>: Limits where the role applies. Pick Functional Unit Hierarchy or Academic Unit, then search for one in the box that appears. Leave it blank for the whole university (Academic Unit - University of British Columbia).<br/><b>Applies To</b>: Shows where the role will apply.'


def texts(n, a, b):
    """Replace help text a with b in every string of the page (both directions, for --off)."""
    if isinstance(n, dict):
        for k, v in n.items():
            if isinstance(v, str) and a in v: n[k] = v.replace(a, b)
            else: texts(v, a, b)
    elif isinstance(n, list):
        for v in n: texts(v, a, b)


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


for page in PAGES:
    p = os.path.join(R, page + '.pmd')
    d = json.load(open(p))
    kids = holder(d['presentation'], 'fuhPicker')
    byid = {k.get('id'): k for k in kids if isinstance(k, dict)}
    fuh, au = byid['fuhPicker'], byid['academicUnitPicker']
    kids[:] = [k for k in kids if not (isinstance(k, dict) and k.get('id') == 'enabledForTypeDropdown')]
    for w in (fuh, au):
        w.pop('visible', None)
    disp = byid.get('enabledForDisplay')
    if disp is not None: disp['label'] = 'Enabled For' if OFF else 'Applies To'
    if OFF: texts(d['presentation'], HELP_NEW, HELP_OLD)
    else: texts(d['presentation'], HELP_OLD, HELP_NEW)
    # remove an earlier copy of the OK check (idempotent)
    d['onSubmit'] = re.sub(r'\n  ' + re.escape(MARK) + r'\n.*?' + re.escape(MARK_END) + r'\n', '\n', d['onSubmit'], flags=re.S)
    if not OFF:
        # role name (AAA page only): same wording as the pickers' own onChange
        role = ''
        if page == 'adminProvisioning':
            role = ("  let appDesc = !empty(applicationDropdown.value) ? applicationDropdown.selectedEntries[0].descriptor : '';\n"
                    "  generatedRoleName.clearError();\n"
                    "  if (!empty(appDesc)) {\n"
                    "    generatedRoleName.setValue(keepFuh ? ('Organizations and Roles Assignment Administrator (' + appDesc + ', Functional Org)') :\n"
                    "      (keepAu ? ('Organizations and Roles Assignment Administrator (' + appDesc + ', Academic Unit)') :\n"
                    "        ('Organizations and Roles Assignment Administrator (' + appDesc + ')')));\n  }\n")
        drop = {
            "type": "dropdown", "id": "enabledForTypeDropdown", "label": "Enabled For",
            "instanceList": [{"id": "FUH", "descriptor": "Functional Unit Hierarchy"},
                             {"id": "AU", "descriptor": "Academic Unit"}],
            "helpText": f"Pick what the role is enabled for, then search for it below. Leave blank for the whole university ({UNI}).",
            "onChange": ("<%\n  let t = " + TYPE.replace('enabledForTypeDropdown', 'self') + ";\n"
                         "  fuhPicker.setVisible(t == 'FUH');\n  academicUnitPicker.setVisible(t == 'AU');\n"
                         "  if (t != 'FUH') { fuhPicker.setValue([]); }\n  if (t != 'AU') { academicUnitPicker.setValue([]); }\n"
                         "  fuhPicker.clearError();\n  academicUnitPicker.clearError();\n"
                         "  let keepFuh = t == 'FUH' && !empty(fuhPicker.value);\n  let keepAu = t == 'AU' && !empty(academicUnitPicker.value);\n"
                         "  enabledForWidBinding.setValue(keepFuh ? fuhPicker.value[0] : (keepAu ? academicUnitPicker.value[0] : ''));\n"
                         f"  enabledForDisplay.setValue(keepFuh ? fuhPicker.selectedEntries[0].descriptor : (keepAu ? academicUnitPicker.selectedEntries[0].descriptor : '{UNI}'));\n"
                         + role + "%>")}
        kids.insert(kids.index(fuh), drop)
        fuh['visible'] = f"<% {TYPE} == 'FUH' %>"
        au['visible'] = f"<% {TYPE} == 'AU' %>"
        check = (f"\n  {MARK}\n"
                 f"  if ({TYPE} == 'FUH' && empty(fuhPicker.value)) {{\n"
                 "    fuhPicker.setError('Search for and pick a Functional Unit Hierarchy, or clear Enabled For to use the whole university.');\n    valid = false;\n  }\n"
                 f"  if ({TYPE} == 'AU' && empty(academicUnitPicker.value)) {{\n"
                 "    academicUnitPicker.setError('Search for and pick an Academic Unit, or clear Enabled For to use the whole university.');\n    valid = false;\n  }\n"
                 f"  {MARK_END}\n  valid;\n%>")
        body = d['onSubmit'].rstrip()
        assert body.endswith('valid;\n%>'), page
        body = body[:-len('valid;\n%>')].rstrip() + check
        # the checks above set errors on the pickers: clear them first (OK errors persist otherwise)
        for w in ('fuhPicker', 'academicUnitPicker'):
            if f'{w}.clearError();' not in body.split('let valid')[0]:
                body = body.replace('<%\n', f'<%\n  {w}.clearError();\n', 1)
        d['onSubmit'] = body
    open(p, 'w').write(json.dumps(d, indent=2, ensure_ascii=False) + '\n')
    print(f"{page}: Enabled For choice {'removed' if OFF else 'added'}")
