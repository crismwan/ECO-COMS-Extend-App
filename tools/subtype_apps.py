#!/usr/bin/env python3
"""Organizations by subtype, applications by organization type (product owner 2026-11-06).

Until now the app found its organizations by an "X:" in the code and worked out the application by parsing the code
(X:CLW in X:CLW:ORG:ANY). An application or organization can now be named anything, so:

- **Which organizations:** every organization whose subtype is X:META or X:SHELL (WQL `subtype in (...)`).
- **Which application:** the organization's type (`type1`). Every application has an organization type of its own
  name; its own organization and every organization under it carry that type (probe 2026-11-06: all 614 organizations
  have exactly one type, matching the parsed application for all but one mis-named test pattern, whose type is right).
- **Which roles:** roles enabled for one of those organization types (the role data source has no subtype field), so
  the role query gets the type WIDs from a small `appTypes` list on each page that lists roles.

Runs near the end of rebuild_all (after every page builder). Every rewrite is plain text and idempotent.
"""
import glob, json, os, re, sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'presentation')
# Earlier build steps patch pages in place and check their own text, which this step then rewrites. So this step keeps
# each page as it found it in tools/subtype_src/, and `--restore` (first in rebuild_all) puts those back before they run.
SRC = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'subtype_src')
if '--restore' in sys.argv:
    for p in glob.glob(os.path.join(SRC, '**', '*'), recursive=True):
        if os.path.isfile(p):
            dst = os.path.join(ROOT, os.path.relpath(p, SRC))
            open(dst, 'w', encoding='utf-8').write(open(p, encoding='utf-8').read())
    print('subtype_apps --restore: pages as the earlier build steps left them')
    sys.exit(0)
import shutil
shutil.rmtree(SRC, ignore_errors=True)
def keep(p):
    dst = os.path.join(SRC, os.path.relpath(p, ROOT))
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    if not os.path.exists(dst):
        shutil.copyfile(p, dst)
# The app's organizations are found by the NAMES of their subtypes and type, not by WIDs: a WID differs from tenant to
# tenant (user, 2026-11-10). WQL can't filter an instance field by name (probe 2026-11-10: `subtype in (X:SHELL)` and
# `Organization_Subtype_Name = ...` are refused; only WIDs resolve), so each list is two steps: a tiny GROUP BY lookup
# returns every subtype (or type) with its WID (34 / 41 rows), the page keeps the WIDs whose descriptor matches, and the
# real query takes them as a parameter. No match gives `in ()`, which WQL answers with no rows (no error).
SUBTYPE_NAMES = ['X:META', 'X:SHELL']
FUH_TYPE_NAME = 'Functional Unit Hierarchy'
SUBTYPES = '<% subtypes %>'
def _match(field, names):
    return ' || '.join(f"r.{field}.descriptor == '{n}'" for n in names)
# script text: the matching WIDs, comma-separated
SUB_IDS = (f"(orgSubtypes.data ?? []).filter(r => {{ empty(r.subtype) ? false : ({_match('subtype', SUBTYPE_NAMES)}) }})"
           ".map(r => { r.subtype.id }).join(',')")
FUH_IDS = (f"(orgTypes.data ?? []).filter(r => {{ empty(r.organizationTypesPrimary) ? false : ({_match('organizationTypesPrimary', [FUH_TYPE_NAME])}) }})"
           ".map(r => { r.organizationTypesPrimary.id }).join(',')")
NOT_AAA = "roleName not contains 'Organizations and Roles Assignment Administrator'"
ROLE_SEL = ('SELECT role, enabledForOrganizationTypes, roleAssignments{organization, workersAssigned, '
            'cf_ZCF_EE_RoleAssignedToAsPositionRestrictions} as roleAssignments FROM assignableRoles')

# ---- WQL query components -------------------------------------------------------------------------------------------
QUERIES = {
    'orgSubtypes': {'id': 'orgSubtypes', 'query':
        'SELECT subtype, COUNT(workdayID) FROM topLevelOrganizations GROUP BY subtype'},
    'orgTypes': {'id': 'orgTypes', 'query':
        'SELECT organizationTypesPrimary, COUNT(workdayID) FROM customOrganizations GROUP BY organizationTypesPrimary'},
    'allShellOrgs': {'id': 'allShellOrgs', 'parameters': ['subtypes'], 'query':
        f'SELECT workdayID, organizationByName, code, cf_active1, type1 FROM topLevelOrganizations WHERE subtype in ({SUBTYPES})'},
    'customOrganizations': {'id': 'customOrganizations', 'parameters': ['subtypes'], 'query':
        f'SELECT workdayID, organizationByName, code, type1 FROM topLevelOrganizations WHERE subtype in ({SUBTYPES})'},
    'appTypes': {'id': 'appTypes', 'parameters': ['subtypes'], 'query':
        f'SELECT workdayID, type1 FROM topLevelOrganizations WHERE subtype in ({SUBTYPES})'},
    'allShellAssignableRolesinTenant': {'id': 'allShellAssignableRolesinTenant', 'parameters': ['types'], 'query':
        f'{ROLE_SEL} WHERE enabledForOrganizationTypes in (<% types %>) AND {NOT_AAA}'},
    'allAAArolesinTenant': {'id': 'allAAArolesinTenant', 'query':
        f"{ROLE_SEL} WHERE roleName contains 'Organizations and Roles Assignment Administrator'"},
}
for name, q in QUERIES.items():
    p = os.path.join(ROOT, 'wqlQueries', name + '.wqlquery')
    open(p, 'w', encoding='utf-8').write(json.dumps(q, indent=2) + '\n')

# The type WIDs of the applications, from any list of organizations that carries type1.
def types_of(ep):
    return (f"<% let ts = ({ep}.data ?? []).map(o => {{ (o.type1 ?? []).size() > 0 ? o.type1[0].id : '' }})"
            f".filter(t => {{ t != '' }}).distinct(); ts.size() > 0 ? ts.join(',') : 'none' %>")

def _wql_ep(name, params=None):
    q = {"queryId": name}
    if params:
        q["parameters"] = params
    return {"name": name, "baseUrlType": "workday-wql", "url": "data", "authType": "sso", "bestEffort": "true",
            "wqlQuery": q, "failOnStatusCodes": [{"code": 400}, {"code": 429}]}
APP_TYPES_EP = _wql_ep("appTypes", {"subtypes": f"<% {SUB_IDS} %>"})

# The application of an organization record (inline in pages): its type, else its code.
APP_OF = "((org.type1 ?? []).size() > 0 ? org.type1[0].descriptor : org.code)"

# ---- text rewrites (old -> new), applied to every page and script ------------------------------------------------------
REWRITES = [
    # Assignable Role Request: the application of the chosen organization is its organization type (was parsed from the
    # code, which cut a bracketed application to its inner code: X:BPMS(COMS) -> COMS)
    ("    let code = org.code;\n    let appCode = code.contains('(') ?\n      code.substringAfter('(').substringBefore(')') :\n"
     "      (code.substringAfter(':').contains(':') ?\n        code.substringBefore(':') + ':' + code.substringAfter(':').substringBefore(':') :\n        code);\n"
     "    if (!appCodes.contains(appCode)) {",
     "    let code = org.code;\n    let appCode = ((org.type1 ?? []).size() > 0 ? org.type1[0].descriptor : org.code);\n"
     "    if (!appCodes.contains(appCode)) {"),
    ("              let appCode = orgCode.contains('(') ?\n                orgCode.substringAfter('(').substringBefore(')') :\n"
     "                (orgCode.substringAfter(':').contains(':') ?\n                  orgCode.substringBefore(':') + ':' + orgCode.substringAfter(':').substringBefore(':') :\n"
     "                  orgCode);\n              let matched = shellOrgPatterns.data.filter(o => {\n                let c = o.code;\n"
     "                let ac = c.contains('(') ?\n                  c.substringAfter('(').substringBefore(')') :\n"
     "                  (c.substringAfter(':').contains(':') ?\n                    c.substringBefore(':') + ':' + c.substringAfter(':').substringBefore(':') :\n"
     "                    c);\n                ac == appCode;\n              });",
     "              let sel = shellOrgPatterns.data.filter(o => { o.code == orgCode });\n"
     "              let appCode = (sel.size() > 0 && (sel[0].type1 ?? []).size() > 0) ? sel[0].type1[0].descriptor : orgCode;\n"
     "              let matched = shellOrgPatterns.data.filter(o => { ((o.type1 ?? []).size() > 0 ? o.type1[0].descriptor : o.code) == appCode });"),
    # Change Status: the application (orgType / comsAppId in the launch) is the organization's type, URL-encoded
    # (a code with a space failed the launch: "Illegal character in query", live 2026-11-06)
    ("let ot = oc.substringBefore(':') + ':' + oc.substringAfter(':').substringBefore(':');",
     "let ti = (appTypes.data ?? []).map(o => { o.workdayID ?? '' }).indexOf(queryParams.orgId ?? ''); "
     "let ot = ti < 0 ? (oc.contains('(') ? (oc.substringBefore(')') + ')') : (oc.substringAfter(':').contains(':') ? (oc.substringBefore(':') + ':' + oc.substringAfter(':').substringBefore(':')) : oc)) "
     ": ((((appTypes.data ?? []).get(ti)).type1 ?? []).size() > 0 ? ((appTypes.data ?? []).get(ti)).type1[0].descriptor : oc);"),
    ("'ot': ot, 'vo'", "'ot': ot.urlEncode(), 'vo'"),
    # run-and-verify readbacks (Add Shell Org, Add Pattern): find the new organization among the subtype ones
    ("WHERE%20code%20contains%20%27X%3A%27", f"WHERE%20subtype%20in%20(' + {SUB_IDS} + ')"),
    # filters that only kept X: organizations: the list is already limited by subtype
    ("(o.code ?? '').startsWith('X:') && ", ""),
    ("o.code.startsWith('X:') && ", ""),
    ("(p.code ?? '').startsWith('X:') && ", ""),
    # Shell Org Manager: one application's organizations, or all of them
    ("(o.code ?? '').startsWith((empty(queryParams.appCode) ? 'X:' : queryParams.appCode + ':'))",
     "(empty(queryParams.appCode) || (o.code ?? '').startsWith(queryParams.appCode + ':'))"),
    ("(o.code ?? '').startsWith(empty(queryParams.appCode) ? 'X:' : queryParams.appCode + ':PATTERN')",
     "(empty(queryParams.appCode) || (o.code ?? '').startsWith(queryParams.appCode + ':PATTERN'))"),
    ("(empty(queryParams.appCode) ? ra.organization.descriptor.startsWith('X:') : (",
     "(empty(queryParams.appCode) ? true : ("),
    ("ra.organization.descriptor.startsWith(empty(queryParams.appCode) ? 'X:' : queryParams.appCode)",
     "(empty(queryParams.appCode) || ra.organization.descriptor.startsWith(queryParams.appCode))"),
    # Bulk Edit: the applications that have role assignments: each assignment's organization type (appTypes list)
    ("list:flatten((shellRoles.data ?? []).map(r => { (r.roleAssignments ?? []).filter(ra => { ra.organization != null && "
     "ra.organization.descriptor.startsWith('X:') }).map(ra => { 'X:' + ra.organization.descriptor.substringAfter(':')"
     ".substringBefore(':').substringBefore(' ') }) })).distinct().sort()",
     "let ids = (appTypes.data ?? []).map(o => { o.workdayID ?? '' }); let tys = (appTypes.data ?? []).map(o => { (o.type1 ?? []).size() > 0 ? o.type1[0].descriptor : '' }); "
     "list:flatten((shellRoles.data ?? []).map(r => { (r.roleAssignments ?? []).filter(ra => { ra.organization != null }).map(ra => { let i = ids.indexOf(ra.organization.id); i < 0 ? '' : tys.get(i) }) }))"
     ".filter(a => { a != '' }).distinct().sort()"),
    # Add Shell Org and AAA pages: the application picker lists organization types
    ("  for (var org : (existingOrgs.data ?? [])) {\n    let code = org.code;\n    let appCode = code.substringAfter(':').contains(':') ?\n"
     "      code.substringBefore(':') + ':' + code.substringAfter(':').substringBefore(':') :\n      code;\n",
     f"  for (var org : (existingOrgs.data ?? [])) {{\n    let code = org.code;\n    let appCode = {APP_OF};\n"),
    ("  for (var org : customOrganizations.data) {\n    let code = org.code;\n    let appCode = code.contains('(') ?\n"
     "      (code.substringBefore(')') + ')') :\n      (code.substringAfter(':').contains(':') ?\n"
     "        code.substringBefore(':') + ':' + code.substringAfter(':').substringBefore(':') :\n        code);\n",
     f"  for (var org : (customOrganizations.data ?? [])) {{\n    let code = org.code;\n    let appCode = {APP_OF};\n"),
    # Audit Log: the Application column for records named after an organization or role
    ("let n = (logEntry.coName ?? '').startsWith('X:') ? logEntry.coName : (logEntry.roleName ?? ''); "
     "n.startsWith('X:') ? (n.substringBefore(':') + ':' + n.substringAfter(':').substringBefore(':')) : ''",
     "let n = !empty(logEntry.coName) ? logEntry.coName : (logEntry.roleName ?? ''); "
     "n.contains('(') ? (n.substringBefore(')') + ')') : (n.contains(':') ? (n.substringAfter(':').contains(':') && n.startsWith('X:') "
     "? (n.substringBefore(':') + ':' + n.substringAfter(':').substringBefore(':')) : n.substringBefore(':')) : n)"),
]

SCRIPT_REWRITES = {
    'comsAppIndex.script': [
        ("var shortOf = function(app) {\n  app.contains('(') ? app.substringAfter('(').substringBefore(')') : app.substringAfter('X:');\n};",
         "/* The application of an organization record: its organization type (subtype design, 2026-11-06), else its code. */\n"
         "var appOfOrg = function(o) {\n  (o.type1 ?? []).size() > 0 ? o.type1[0].descriptor : appOf(o.code ?? '');\n};\n\n"
         "var shortOf = function(app) {\n  app.contains('(') ? app.substringAfter('(').substringBefore(')') : (app.startsWith('X:') ? app.substringAfter('X:') : app);\n};"),
        ("base.substringAfter('X:') : 'Standalone'", "(base.startsWith('X:') ? base.substringAfter('X:') : base) : 'Standalone'"),
        ("(orgs ?? []).filter(o => { (o.code ?? '').startsWith('X:') }).map(o => { { 'c': o.code, 'a': appOf(o.code), ",
         "(orgs ?? []).map(o => { { 'c': o.code, 'a': appOfOrg(o), "),
        ("(recs ?? []).map(r => { r.appId ?? '' }).filter(x => { x.startsWith('X:') })", "(recs ?? []).map(r => { r.appId ?? '' }).filter(x => { x != '' })"),
        ("let xs = (orgs ?? []).filter(o => { (o.code ?? '').startsWith('X:') });", "let xs = (orgs ?? []);"),
    ],
    'comsPatterns.script': [
        ("let fromOrgs = (orgs ?? []).filter(o => { (o.code ?? '').startsWith('X:') }).map(o => { o.code.substringAfter(':').contains(':') "
         "? ('X:' + o.code.substringAfter(':').substringBefore(':')) : o.code });",
         "let fromOrgs = (orgs ?? []).map(o => { (o.type1 ?? []).size() > 0 ? o.type1[0].descriptor : (o.code ?? '') }).filter(c => { c != '' });"),
    ],
    'comsAppSetup.script': [
        ("/* Application codes from Workday's X: organizations (as on Add Shell Org) that have no record here yet. */",
         "/* Application codes (organization types of the X:META / X:SHELL organizations, as on Add Shell Org) with no record here yet. */"),
        ("  (orgs ?? []).map(o => { let c = o.code ?? ''; c.substringAfter(':').contains(':') ? (c.substringBefore(':') + ':' + "
         "c.substringAfter(':').substringBefore(':')) : c })\n    .filter(c => { c.startsWith('X:') && !have.contains(c) })",
         "  (orgs ?? []).map(o => { (o.type1 ?? []).size() > 0 ? o.type1[0].descriptor : (o.code ?? '') })\n"
         "    .filter(c => { c != '' && !have.contains(c) })"),
    ],
    'comsInsights.script': [
        ("var isShellOrg = function(o) {\n  ('' + (o.code ?? '')).startsWith('X:') && !('' + (o.code ?? '')).contains(':PATTERN');\n};",
         "var isShellOrg = function(o) {\n  !('' + (o.code ?? '')).contains(':PATTERN');\n};"),
        ("var isPattern = function(o) {\n  ('' + (o.code ?? '')).startsWith('X:') && ('' + (o.code ?? '')).contains(':PATTERN');\n};",
         "var isPattern = function(o) {\n  ('' + (o.code ?? '')).contains(':PATTERN');\n};"),
    ],
}

changed = []
for p in sorted(glob.glob(os.path.join(ROOT, '*.pmd')) + glob.glob(os.path.join(ROOT, 'scripts', '*.script'))):
    t = open(p, encoding='utf-8').read()
    n = t
    if p.endswith('.pmd'):
        # the rewrites are written as script text; in a .pmd that text sits inside JSON strings
        for old, new in REWRITES:
            n = n.replace(json.dumps(old)[1:-1], json.dumps(new)[1:-1])
    else:
        for old, new in REWRITES + SCRIPT_REWRITES.get(os.path.basename(p), []):
            n = n.replace(old, new)
    if n != t:
        keep(p)
        open(p, 'w', encoding='utf-8').write(n)
        changed.append(os.path.basename(p))

# ---- role lists: query by application organization type -------------------------------------------------------------
for p in sorted(glob.glob(os.path.join(ROOT, '*.pmd'))):
    d = json.load(open(p, encoding='utf-8'))
    eps = d.get('endPoints', [])
    roles = [e for e in eps if (e.get('wqlQuery') or {}).get('queryId') == 'allShellAssignableRolesinTenant']
    if not roles:
        if 'appTypes.data' in json.dumps(d) and not any(e.get('name') == 'appTypes' for e in eps):
            keep(p)
            eps.insert(0, dict(APP_TYPES_EP))
            open(p, 'w', encoding='utf-8').write(json.dumps(d, indent=2, ensure_ascii=False) + '\n')
        continue
    orgs = next((e['name'] for e in eps if (e.get('wqlQuery') or {}).get('queryId') in ('allShellOrgs', 'customOrganizations')), None)
    if not orgs:
        if not any(e.get('name') == 'appTypes' for e in eps):
            eps.insert(eps.index(roles[0]), dict(APP_TYPES_EP))
        orgs = 'appTypes'
    keep(p)
    for e in roles:
        e['wqlQuery']['parameters'] = {'types': types_of(orgs)}
    open(p, 'w', encoding='utf-8').write(json.dumps(d, indent=2, ensure_ascii=False) + '\n')
    if os.path.basename(p) not in changed:
        changed.append(os.path.basename(p))

# ---- nothing may still tell applications apart by an X: prefix ------------------------------------------------------
left = []
pat = re.compile(r"startsWith\('X:'\)(?! \?)|startsWith\(\(?empty\(queryParams\.appCode\) \? 'X:'|contains 'X:'|%27X%3A%27")
for p in glob.glob(os.path.join(ROOT, '*.pmd')) + glob.glob(os.path.join(ROOT, 'scripts', '*.script')) + glob.glob(os.path.join(ROOT, 'wqlQueries', '*')):
    for m in pat.finditer(open(p, encoding='utf-8').read()):
        left.append(os.path.basename(p))
ALLOWED = {'comsShellOrg.script', 'comsInsights.script'}  # typed-name check; request text with an X: code
bad = sorted(set(left) - ALLOWED)
if bad:
    sys.exit('subtype_apps: X: prefix tests left in ' + ', '.join(bad))
# ---- by name, not WID: subtype / type lookups on every page that needs them -------------------------------------------
NEEDS_SUBTYPES = ('allShellOrgs', 'customOrganizations', 'appTypes')
FUH_WID = 'b40d8b016367100175b147f364840000'
for p in sorted(glob.glob(os.path.join(ROOT, '*.pmd'))):
    t = open(p, encoding='utf-8').read()
    n = t.replace(f'type1 in ({FUH_WID})', f"type1 in (' + {FUH_IDS} + ')")
    d = json.loads(n)
    eps = d.get('endPoints', [])
    for e in eps:
        q = e.get('wqlQuery') or {}
        if q.get('queryId') in NEEDS_SUBTYPES:
            q.setdefault('parameters', {})['subtypes'] = f'<% {SUB_IDS} %>'
    body = json.dumps(d)
    names = [e.get('name') for e in eps]
    for ep, ref in (('orgTypes', 'orgTypes.data'), ('orgSubtypes', 'orgSubtypes.data')):
        if ref in body and ep not in names:
            eps.insert(0, _wql_ep(ep))
    n2 = json.dumps(d, indent=2, ensure_ascii=False) + '\n'
    if n2 != t:
        keep(p)
        open(p, 'w', encoding='utf-8').write(n2)
        if os.path.basename(p) not in changed:
            changed.append(os.path.basename(p))

# Change Status guard (orchestration): look the subtype WIDs up by name, then list the X:META / X:SHELL organizations
ORCH = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'orchestration')
op = os.path.join(ORCH, 'IORC_0037_XFD_SEC_Change_Shell_Org_Status.orchestration')
od = json.load(open(op, encoding='utf-8'))
def _node_lists(x):
    if isinstance(x, dict):
        for k, v in x.items():
            if k == 'nodes' and isinstance(v, dict) and isinstance(v.get('_value'), list):
                yield v['_value']
            yield from _node_lists(v)
    elif isinstance(x, list):
        for v in x:
            yield from _node_lists(v)
import copy
def _name(nd):
    return ((nd.get('_value') or {}).get('name') or {}).get('_value')
for nodes in _node_lists(od):
    idx = next((i for i, nd in enumerate(nodes) if _name(nd) == 'LookupShellOrgs'), None)
    if idx is None:
        continue
    if not any(_name(nd) == 'LookupSubtypes' for nd in nodes):
        nn = copy.deepcopy(nodes[idx])
        nn['_value']['name']['_value'] = 'LookupSubtypes'
        nodes.insert(idx, nn)
        idx += 1
    look = next(nd for nd in nodes if _name(nd) == 'LookupSubtypes')
    look['_value']['path']['_value']['source']['_value'] = (
        '"/wql/v1/data?limit=1000&query=SELECT%20subtype%2C%20COUNT(workdayID)%20FROM%20topLevelOrganizations%20GROUP%20BY%20subtype"')
    look['_value']['notes'] = {"_type": ["List", "Note"], "_value": [{"_type": "Note", "_value": {
        "key": {"_type": "String", "_value": "description"},
        "value": {"_type": "String", "_value": "Every organization subtype with its WID, so the next step can find X:META and X:SHELL by name (WIDs differ between tenants)"}}}]}
    sub = lambda nm: f"data.LookupSubtypes.response.asJSON().stringAtJsonPathWithDefault(\"$.data[?(@.subtype.descriptor == '{nm}')].subtype.id\", \"\")"
    m, sh = sub(SUBTYPE_NAMES[0]), sub(SUBTYPE_NAMES[1])
    ids = f'(if ({m}.isEmpty()) {sh} else (if ({sh}.isEmpty()) {m} else {m}.append("%2C").append({sh})))'
    nodes[idx]['_value']['path']['_value']['source']['_value'] = (
        '"/wql/v1/data?limit=10000&query=SELECT%20workdayID%20FROM%20topLevelOrganizations%20WHERE%20subtype%20in%20(" + '
        + ids + ' + ")"')
ns = json.dumps(od, separators=(',', ':'), ensure_ascii=False)
if ns != open(op, encoding='utf-8').read():
    open(op, 'w', encoding='utf-8').write(ns)
    changed.append(os.path.basename(op))

# no tenant-specific subtype / type WID may be left behind
for p in glob.glob(os.path.join(ROOT, '**', '*'), recursive=True) + [op]:
    if os.path.isfile(p) and any(w in open(p, encoding='utf-8', errors='ignore').read() for w in
                                 ('e6ca8683b78d10017a5c108412fc0000', 'e6ca8683b78d10017a5c108412fc0001', FUH_WID)):
        sys.exit('subtype_apps: tenant WID left in ' + os.path.relpath(p, ROOT))

print('subtype_apps: organizations by subtype, applications by organization type;', len(changed), 'files')
