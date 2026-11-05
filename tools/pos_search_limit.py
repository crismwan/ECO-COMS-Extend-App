#!/usr/bin/env python3
"""Position searches return the first 50 matches (e2e `possearch`, 2026-11-05, median of 5).

Measured: the server takes about 1 s for any position search (the text scan over allPositions), whatever the limit or
columns. Without a limit a broad search returned every match (804 rows, 247 KB, 1.2 s for "a"; 783 rows, 240 KB,
1.4 s for "P-00"); with 50 it took about 1.0 s and 15 KB, and the page maps 50 rows instead of hundreds. Dropping the
unused cf_PositionIsFilled column gained nothing, so the query is otherwise unchanged.

Pages: Submit Assignable Role Request, AAA Role Request, Edit Role Assignment (posSearch) and Bulk Edit (gridPosSearch).
Rollback: `python3 tools/pos_search_limit.py --off` (or remove the step from rebuild_all.sh).
"""
import json, os, sys

R = os.path.join(os.path.dirname(__file__), '..', 'presentation')
OFF = '--off' in sys.argv
LIMIT = 50
ENDPOINTS = {'assignableRoleManager': ('posSearch', 'positionsList'), 'adminProvisioning': ('posSearch', 'positionsList'),
             'editRoleAssignment': ('posSearch', 'positionsToAddInstanceList'), 'bulkRoleGrid': ('gridPosSearch', 'positionAddList')}
PLAIN, LIMITED = "'data?query='", f"'data?limit={LIMIT}&query='"
HINT = f' Shows the first {LIMIT} matches; type more of the title or ID to narrow.'


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


for page, (ep, picker) in ENDPOINTS.items():
    p = os.path.join(R, page + '.pmd')
    d = json.load(open(p))
    e = next(x for x in d['endPoints'] if x['name'] == ep)
    assert 'allPositions' in e['url'], (page, ep)
    e['url'] = e['url'].replace(LIMITED, PLAIN) if OFF else e['url'].replace(PLAIN, LIMITED)
    w = find(d, picker)
    if w is not None:
        h = (w.get('helpText') or '').replace(HINT, '').replace(HINT.strip(), '').strip()
        if not OFF: h = (h + HINT).strip()
        if h: w['helpText'] = h
        else: w.pop('helpText', None)
    open(p, 'w').write(json.dumps(d, indent=2, ensure_ascii=False) + '\n')
    print(f"{page}.{ep}: {'no limit' if OFF else f'limit {LIMIT}'}")
