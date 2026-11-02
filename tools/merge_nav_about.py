#!/usr/bin/env python3
"""Back links in the About box (product owner 2026-11-02: "move Home to above About This Page").

Pages had a box of back links (navSection: "← Home", "← Shell Org Manager", ...) and then a separate About box.
This moves the links into the top of the About box, above its "About This Page" heading, so the page starts
with one box instead of two. Only pages whose navSection is directly followed by a section holding an
"About This Page" fieldSet are changed (success pages keep their links at the bottom).

Like title_banner.py: `--restore` (first step of rebuild_all) splits the links back into navSection, so every
other builder sees the usual layout; the plain run (near the end) merges them again. Merged pages are kept in
tools/nav_merged.json.
"""
import glob, json, os, sys
ROOT = os.path.join(os.path.dirname(__file__), '..', 'presentation')
STORE = os.path.join(os.path.dirname(__file__), 'nav_merged.json')


def save(f, d):
    open(f, 'w').write(json.dumps(d, indent=2, ensure_ascii=False) + '\n')


def is_about(sec):
    kids = sec.get('children') or []
    return bool(kids) and isinstance(kids[0], dict) and kids[0].get('type') == 'fieldSet' and kids[0].get('title') == 'About This Page'


if '--restore' in sys.argv:
    merged = json.load(open(STORE)) if os.path.exists(STORE) else {}
    for page, about_id in merged.items():
        f = os.path.join(ROOT, page + '.pmd')
        if not os.path.exists(f): continue
        d = json.load(open(f)); secs = d['presentation']['body']['sections']
        i = [s.get('id') for s in secs].index(about_id)
        kids = secs[i]['children']
        n = next(k for k, c in enumerate(kids) if c.get('type') == 'fieldSet')
        links, secs[i]['children'] = kids[:n], kids[n:]
        if links:
            secs.insert(i, {"type": "layoutSection", "id": "navSection", "children": links})
        save(f, d)
    print(f'back links split out again on {len(merged)} pages')
    sys.exit(0)

merged = {}
for f in sorted(glob.glob(os.path.join(ROOT, '*.pmd'))):
    d = json.load(open(f))
    body = d['presentation'].get('body', {})
    if body.get('type') != 'basicFormLayout': continue
    secs = body['sections']
    ids = [s.get('id') for s in secs]
    if 'navSection' not in ids: continue
    i = ids.index('navSection')
    nav = secs[i]
    if i + 1 >= len(secs) or not is_about(secs[i + 1]) or nav.get('render') or nav.get('visible'): continue
    if not all(isinstance(c, dict) and c.get('type') == 'button' for c in nav['children']): continue
    secs[i + 1]['children'] = nav['children'] + secs[i + 1]['children']
    del secs[i]
    save(f, d)
    merged[d['id']] = secs[i]['id']
save(STORE, merged)
print(f'back links moved into the About box on {len(merged)} pages')
