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
X_META = 'e6ca8683b78d10017a5c108412fc0000'
X_SHELL = 'e6ca8683b78d10017a5c108412fc0001'
SUBTYPES = f'{X_META}, {X_SHELL}'
NOT_AAA = "roleName not contains 'Organizations and Roles Assignment Administrator'"
ROLE_SEL = ('SELECT role, enabledForOrganizationTypes, roleAssignments{organization, workersAssigned, '
            'cf_ZCF_EE_RoleAssignedToAsPositionRestrictions} as roleAssignments FROM assignableRoles')

# ---- WQL query components -------------------------------------------------------------------------------------------
QUERIES = {
    'allShellOrgs': {'id': 'allShellOrgs', 'query':
        f'SELECT workdayID, organizationByName, code, cf_active1, type1 FROM topLevelOrganizations WHERE subtype in ({SUBTYPES})'},
    'customOrganizations': {'id': 'customOrganizations', 'query':
        f'SELECT workdayID, organizationByName, code, type1 FROM topLevelOrganizations WHERE subtype in ({SUBTYPES})'},
    'appTypes': {'id': 'appTypes', 'query':
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

APP_TYPES_EP = {"name": "appTypes", "baseUrlType": "workday-wql", "url": "data", "authType": "sso", "bestEffort": "true",
                "wqlQuery": {"queryId": "appTypes"}, "failOnStatusCodes": [{"code": 400}, {"code": 429}]}

# The application of an organization record (inline in pages): its type, else its code.
APP_OF = "((org.type1 ?? []).size() > 0 ? org.type1[0].descriptor : org.code)"

# ---- text rewrites (old -> new), applied to every page and script ------------------------------------------------------
REWRITES = [
    # run-and-verify readbacks (Add Shell Org, Add Pattern): find the new organization among the subtype ones
    ("WHERE%20code%20contains%20%27X%3A%27", f"WHERE%20subtype%20in%20({X_META}%2C%20{X_SHELL})"),
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
print('subtype_apps: organizations by subtype, applications by organization type;', len(changed), 'files')
