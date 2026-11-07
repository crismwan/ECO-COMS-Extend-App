#!/usr/bin/env python3
"""Mermaid flowchart (.mmd) -> Gliffy diagram file (application/gliffy+json, version 2.0), for Confluence.

Layout comes from Graphviz (dot -Tjson); shapes and connectors use the stencils of an existing Gliffy diagram on
UBC Confluence ("XTND-COMS - Architecture Design"): basic round_rectangle, flowchart process, basic line. Connectors
are glued to their shapes (start/end constraints), so the diagram stays editable in the Gliffy editor.

Usage: python3 gliffy.py diagrams/arch.mmd out/arch.gliffy "Title"
"""
import html, json, re, subprocess, sys, uuid

SRC, OUT, TITLE = sys.argv[1], sys.argv[2], sys.argv[3]
LAYER = 'L0'
PALETTE = ['#e8f0fa', '#fdf2e3', '#e9f5ec', '#f3eafa', '#fbe9ea', '#eef3f6']

# ---------------------------------------------------------------- parse mermaid
nodes, edges, clusters = {}, [], []          # node id -> {label, shape, cluster}
stack, direction, newcls = [], 'LR', set()
NODE = re.compile(r'([A-Za-z0-9_]+)\s*(\(\[(.*?)\]\)|\[\((.*?)\)\]|\{\{(.*?)\}\}|\(\((.*?)\)\)|\[(.*?)\]|\{(.*?)\}|\((.*?)\))?')
ARROW = re.compile(r'\s*(-->\|[^|]*\||--\s[^-]*?\s-->|-\.\s[^.]*?\s\.->|-\.->|-->|---|~~~)\s*')


def clean(t):
    t = (t or '').strip().strip('"')
    return html.unescape(t.replace('<br/>', '\n').replace('<br>', '\n'))


def node(tok):
    out = []
    for part in [p.strip() for p in tok.split('&')]:
        m = NODE.fullmatch(part)
        if not m:
            raise SystemExit(f'cannot parse node: {part!r}')
        nid = m.group(1)
        groups = m.groups()[2:]
        shape = None
        if m.group(2):
            shape = ['stadium', 'db', 'hex', 'circle', 'rect', 'diamond', 'round'][next(i for i, g in enumerate(groups) if g is not None)]
            label = next(g for g in groups if g is not None)
        n = nodes.setdefault(nid, {'label': nid, 'shape': 'rect', 'cluster': stack[-1] if stack else None})
        if shape:
            n['label'], n['shape'] = clean(label), shape
            n['cluster'] = stack[-1] if stack else None
        out.append(nid)
    return out


for raw in open(SRC, encoding='utf-8'):
    line = raw.strip()
    if not line or line.startswith('%%'):
        continue
    if line.startswith('flowchart') or line.startswith('graph'):
        direction = line.split()[1]
        continue
    if line.startswith('direction'):
        continue
    if line.startswith('classDef'):
        continue
    if line.startswith('class '):
        newcls.update(x.strip() for x in line.split()[1].split(','))
        continue
    if line.startswith('subgraph'):
        m = re.match(r'subgraph\s+([A-Za-z0-9_]+)(?:\[(.*)\])?', line)
        cid = m.group(1)
        clusters.append({'id': cid, 'title': clean(m.group(2) or cid), 'parent': stack[-1] if stack else None})
        stack.append(cid)
        continue
    if line == 'end':
        stack.pop()
        continue
    parts = ARROW.split(line)
    prev = node(parts[0])
    i = 1
    while i < len(parts) - 1:
        arrow, nxt = parts[i], node(parts[i + 1])
        label, style = '', 'solid'
        if arrow.startswith('-->|'):
            label = arrow[4:-1]
        elif arrow.startswith('-- '):
            label = arrow[3:-4]
        elif arrow.startswith('-. ') and len(arrow) > 5:
            label, style = arrow[3:-4], 'dash'
        elif arrow == '-.->':
            style = 'dash'
        elif arrow == '~~~':
            style = 'invisible'
        head = arrow not in ('---', '~~~')
        for a in prev:
            for b in nxt:
                edges.append({'a': a, 'b': b, 'label': clean(label), 'style': style, 'head': head})
        prev = nxt
        i += 2

# ---------------------------------------------------------------- layout with Graphviz
def q(s):
    return '"' + s.replace('\\', '\\\\').replace('"', '\\"') + '"'


dot = [f'digraph G {{ rankdir={"TB" if direction in ("TB", "TD") else "LR"}; compound=true; nodesep=0.5; ranksep=0.9; splines=polyline;',
       'node [shape=box fontname="Arial" fontsize=11 margin="0.15,0.08"]; edge [fontname="Arial" fontsize=10];']


def emit_cluster(cid, depth):
    c = next(x for x in clusters if x['id'] == cid)
    dot.append(f'subgraph cluster_{cid} {{ label={q(c["title"])}; fontname="Arial"; fontsize=12; margin=18;')
    for k in [x['id'] for x in clusters if x['parent'] == cid]:
        emit_cluster(k, depth + 1)
    for nid, n in nodes.items():
        if n['cluster'] == cid:
            dot.append(f'{nid} [label={q(n["label"])}];')
    dot.append('}')


for c in [x for x in clusters if x['parent'] is None]:
    emit_cluster(c['id'], 0)
for nid, n in nodes.items():
    if n['cluster'] is None:
        dot.append(f'{nid} [label={q(n["label"])}];')
for e in edges:
    attrs = [f'label={q(e["label"])}' if e['label'] else '']
    if e['style'] == 'invisible':
        attrs.append('style=invis')
    dot.append(f'{e["a"]} -> {e["b"]} [{",".join(a for a in attrs if a)}];')
dot.append('}')
lay = json.loads(subprocess.run(['dot', '-Tjson'], input='\n'.join(dot), capture_output=True, text=True, check=True).stdout)

PT = 1.4          # points -> pixels
H = float(lay['bb'].split(',')[3])
X = lambda x: round(float(x) * PT + 20, 1)
Y = lambda y: round((H - float(y)) * PT + 20, 1)

# ---------------------------------------------------------------- gliffy objects
order = [0]


def nid():
    return str(uuid.uuid4())


def next_order():
    order[0] += 1
    return order[0]


def text_obj(txt, w, h, bold=False, align='center', size=12, valign='middle', x=0, y=0):
    paras = ''.join(
        f'<p style="text-align:{align};"><span style="font-family:Arial;font-size:{size}px;'
        f'{"font-weight:bold;" if bold else ""}text-decoration:none;">{html.escape(line) or "&nbsp;"}</span></p>'
        for line in txt.split('\n'))
    return {'x': x, 'y': y, 'rotation': 0, 'id': nid(), 'uid': None, 'width': w, 'height': h, 'lockAspectRatio': False,
            'lockShape': False, 'order': next_order(), 'hidden': False,
            'graphic': {'type': 'Text', 'Text': {'tid': None, 'valign': valign, 'overflow': 'none', 'vposition': 'none',
                                                 'hposition': 'none', 'html': paras, 'paddingLeft': 2, 'paddingRight': 2,
                                                 'paddingBottom': 2, 'paddingTop': 2, 'outerPaddingLeft': 6,
                                                 'outerPaddingRight': 6, 'outerPaddingBottom': 2, 'outerPaddingTop': 6,
                                                 'editable': {'isEditable': True}}},
            'children': None, 'layerId': LAYER}


def shape(uid, tid, x, y, w, h, fill, stroke='#333333', sw=1, children=None, oid=None):
    return {'x': x, 'y': y, 'rotation': 0, 'id': oid or nid(), 'uid': uid, 'width': w, 'height': h,
            'lockAspectRatio': False, 'lockShape': False, 'flipHorizontal': False, 'flipVertical': False,
            'order': next_order(), 'hidden': False,
            'graphic': {'type': 'Shape', 'Shape': {'tid': tid, 'strokeWidth': sw, 'strokeColor': stroke, 'fillColor': fill,
                                                   'gradient': False, 'dropShadow': False, 'state': 0, 'shadowX': 0,
                                                   'shadowY': 0, 'opacity': 1}},
            'children': children or [], 'layerId': LAYER, 'linkMap': []}


ROUND = ('com.gliffy.shape.basic.basic_v1.default.round_rectangle', 'com.gliffy.stencil.round_rectangle.basic_v1')
PROC = ('com.gliffy.shape.flowchart.flowchart_v1.default.process', 'com.gliffy.stencil.rectangle.basic_v1')
objects = []

# clusters, outermost first (drawn behind), each with its title at the top
depth = {}
for c in clusters:
    d, p = 0, c['parent']
    while p:
        d, p = d + 1, next(x for x in clusters if x['id'] == p)['parent']
    depth[c['id']] = d
for i, g in enumerate(sorted((o for o in lay.get('objects', []) if o['name'].startswith('cluster_')),
                             key=lambda o: depth[o['name'][8:]])):
    x1, y1, x2, y2 = map(float, g['bb'].split(','))
    x, y, w, h = X(x1), Y(y2), round((x2 - x1) * PT, 1), round((y2 - y1) * PT, 1)
    title = next(c for c in clusters if c['id'] == g['name'][8:])['title']
    objects.append(shape(*ROUND, x, y, w, h, PALETTE[i % len(PALETTE)], '#7a8a99', 1,
                         [text_obj(title, w - 4, 22, bold=True, align='left', valign='top', x=2, y=0)]))

ids = {}
for g in lay.get('objects', []):
    if g['name'].startswith('cluster_') or 'pos' not in g:
        continue
    n = nodes[g['name']]
    cx, cy = map(float, g['pos'].split(','))
    w, h = float(g['width']) * 72 * PT, float(g['height']) * 72 * PT
    x, y = round(X(cx) - w / 2, 1), round(Y(cy) - h / 2, 1)
    uid, tid = ROUND if n['shape'] in ('stadium', 'round', 'circle', 'db') else PROC
    fill = '#FFE8D6' if g['name'] in newcls else ('#fff8d6' if n['shape'] in ('diamond', 'hex') else '#ffffff')
    if n['shape'] == 'db':
        fill = '#eef6ff'
    oid = nid()
    ids[g['name']] = (oid, x, y, w, h)
    objects.append(shape(uid, tid, x, y, round(w, 1), round(h, 1), fill, '#333333', 2 if n['shape'] in ('diamond', 'hex') else 1,
                         [text_obj(n['label'], round(w - 4, 1), round(h, 1), bold=n['shape'] in ('diamond', 'hex'), x=2)], oid))

name_of = {o['_gvid']: o['name'] for o in lay.get('objects', []) if '_gvid' in o}
for e in lay.get('edges', []):
    src, dst = name_of[e['tail']], name_of[e['head']]
    meta = next((x for x in edges if x['a'] == src and x['b'] == dst), {'style': 'solid', 'head': True, 'label': ''})
    if meta['style'] == 'invisible' or src not in ids or dst not in ids:
        continue
    pts = []
    for d in e.get('_draw_', []):
        if d.get('op') in ('b', 'B'):
            pts = [(X(px), Y(py)) for px, py in d['points']]
    if not pts:
        continue
    pts = [p for i, p in enumerate(pts) if i == 0 or p != pts[i - 1]]
    for d in e.get('_hdraw_', []):
        if d.get('op') in ('P', 'p') and meta['head']:
            tip = max(((X(a), Y(b)) for a, b in d['points']), key=lambda t: (t[0] - pts[-1][0]) ** 2 + (t[1] - pts[-1][1]) ** 2)
            pts.append(tip)
    x0, y0 = pts[0]
    so, _, _, _, _ = ids[src]; do_, *_ = ids[dst]
    objects.append({'x': x0, 'y': y0, 'rotation': 0, 'id': nid(), 'uid': 'com.gliffy.shape.basic.basic_v1.default.line',
                    'width': 100, 'height': 100, 'lockAspectRatio': False, 'lockShape': False, 'order': next_order(),
                    'hidden': False,
                    'graphic': {'type': 'Line', 'Line': {'strokeWidth': 1.5, 'strokeColor': '#333333', 'fillColor': 'none',
                                                         'dashStyle': '4.0,4.0' if meta['style'] == 'dash' else None,
                                                         'startArrow': 0, 'endArrow': 2 if meta['head'] else 0,
                                                         'startArrowRotation': 'auto', 'endArrowRotation': 'auto',
                                                         'ortho': False, 'interpolationType': 'linear', 'cornerRadius': None,
                                                         'controlPath': [[round(px - x0, 1), round(py - y0, 1)] for px, py in pts],
                                                         'lockSegments': {}}},
                    'children': [], 'layerId': LAYER,
                    'constraints': {'constraints': [],
                                    'startConstraint': {'type': 'StartPositionConstraint', 'StartPositionConstraint': {'nodeId': so, 'px': 0.5, 'py': 0.5}},
                                    'endConstraint': {'type': 'EndPositionConstraint', 'EndPositionConstraint': {'nodeId': do_, 'px': 0.5, 'py': 0.5}}},
                    'linkMap': []})
    if meta['label'] and ('lp' in e or 'xlp' in e):
        lx, ly = map(float, (e.get('lp') or e['xlp']).split(','))
        lw = max(len(l) for l in meta['label'].split('\n')) * 6.5 + 16
        lh = 16 * (meta['label'].count('\n') + 1) + 4
        objects.append(text_obj(meta['label'], round(lw, 1), lh, size=10, x=round(X(lx) - lw / 2, 1), y=round(Y(ly) - lh / 2, 1)))

W = X(float(lay['bb'].split(',')[2])) + 20
HH = Y(0) + 20
page = str(uuid.uuid4())[:10]
doc = {'contentType': 'application/gliffy+json', 'version': '2.0', 'title': TITLE, 'revision': 1, 'defaultPage': page,
       'lastSerialized': 0,
       'libraries': ['com.gliffy.libraries.flowchart.flowchart_v1.default', 'com.gliffy.libraries.basic.basic_v1.default'],
       'editorSettings': {'exportBorder': False, 'loadPosition': 'default', 'autosaveDisabled': False},
       'printModel': {'pageSize': 'a4', 'portrait': False, 'fitToOnePage': False, 'displayPageBreaks': False},
       'resources': [],
       'pages': [{'type': 'default', 'id': page, 'title': 'Page 1', 'index': 0, 'external': False,
                  'scene': {'objects': objects, 'imageCache': {}, 'background': '#FFFFFF', 'width': W, 'height': HH,
                            'maxWidth': 5000, 'maxHeight': 5000, 'nodeIndex': order[0] + 1, 'autoFit': True,
                            'exportBorder': False, 'gridOn': True, 'snapToGrid': False, 'drawingGuidesOn': True,
                            'diagramEditable': True, 'shapeStyles': {}, 'lineStyles': {}, 'textStyles': {},
                            'themeData': None, 'viewportType': 'default',
                            'layers': [{'guid': LAYER, 'order': 0, 'name': 'Layer 0', 'active': True, 'locked': False,
                                        'visible': True, 'nodeIndex': order[0]}],
                            'fitBB': {'min': {'x': 20, 'y': 20}, 'max': {'x': W, 'y': HH}}}}]}
json.dump(doc, open(OUT, 'w', encoding='utf-8'))
print(f'{OUT}: {len(nodes)} shapes, {len(clusters)} groups, {sum(1 for o in objects if o["uid"] and o["uid"].endswith("line"))} connectors, {W:.0f}x{HH:.0f}px')
