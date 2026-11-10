#!/usr/bin/env python3
"""Delivered Workday fields instead of tenant calculated fields (user, 2026-11-10).

A calculated field (`cf_...`) is tenant report setup, not part of the app, so every tenant the app moves to would need
it recreated under the same alias. Three have delivered fields that gave the same value on every row (e2e probe
2026-11-10, ubc_wcpdev2), so the app reads those instead:

  allPositions          cf_PositionID        -> positionID          (829/829 equal)
  allPositions          cf_PositionIsFilled  -> worker is not empty (829/829)
  topLevelOrganizations cf_active1           -> not inactive        (1704/1704)

Role assignments: cf_ZCF_EE_RoleAssignedToAsPositionRestrictions is, by its definition in the tenant ("zCF - EE - Role
Assigned to as Position Restrictions" -> "zCF - EMI - Restricted Postions"), Role Assigned To kept to the instances whose
class is Position Restrictions. The pages now do the same with delivered fields: roleAssignedTo, kept to the ids that are
an allPositions.positionRestriction, named by that field (3459/3459 assignments and 3637/3637 names equal, probe
2026-11-10). Helper comsRoleAssignees.positionsOf; one eager list posRestrictions per page that needs it.

One stays, because nothing delivered matches (a tenant prerequisite, see docs/ECO-COMS-NOTES.md): cf_PositionText
(position search: the descriptor isn't searchable and positionTitle misses words, 22 vs 51 for "analyst").

Runs near the end of rebuild_all, after every page builder and before the sub-orchestration extraction. Earlier steps
patch files in place and look for their own text, so this step keeps each file as it found it in
tools/delivered_src/, and `--restore` (first in rebuild_all) puts those back.
"""
import glob, json, os, re, shutil, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, '..'))
SRC = os.path.join(HERE, 'delivered_src')

if '--restore' in sys.argv:
    n = 0
    for p in glob.glob(os.path.join(SRC, '**', '*'), recursive=True):
        if os.path.isfile(p):
            dst = os.path.join(ROOT, os.path.relpath(p, SRC))
            open(dst, 'w', encoding='utf-8').write(open(p, encoding='utf-8').read())
            n += 1
    print(f'delivered_fields --restore: {n} files as the earlier build steps left them')
    sys.exit(0)

shutil.rmtree(SRC, ignore_errors=True)


def keep(p):
    dst = os.path.join(SRC, os.path.relpath(p, ROOT))
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    if not os.path.exists(dst):
        shutil.copyfile(p, dst)


# ---- role assignments: positions held, without the calculated field ---------------------------------------------------
RA_CF = 'cf_ZCF_EE_RoleAssignedToAsPositionRestrictions'
POS_FN = """/* The positions a role assignment holds: Role Assigned To kept to position restrictions, named as the restriction.
   Same as the tenant calculated field zCF - EE - Role Assigned to as Position Restrictions (tools/delivered_fields.py). */
var positionsOf = function(assignees, prs) {
  let ids = (prs ?? []).map(p => { empty(p.positionRestriction) ? '' : p.positionRestriction.id });
  (assignees ?? []).filter(a => { ids.contains(a.id) }).map(a => { {'id': a.id, 'descriptor': ((prs ?? []).get(ids.indexOf(a.id))).positionRestriction.descriptor} });
};
"""
SCRIPT_FILE = os.path.join(ROOT, 'presentation', 'scripts', 'comsRoleAssignees.script')
PR_EP = {"name": "posRestrictions", "baseUrlType": "workday-wql",
         "url": "<% 'data?limit=10000&query=' + string:pathEncode('SELECT positionRestriction FROM allPositions') %>",
         "authType": "sso", "bestEffort": "true", "failOnStatusCodes": [{"code": 400}, {"code": 429}]}
PRS = 'posRestrictions.data ?? []'


def add_arg(text, call, arg):
    """Append an argument to every call of `call(` in a script string (parentheses balanced, quoted text skipped)."""
    out, i = [], 0
    while True:
        j = text.find(call, i)
        if j < 0:
            out.append(text[i:]); return ''.join(out)
        k = j + len(call); depth = 1; q = None
        while depth:
            c = text[k]
            if q:
                if c == '\\': k += 1
                elif c == q: q = None
            elif c in ('\'', '"'): q = c
            elif c == '(': depth += 1
            elif c == ')': depth -= 1
            k += 1
        seg = text[i:k - 1]
        out.append(seg + (')' if seg.endswith(', ' + arg) else ', ' + arg + ')')); i = k


def ra_page(d):
    def fix(v):
        if isinstance(v, str):
            v = add_arg(v, 'comsAccessReview.rowsFrom(', PRS)
            return v.replace('ra.' + RA_CF, f'comsRoleAssignees.positionsOf(ra.roleAssignedTo, {PRS})')
        if isinstance(v, list): return [fix(x) for x in v]
        if isinstance(v, dict): return {k: fix(x) for k, x in v.items()}
        return v
    d = fix(d)
    body = json.dumps(d)
    if 'comsRoleAssignees.' in body and 'comsRoleAssignees.script' not in (d.get('include') or []):
        d['include'] = (d.get('include') or []) + ['comsRoleAssignees.script']
    if 'posRestrictions.data' in body and not any(e.get('name') == 'posRestrictions' for e in d.get('endPoints', [])):
        d.setdefault('endPoints', []).insert(0, dict(PR_EP))
    return d

# Workday Script (pages, scripts): read the delivered field the way the calculated one was read
SCRIPT = [
    (re.compile(r'(\b[\w\]\)]+)\.cf_PositionIsFilled == false'), r'empty(\1.worker)'),
    (re.compile(r'(\b[\w\]\)]+)\.cf_PositionIsFilled == true'), r'!empty(\1.worker)'),
    (re.compile(r'\.cf_active1 == true'), '.inactive != true'),
    (re.compile(r'\.cf_active1 != true'), '.inactive == true'),
]
# WQL field lists and filters, and any leftover name (comments, JSON paths)
COMMON = [
    (re.compile(r'\bcf_PositionIsFilled = false\b'), 'worker is empty'),
    (re.compile(r'\bcf_PositionIsFilled\b'), 'worker'),
    (re.compile(r'\bcf_active1\b'), 'inactive'),
    (re.compile(r'\bcf_PositionID\b'), 'positionID'),
]
# Orchestrations (bulk role changes): "the position was found and has nobody in it", from the WQL response text.
# An empty instance field is left out of the response (probe: P-00030 had no "worker" key).
ORCH_UNFILLED = (
    'data.LookupPosition.response.toString().replace(\\" \\", \\"\\").contains(\\"\\\\\\"cf_PositionIsFilled\\\\\\":false\\")',
    '(if (data.LookupPosition.response.toString().replace(\\" \\", \\"\\").contains(\\"\\\\\\"positionID\\\\\\":\\")) '
    'data.LookupPosition.response.toString().replace(\\" \\", \\"\\").contains(\\"\\\\\\"worker\\\\\\":\\").not() else false)',
)

files = (glob.glob(os.path.join(ROOT, 'presentation', '*.pmd')) + glob.glob(os.path.join(ROOT, 'presentation', 'scripts', '*.script'))
         + glob.glob(os.path.join(ROOT, 'presentation', 'wqlQueries', '*.wqlquery'))
         + glob.glob(os.path.join(ROOT, 'presentation', 'cards', '*')) + glob.glob(os.path.join(ROOT, 'orchestration', '*')))
changed = []
for p in sorted(files):
    t = open(p, encoding='utf-8').read()
    n = t
    if '/orchestration/' in p.replace('\\', '/'):
        if 'LookupPosition' in n and 'cf_PositionIsFilled' in n:
            if ORCH_UNFILLED[0] not in n:
                sys.exit('delivered_fields: unfilled check not found in ' + os.path.basename(p))
            n = n.replace(*ORCH_UNFILLED)
    for rx, rep in SCRIPT + COMMON:
        n = rx.sub(rep, n)
    if RA_CF in n or 'comsAccessReview.rowsFrom(' in n:
        if p.endswith('.wqlquery'):
            n = n.replace(RA_CF + '}', 'roleAssignedTo}')
        elif p.endswith('comsAccessReview.script'):
            n = n.replace('var allRows = function(roles) {', POS_FN + '\nvar allRows = function(roles, prs) {')
            n = n.replace('(ra.' + RA_CF + ' ?? [])', 'positionsOf(ra.roleAssignedTo, prs)')
            n = n.replace('var rowsFrom = function(roles, vacant) {', 'var rowsFrom = function(roles, vacant, prs) {')
            n = n.replace('allRows(roles).filter', 'allRows(roles, prs).filter')
        elif p.endswith('.pmd'):
            n = json.dumps(ra_page(json.loads(n)), indent=2, ensure_ascii=False) + '\n'
    if n != t:
        keep(p)
        open(p, 'w', encoding='utf-8').write(n)
        changed.append(os.path.relpath(p, ROOT))

open(SCRIPT_FILE, 'w', encoding='utf-8').write(POS_FN + '\n{\n  "positionsOf": positionsOf\n}\n')
left = [os.path.relpath(p, ROOT) for p in files if re.search(r'cf_(PositionID|PositionIsFilled|active1|ZCF_EE_RoleAssignedToAsPositionRestrictions)\b', open(p, encoding='utf-8').read())]
if left:
    sys.exit('delivered_fields: calculated fields left in ' + ', '.join(left))
dup = [os.path.relpath(p, ROOT) for p in files if re.search(r'\bworker, (\w+, )*worker\b', open(p, encoding='utf-8').read())]
if dup:
    sys.exit('delivered_fields: worker selected twice in ' + ', '.join(dup))
print(f'delivered_fields: positionID / worker / inactive / roleAssignedTo instead of four calculated fields; {len(changed)} files')
