#!/usr/bin/env python3
"""Record what c01.py / c02.py change, as format-independent operations, to replay in the Confluence editor.

The builders were written against the Confluence export of the template (view HTML). The live pages are edited in
Confluence's editor, so instead of shipping a whole page this records each change by what it's anchored to:
a table found by the text of its first cell, a paragraph found by its text, a "Diagram — …" block. replay.js
applies the operations to the editor and Confluence keeps the result as an unpublished draft.

Images become Confluence storage markup: Gliffy diagrams (ac:structured-macro gliffy, attached by upload.js) and
attached screenshots (ac:image). The editor converts them through /rest/api/contentbody/convert/editor.

Usage: python3 record.py c01.py <template.html> ops01.json
"""
import html as _html, json, sys
import fill

SCRIPT, SRC, OUT = sys.argv[1], sys.argv[2], sys.argv[3]
OPS, LOC = [], {}

GLIFFY = {
    'img/current-architecture.png': 'ECO-COMS Current State',
    'img/future-state.png': 'ECO-COMS Future State',
    'img/value-stream.png': 'ECO-COMS Value Stream Map',
    'img/user-journey.png': 'ECO-COMS User Journey',
    'img/solution-architecture.png': 'ECO-COMS Solution Architecture',
    'img/navigation-map.png': 'ECO-COMS Navigation Map',
    'img/data-flow.png': 'ECO-COMS Data Flow',
    'img/orchestration-flow.png': 'ECO-COMS Orchestration Flow',
    'img/process-workflow.png': 'ECO-COMS Role Request Workflow',
}


def img(src, alt, width=900):
    cap = f'<p><em>{_html.escape(alt, quote=False)}</em></p>'
    if src in GLIFFY:
        n = GLIFFY[src]
        return (f'<ac:structured-macro ac:name="gliffy" ac:schema-version="1"><ac:parameter ac:name="size">{width}</ac:parameter>'
                f'<ac:parameter ac:name="displayName">{n}</ac:parameter><ac:parameter ac:name="name">{n}</ac:parameter>'
                f'<ac:parameter ac:name="pagePin">1</ac:parameter></ac:structured-macro>' + cap)
    # dev-tenant screenshots aren't published from the public repository: a marked placeholder instead
    return f'<p><em>[Screenshot to add: {_html.escape(alt, quote=False)}]</em></p>'


o_T, o_wrap, o_heading, o_pah = fill.T, fill.wrap_of, fill.heading, fill.p_after_heading
o_kv, o_rows, o_cell, o_after, o_before, o_dia = fill.kv, fill.set_rows, fill.set_cell, fill.insert_after, fill.insert_before, fill.diagram_html


def T(soup, start, nth=0):
    t = o_T(soup, start, nth)
    LOC[id(t)] = {'t': 'table', 'start': start, 'nth': nth}
    return t


def wrap_of(t):
    w = o_wrap(t)
    LOC[id(w)] = LOC.get(id(t))
    return w


def heading(soup, start, tags=('h1', 'h2', 'h3', 'p')):
    h = o_heading(soup, start, tags)
    LOC[id(h)] = {'t': 'text', 'start': start}
    return h


def loc(elem):
    if id(elem) in LOC and LOC[id(elem)]:
        return LOC[id(elem)]
    prev = elem.find_previous_sibling()
    while prev is not None:
        if id(prev) in LOC:
            return {'t': 'next', 'base': LOC[id(prev)], 'tag': elem.name}
        prev = prev.find_previous_sibling()
    raise SystemExit(f'no anchor for <{elem.name}> {elem.get_text(" ", strip=True)[:60]!r}')


def kv(soup, table, key, value, col=1):
    OPS.append({'op': 'kv', 'at': loc(table), 'key': key, 'col': col, 'html': fill.cell_html(value)})
    return o_kv(soup, table, key, value, col)


def set_rows(soup, table, rows, keep=1, bold_first=False):
    cells = []
    for r in rows:
        row = []
        for i, v in enumerate(r):
            if bold_first and i == 0 and not isinstance(v, fill.H):
                v = fill.H('<p><strong>' + fill.esc(v) + '</strong></p>')
            row.append(fill.cell_html(v))
        cells.append(row)
    OPS.append({'op': 'rows', 'at': loc(table), 'keep': keep, 'rows': cells})
    return o_rows(soup, table, rows, keep, bold_first)


def set_cell(soup, table, r, c, value):
    key = table.find_all('tr')[r].find_all(['td', 'th'])[0].get_text(' ', strip=True)
    OPS.append({'op': 'cell', 'at': loc(table), 'key': key, 'col': c, 'html': fill.cell_html(value)})
    return o_cell(soup, table, r, c, value)


MUTE = [False]


def insert_after(soup, elem, html_s):
    if MUTE[0]:
        return o_after(soup, elem, html_s)
    OPS.append({'op': 'after', 'at': loc(elem), 'html': html_s})
    return o_after(soup, elem, html_s)


def insert_before(soup, elem, html_s):
    if 'Selected' in html_s:
        OPS.append({'op': 'selectExtend', 'at': {'t': 'table', 'start': 'Workday Studio Integration', 'nth': 0}})
    else:
        OPS.append({'op': 'before', 'at': loc(elem), 'html': html_s})
    return o_before(soup, elem, html_s)


def diagram_html(soup, title_start, html_s):
    OPS.append({'op': 'diagram', 'title': title_start, 'html': html_s})
    MUTE[0] = True
    try:
        return o_dia(soup, title_start, html_s)
    finally:
        MUTE[0] = False


for name, fn in [('T', T), ('wrap_of', wrap_of), ('heading', heading), ('kv', kv), ('set_rows', set_rows),
                 ('set_cell', set_cell), ('insert_after', insert_after), ('insert_before', insert_before),
                 ('diagram_html', diagram_html), ('img', img)]:
    setattr(fill, name, fn)

src = open(SCRIPT, encoding='utf-8').read().replace("SRC = '01_part1.html'", f'SRC = {SRC!r}').replace("SRC = '02_part1.html'", f'SRC = {SRC!r}')
sys.argv = [SCRIPT, '/dev/null']
exec(compile(src, SCRIPT, 'exec'), {'__name__': '__main__'})
if 'c02' in SCRIPT:
    OPS.append({'op': 'removeCards', 'titles': ['Studio', 'Orchestrate']})
json.dump(OPS, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False)
print(f'{OUT}: {len(OPS)} operations, {len(json.dumps(OPS, ensure_ascii=False)) // 1024} KB')
