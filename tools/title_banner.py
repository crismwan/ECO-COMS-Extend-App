#!/usr/bin/env python3
"""Title tile (product owner 2026-11-02): a white rounded tile with the page title in blue, instead of Workday's
square blue page banner.

Workday's banner can't be styled (title: id/label/render only; headerSize STANDARD|HIDDEN). richText keeps only
color and font-size (2026-11-02 live), so the tile is a layoutSection box (white, rounded like the cards) holding
a richText title in the header blue. HIDDEN alone left the banner in place, so this trial also removes the title
tag on the listed pages. Idempotent; run last in rebuild_all.sh.
"""
import glob, html, json, os, sys
ROOT = os.path.join(os.path.dirname(__file__), '..', 'presentation')
BLUE = '#0055B3'
STORE = os.path.join(os.path.dirname(__file__), 'page_titles.json')   # page -> original title label
STYLE = f'color:{BLUE};font-size:24px'
# Not converted: editWizard containers (the wizard must be the only body tag), wizard steps (the wizard shows
# its own title) and business-process step pages (they open in the Workday inbox, which titles the step).
BP_STEPS = {'reviewRoleRequestApproval', 'reviewRoleRequestAssignableRole', 'reviewRoleRequestDetails', 'reviewRoleRequestSecurityGroup'}

amd = json.load(open(os.path.join(ROOT, 'ecocomsphase_xclw_cm_sync2_vmzvxm.amd')))
task_page = {t['id']: t['page']['id'] for t in amd['tasks']}
wizard_steps = set()
for f in glob.glob(os.path.join(ROOT, '*.pmd')):
    b = json.load(open(f))['presentation'].get('body', {})
    if b.get('type') == 'editWizard':
        wizard_steps |= {task_page.get(t['task']['taskId'], t['task']['taskId']) for t in b.get('editTasks', [])}


def tile_value(label):
    label = label.strip()
    if label.startswith('<%'):
        expr = label[2:-2].strip()
        return f"<% '<span style=\"{STYLE}\"><b>' + ({expr}).replace('<', '&lt;') + '</b></span>' %>"
    return f'<span style="{STYLE}"><b>{html.escape(label)}</b></span>'


def restore():
    """Start of rebuild_all: put each converted page back to Workday's title (from page_titles.json), so every
    other builder sees ordinary pages; the last step converts them again."""
    titles = json.load(open(STORE)) if os.path.exists(STORE) else {}
    for page, label in titles.items():
        f = os.path.join(ROOT, page + '.pmd')
        if not os.path.exists(f): continue
        d = json.load(open(f)); pres = d['presentation']
        pres['body']['sections'] = [x for x in pres['body']['sections'] if x.get('id') != 'titleBannerSection']
        pres['title'] = {"type": "title", "label": label}
        pres['headerSize'] = 'STANDARD'
        open(f, 'w').write(json.dumps(d, indent=2, ensure_ascii=False) + '\n')
    print(f'restored Workday titles on {len(titles)} pages')


if '--restore' in sys.argv:
    restore(); sys.exit(0)

titles = {}
for f in sorted(glob.glob(os.path.join(ROOT, '*.pmd'))):
    d = json.load(open(f))
    page, pres = d['id'], d['presentation']
    body = pres.get('body', {})
    if body.get('type') != 'basicFormLayout' or page in wizard_steps or page in BP_STEPS:
        continue
    label = (pres.get('title') or {}).get('label')
    if not label:
        sys.exit(f'{page}: no title to turn into a tile (run with --restore first)')
    sections = body['sections']
    sections[:] = [x for x in sections if x.get('id') != 'titleBannerSection']
    sections.insert(0, {"type": "layoutSection", "id": "titleBannerSection", "children": [
        {"type": "richText", "id": "titleBannerRichText", "enabled": False, "value": tile_value(label)}]})
    pres.pop('title', None)
    pres['headerSize'] = 'HIDDEN'
    open(f, 'w').write(json.dumps(d, indent=2, ensure_ascii=False) + '\n')
    titles[page] = label
open(STORE, 'w').write(json.dumps(titles, indent=2, ensure_ascii=False) + '\n')
print(f'title tile on {len(titles)} pages')
