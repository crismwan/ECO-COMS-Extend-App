#!/usr/bin/env python3
"""One grid format across the app (product owner 2026-11-02: "ensure grid format is consistent").

Every read-only grid gets the same presentation:
  - gridType LIST + multiViewStylingEnabled (the list look used on most pages)
  - every column sortable and filterable, except button columns (nothing to sort)
  - VIEW pages: autoPaging and Excel export (export is view-page only, developer.workday.com "grid")
  - EDIT pages: doNotAdd / doNotRemove, so a display grid shows no +/- icons (readOnly doesn't hide them)
  - `enabled` is left as each page has it (related-action links on instanceList cells must keep working)
Editable grids (EDITABLE below) keep Workday's spreadsheet look. Idempotent; runs after polish.py.
"""
import glob, json, os
ROOT = os.path.join(os.path.dirname(__file__), '..', 'presentation')
EDITABLE = {('bulkRoleGrid', 'currentGrid'), ('bulkRoleGrid', 'addGrid')}   # users tick / add rows here
changed = []


def style(g, page, edit):
    if (page, g.get('id')) in EDITABLE: return
    before = json.dumps(g, sort_keys=True)
    g['gridType'] = 'LIST'
    g['multiViewStylingEnabled'] = True
    for c in g.get('columns', []):
        if (c.get('cellTemplate') or {}).get('type') == 'button':
            c.pop('sortableAndFilterable', None)
        else:
            c['sortableAndFilterable'] = 'true'
    if edit:
        g['doNotAdd'] = True
        g['doNotRemove'] = True
        g.pop('autoPaging', None); g.pop('excelExportEnabled', None)
    else:
        g['autoPaging'] = True
        g['excelExportEnabled'] = True
    if json.dumps(g, sort_keys=True) != before:
        changed.append(f'{page}.{g.get("id")}')


def walk(n, page, edit):
    if isinstance(n, dict):
        if n.get('type') == 'grid': style(n, page, edit)
        for v in n.values(): walk(v, page, edit)
    elif isinstance(n, list):
        for v in n: walk(v, page, edit)


for f in sorted(glob.glob(os.path.join(ROOT, '*.pmd'))):
    d = json.load(open(f))
    edit = (d['presentation'].get('pageType') or d.get('pageType')) == 'EDIT'
    before = json.dumps(d)
    walk(d['presentation'], d['id'], edit)
    if json.dumps(d) != before:
        open(f, 'w').write(json.dumps(d, indent=2, ensure_ascii=False) + '\n')
print('grids restyled:', ', '.join(changed) or 'none')
