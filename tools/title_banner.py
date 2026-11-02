#!/usr/bin/env python3
"""Title tile (product owner 2026-11-02): a white rounded tile with the page title in blue, instead of Workday's
square blue page banner.

Workday's banner can't be styled (title: id/label/render only; headerSize STANDARD|HIDDEN). richText keeps only
color and font-size (2026-11-02 live), so the tile is a layoutSection box (white, rounded like the cards) holding
a richText title in the header blue. HIDDEN alone left the banner in place, so this trial also removes the title
tag on the listed pages. Idempotent; run last in rebuild_all.sh.
"""
import html, json, os
ROOT = os.path.join(os.path.dirname(__file__), '..', 'presentation')
PAGES = ['hubLanding']
BLUE = '#0055B3'
TITLES = {'hubLanding': 'ECO-COMS: RBAC Hub'}

for page in PAGES:
    p = os.path.join(ROOT, page + '.pmd')
    d = json.load(open(p))
    pres = d['presentation']
    label = TITLES.get(page) or (pres.get('title') or {}).get('label', '')
    pres['headerSize'] = 'HIDDEN'
    pres.pop('title', None)
    value = f'<span style="color:{BLUE};font-size:24px"><b>{html.escape(label)}</b></span>'
    sections = pres['body']['sections']
    sections[:] = [s for s in sections if s.get('id') != 'titleBannerSection']
    sections.insert(0, {"type": "layoutSection", "id": "titleBannerSection", "children": [
        {"type": "richText", "id": "titleBannerRichText", "enabled": False, "value": value}]})
    open(p, 'w').write(json.dumps(d, indent=2, ensure_ascii=False) + '\n')
    print(f'{page}: title tile')
