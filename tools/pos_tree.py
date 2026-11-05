#!/usr/bin/env python3
"""Position picker: browse by supervisory organization as well as typing (pilot; product owner 2026-11-05, "Yes try
this" on the position tree research in docs/ECO-COMS-NOTES.md).

Clicking the picker shows folders from Workday's own supervisory organization prompt
(staffing/v6/values/jobChangesGroup/supervisoryOrganization/, the list developer.workday.com "Concept: Multilevel
Lists" uses): My Favorites, My Organizations, Supervisory Organizations by Manager (manager -> organizations) and
Supervisory Organization (A-Z). Opening an organization lists its positions, with the same id (Position ID) and
label as a typed search result, so OK, the orchestration and the audit record are unchanged. Typing still searches
(posSearch, first 50 matches). The two "... by Hierarchy" folders nest to any depth, so they are left out.

How (dynamicMonikerLevels): the root values come from posTreeRoot (eager, ~75 ms). A folder or manager opens with
posTreeNode (deferred, the folder's href; two pages when it holds more than 100, since REST returns 100 at most);
an organization opens with posTreeOrgPositions (deferred WQL, positions WHERE supervisoryOrganization in (<WID>),
~0.4 s, 41 at most). [values, true] = more levels below, [values, false] = these are the positions.

Pages: PAGES below (Edit Role Assignment first, then every position picker, 2026-11-05). Rollback: `python3 tools/pos_tree.py --off`.
"""
import json, os, sys

R = os.path.join(os.path.dirname(__file__), '..', 'presentation')
OFF = '--off' in sys.argv
# page: (picker, the id the page stores for a position, the help sentence the hint replaces)
PAGES = {'editRoleAssignment': ('positionsToAddInstanceList', 'cf_PositionID', 'Search by position name or ID.'),
         'bulkRoleGrid': ('positionAddList', 'cf_PositionID', ''),
         'assignableRoleManager': ('positionsList', 'workdayID', ''),
         'adminProvisioning': ('positionsList', 'workdayID', '')}
FOLDERS = ['My Favorites', 'My Organizations', 'Supervisory Organizations by Manager', 'Supervisory Organization']
BY_MANAGER = 'Supervisory Organizations by Manager'
NAMES = ('posTreeRoot', 'posTreeNode', 'posTreeOrgPositions')
HINT = 'Click to browse by supervisory organization, or type a position name or ID.'
LABEL = ("!empty(o.position_PositionManagement.descriptor) ? o.position_PositionManagement.descriptor : "
         "(!empty(o.cf_PositionText) ? o.cf_PositionText : o.cf_PositionID)")

ENDPOINTS = [
    {"name": "posTreeRoot", "baseUrlType": "workday-staffing-v6", "url": "values/jobChangesGroup/supervisoryOrganization/",
     "authType": "sso", "bestEffort": "true"},
    {"name": "posTreeNode", "baseUrlType": "workday-staffing-v6", "url": "<% h + '?limit=100&offset=' + o %>",
     "authType": "sso", "deferred": "true"},
    {"name": "posTreeOrgPositions", "baseUrlType": "workday-wql",
     "url": ("<% 'data?limit=200&query=' + string:pathEncode('SELECT cf_PositionID, workdayID, position_PositionManagement, cf_PositionText "
             "FROM allPositions WHERE supervisoryOrganization in (\\'' + org.replace('\\'', '').replace('\\\\', '') + '\\')') %>"),
     "authType": "sso", "deferred": "true"},
]

ROOT_VALUES = "<% (posTreeRoot.data ?? []).filter(r => { " + " || ".join(f"r.descriptor == '{f}'" for f in FOLDERS) + " }).map(r => { {'id': r.id, 'descriptor': r.descriptor} }) %>"

LEVELS_T = f"""<%
  const sel = self.promptSelections;
  const roots = posTreeRoot.data ?? [];
  const i = roots.map(r => {{ r.id }}).indexOf(sel[0]);
  const href = i < 0 ? '' : (roots[i].href ?? '');
  const byManager = i < 0 ? false : roots[i].descriptor == '{BY_MANAGER}';
  if (sel.size() == 1 || (byManager && sel.size() == 2)) {{
    const node = sel.size() == 1 ? href : (href + '/' + sel[1]);
    const first = posTreeNode.invoke({{'h': node, 'o': '0'}});
    const more = (first.total ?? 0) > 100 ? (posTreeNode.invoke({{'h': node, 'o': '100'}}).data ?? []) : [];
    return [list:flatten([first.data ?? [], more]).map(o => {{ {{'id': o.id, 'descriptor': o.descriptor}} }}), true];
  }}
  const ps = posTreeOrgPositions.invoke({{'org': sel[sel.size() - 1]}}).data ?? [];
  return [ps.filter(o => {{ !empty(o.IDKEY) }}).map(o => {{ {{'id': o.IDKEY, 'descriptor': {LABEL}}} }}), false];
%>"""


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


for page, (picker, idkey, ORIG) in PAGES.items():
    p = os.path.join(R, page + '.pmd')
    d = json.load(open(p))
    d['endPoints'] = [e for e in d['endPoints'] if e['name'] not in NAMES]
    w = find(d['presentation'], picker)
    h = (w.get('helpText') or '').replace(HINT, '')
    h = (h.replace(ORIG, '') if ORIG else h).strip()
    if OFF:
        h = (ORIG + ' ' + h).strip() if ORIG else h
        w['values'] = '<% [] %>'
        w.pop('dynamicMonikerLevels', None)
    else:
        d['endPoints'] += [dict(e) for e in ENDPOINTS]
        w['values'] = ROOT_VALUES
        w['dynamicMonikerLevels'] = LEVELS_T.replace('IDKEY', idkey)
        h = (HINT + ' ' + h).strip()
    if h: w['helpText'] = h
    else: w.pop('helpText', None)
    open(p, 'w').write(json.dumps(d, indent=2, ensure_ascii=False) + '\n')
    print(f"{page}.{picker}: {'typed search only' if OFF else 'browse by supervisory organization + typed search'}")
