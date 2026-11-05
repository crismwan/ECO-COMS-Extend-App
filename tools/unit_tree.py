#!/usr/bin/env python3
"""Functional Unit Hierarchy and Academic Unit pickers: browse by type as well as typing (product owner 2026-11-05,
"also look at academic unit and functional unit hierarchy" after the position tree).

No hierarchy to follow in this tenant (e2e `orgtree`, 2026-11-05): all 837 FUH custom organizations are at level 1
with no superior or included organizations, and all 157 active Academic Units are top nodes with no hierarchy
(academicUnitHierarchies is empty). Both carry a type, so the tree is type -> entries:
  FUH subtype: 06 Faculty, 07 Department, 08 Sub-Department, 09 Sub-Location, 10 Sub-Unit, 11 Other
  Academic Unit subtype: Campus/Senate, Department, Faculty, Institution, Program Unit, School
A type with more than 40 entries gets an A-Z level first (FUH Department has 363). Leaves are {workdayID, name},
exactly what the typed search (fuhSearch / auSearch) returns, so what the request saves is unchanged.

How: one eager WQL per list (fuhTreeAll, auTreeAll) feeds the root (types with counts, `values`) and every level
(dynamicMonikerLevels filters it; no calls when a folder opens).

Rollback: `python3 tools/unit_tree.py --off` (or remove the step from rebuild_all.sh).
"""
import json, os, sys

R = os.path.join(os.path.dirname(__file__), '..', 'presentation')
OFF = '--off' in sys.argv
PAGES = ['assignableRoleManager', 'adminProvisioning']
BIG = 40
NONE = '(No subtype)'

LISTS = {
    'fuhPicker': dict(
        ep='fuhTreeAll', name='organization1', sub='subtype',
        wql="SELECT workdayID, organization1, subtype FROM customOrganizations WHERE type1 in (b40d8b016367100175b147f364840000)",
        hint='Click to browse by type, or type a code to search.'),
    'academicUnitPicker': dict(
        ep='auTreeAll', name='academicUnit', sub='academicUnitSubtype',
        wql="SELECT workdayID, academicUnit, academicUnitSubtype FROM academicUnits WHERE inactive = false",
        hint='Click to browse by type, or type a name to search.'),
}


def type_of(c):
    return f"(empty(o.{c['sub']}) ? '{NONE}' : (o.{c['sub']}.descriptor ?? '{NONE}'))"


def root(c):
    return (f"<% let d = {c['ep']}.data ?? []; let ts = d.map(o => {{ {type_of(c)} }}); "
            f"ts.distinct().sort().map(t => {{ {{'id': 'T:' + t, 'descriptor': t + ' (' + ts.filter(x => {{ x == t }}).size() + ')'}} }}) %>")


def levels(c):
    return f"""<%
  const sel = self.promptSelections;
  const t = sel[0].substring(2);
  const items = ({c['ep']}.data ?? []).filter(o => {{ {type_of(c)} == t }}).map(o => {{ {{'id': o.workdayID, 'descriptor': (empty(o.{c['name']}) ? '' : (o.{c['name']}.descriptor ?? ''))}} }});
  const first = items.map(o => {{ (o.descriptor + ' ').substring(0, 1).upperCase() }});
  if (sel.size() == 1 && items.size() > {BIG}) {{
    return [first.distinct().sort().map(l => {{ {{'id': 'L:' + l, 'descriptor': l + ' (' + first.filter(x => {{ x == l }}).size() + ')'}} }}), true];
  }}
  const l = sel.size() > 1 ? sel[1].substring(2) : '';
  return [list:sort(items.filter(o => {{ l == '' || (o.descriptor + ' ').substring(0, 1).upperCase() == l }}), 'descriptor', true), false];
%>"""


def endpoint(c):
    q = c['wql']
    return {"name": c['ep'], "baseUrlType": "workday-wql",
            "url": f"<% 'data?limit=10000&query=' + string:pathEncode('{q}') %>",
            "authType": "sso", "bestEffort": "true"}


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


for page in PAGES:
    p = os.path.join(R, page + '.pmd')
    d = json.load(open(p))
    d['endPoints'] = [e for e in d['endPoints'] if e['name'] not in [c['ep'] for c in LISTS.values()]]
    for picker, c in LISTS.items():
        w = find(d['presentation'], picker)
        h = (w.get('helpText') or '').replace(c['hint'], '').strip()
        if OFF:
            w['values'] = '<% [] %>'
            w.pop('dynamicMonikerLevels', None)
        else:
            d['endPoints'].append(endpoint(c))
            w['values'] = root(c)
            w['dynamicMonikerLevels'] = levels(c)
            h = (c['hint'] + ' ' + h).strip()
        if h: w['helpText'] = h
        else: w.pop('helpText', None)
    open(p, 'w').write(json.dumps(d, indent=2, ensure_ascii=False) + '\n')
    print(f"{page}: FUH / Academic Unit {'typed search only' if OFF else 'browse by type + typed search'}")
