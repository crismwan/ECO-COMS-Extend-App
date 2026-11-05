#!/usr/bin/env python3
"""AAA Role Request uses the full application ID (product owner 2026-11-05: "Use the full ID: new requests will build
'...(X:BPMS(COMS))', matching the existing roles").

The Application list on adminProvisioning reduced a bracketed application to its inner code (X:BPMS(COMS) -> COMS),
so the page built "Organizations and Roles Assignment Administrator (COMS)" while the AAA roles in Workday are named
"...(X:BPMS(COMS))" and "...(X:BPMS(ODMT))", and the duplicate check (exact name) missed them. Now a bracketed
application keeps its full ID up to the closing bracket (X:BPMS(COMS), X:LLIS(CPE)); X:APP:... and plain codes are
unchanged. The role name, the request's application / shellOrgCode and the duplicate check all follow, because they
all read the dropdown's descriptor. Only this page: the shared parseAppCode (comsValidations.script) still serves the
shell-org pages.

Rollback: `python3 tools/aaa_full_app_id.py --off`.
"""
import json, os, sys

P = os.path.join(os.path.dirname(__file__), '..', 'presentation', 'adminProvisioning.pmd')
OFF = '--off' in sys.argv
SHORT = "code.substringAfter('(').substringBefore(')')"
FULL = "(code.substringBefore(')') + ')')"


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


d = json.load(open(P))
w = find(d['presentation'], 'applicationDropdown')
a, b = (FULL, SHORT) if OFF else (SHORT, FULL)
assert (a in w['values']) or (b in w['values']), 'application list script changed; update this step'
w['values'] = w['values'].replace(a, b)
open(P, 'w').write(json.dumps(d, indent=2, ensure_ascii=False) + '\n')
print(f"adminProvisioning: Application list {'short codes' if OFF else 'full application IDs'}")
