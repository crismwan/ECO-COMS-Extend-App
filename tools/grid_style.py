#!/usr/bin/env python3
"""One grid format across the app (product owner 2026-11-02: "ensure grid format is consistent").

Every read-only grid gets the same presentation:
  - gridType LIST + multiViewStylingEnabled (the list look used on most pages)
  - text-type columns sortable and filterable (Workday can't sort button / fieldSet columns, and draws their headers ~10px
    lower); the short application lists (SHORT_LISTS) have no sorting at all, so their headers line up
  - button columns last, in their own order (Withdraw's Select column was first)
  - VIEW pages: autoPaging and Excel export (export is view-page only, developer.workday.com "grid")
  - EDIT pages: doNotAdd / doNotRemove, so a display grid shows no +/- icons (readOnly doesn't hide them)
  - `enabled` is left as each page has it (related-action links on instanceList cells must keep working)
Editable grids (EDITABLE below) get the list look too, but no sorting and their own +/- settings. Idempotent; runs after polish.py.
"""
import glob, json, os
ROOT = os.path.join(os.path.dirname(__file__), '..', 'presentation')
EDITABLE = {('bulkRoleGrid', 'currentGrid'), ('bulkRoleGrid', 'addGrid'), ('editAppPattern', 'fieldsGrid')}   # users tick / add rows here
# Application lists (about 15 rows): no sorting, so the button column header lines up (product owner 2026-11-02)
SHORT_LISTS = {'appPickGrid', 'appsGrid', 'appPatternsGrid'}
changed = []


def style(g, page, edit):
    if (page, g.get('id')) in EDITABLE:
        # same list look as every other grid (product owner 2026-11-02); no sorting, and the +/- settings stay as built
        g['gridType'] = 'LIST'
        g['multiViewStylingEnabled'] = True
        return
    before = json.dumps(g, sort_keys=True)
    g['gridType'] = 'LIST'
    g['multiViewStylingEnabled'] = True
    for c in g.get('columns', []):
        # Workday sorts only text-type columns (button and fieldSet columns stay unsortable whatever the attribute says)
        # and draws an unsortable header ~10px lower (live 2026-11-02). Short lists drop sorting so their headers line up.
        if g.get('id') in SHORT_LISTS:
            c.pop('sortableAndFilterable', None)
        elif (c.get('cellTemplate') or {}).get('type') in ('button', 'fieldSet', 'section'):
            c.pop('sortableAndFilterable', None)
        else:
            c['sortableAndFilterable'] = 'true'
    cols = g.get('columns', [])
    is_btn = lambda c: (c.get('cellTemplate') or {}).get('type') == 'button' and (c.get('cellTemplate') or {}).get('action') != 'LINK'   # a link is the row's name
    g['columns'] = [c for c in cols if not is_btn(c)] + [c for c in cols if is_btn(c)]
    if edit:
        g['doNotAdd'] = True
        g['doNotRemove'] = True
        g.pop('autoPaging', None); g.pop('excelExportEnabled', None)
    else:
        g['autoPaging'] = True
        g['excelExportEnabled'] = True
        # App Hub build: a button cell in an exported grid needs excel settings ("To export a column with non-basic widget...")
        # on the column, not the cell widget (live 2026-11-02: the cell-level attribute didn't satisfy the build)
        for c in g['columns']:
            ct = c.get('cellTemplate') or {}
            if ct.get('type') == 'button':
                ct.pop('excel', None)
                c.setdefault('excel', {"enabled": False})
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
