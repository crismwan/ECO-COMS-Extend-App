#!/usr/bin/env python3
"""Rounded title banner (product owner 2026-11-02: "change the ends of this rectangle to look more circular
like the cards").

Workday's page banner can't be styled: the title tag only has id/label/render, and presentation.headerSize is
STANDARD or HIDDEN (developer.workday.com "title", "presentation", checked 2026-11-02). So on the pages listed
here the Workday banner is hidden and the page starts with its own banner: a richText block in the app's header
blue (#0055B3) with rounded corners. The page title tag stays (browser tab name, per the docs).
Idempotent; run last in rebuild_all.sh.
"""
import html, json, os
ROOT = os.path.join(os.path.dirname(__file__), '..', 'presentation')
PAGES = ['hubLanding']
BLUE = '#0055B3'


def banner(label):
    # a static label is HTML-escaped; a scripted label (<% ... %>) is wrapped as a script string
    style = (f'display:block;background:{BLUE};color:#ffffff;border-radius:16px;padding:18px 24px;'
             'font-size:24px;font-weight:700;line-height:1.3')
    if label.strip().startswith('<%'):
        expr = label.strip()[2:-2].strip()
        return f"<% '<span style=\"{style}\">' + ({expr}) + '</span>' %>"
    return f'<span style="{style}">{html.escape(label)}</span>'


for page in PAGES:
    p = os.path.join(ROOT, page + '.pmd')
    d = json.load(open(p))
    pres = d['presentation']
    label = (pres.get('title') or {}).get('label', '')
    pres['headerSize'] = 'HIDDEN'
    sections = pres['body']['sections']
    sec = {"type": "layoutSection", "id": "titleBannerSection", "children": [
        {"type": "richText", "id": "titleBannerRichText", "enabled": False, "value": banner(label)}]}
    sections[:] = [s for s in sections if s.get('id') != 'titleBannerSection']
    sections.insert(0, sec)
    open(p, 'w').write(json.dumps(d, indent=2, ensure_ascii=False) + '\n')
    print(f'{page}: rounded title banner')
