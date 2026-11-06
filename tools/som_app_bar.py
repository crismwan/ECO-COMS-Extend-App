#!/usr/bin/env python3
"""Shell Org Manager, Option D (product owner 2026-11-05, design canvas "Shell Org Manager application filter
options"): the page opens on every application as before; an Application bar above the tabs narrows it.

- Application list = every X: organization's code cut to its application ID (the rule Add Shell Org and AAA Role
  Request use: X:BPMS(AOC), X:APP), plus pattern records, so a new X: organization shows up by itself
  (`presentation/scripts/comsAppIndex.script`). Families: X:FAM(...) applications, plus X:FAM itself; the rest are
  Standalone.
- Bar (cards AppBarAllCard / AppBarNarrowedCard): "Narrow down" opens ?pick=1 (family cards, FamilyPickCard);
  a family opens ?pick=1&family=F (application cards, AppPickCard); an application reloads with ?appCode=, exactly
  as the Manage button does. Narrowed: Change application, Show all applications, Previous / Next in the family.
- Applications grid (Application Patterns tab) lists every application, "No pattern yet" where there is no record;
  Add Pattern only for an active record, otherwise "Set Up Pattern Format" (Maintain Application Pattern, Add).
- Role assignments match the narrowed application exactly (X:LLIS no longer picks up X:LLIS(CPE) roles).
- The yellow "No application selected" banner is replaced by the bar.

Idempotent. Rollback: `python3 tools/som_app_bar.py --off` (restores the saved banner and expressions).
"""
import json, os, sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
P = os.path.join(ROOT, 'presentation', 'shellOrgManager.pmd')
SAVE = os.path.join(ROOT, 'tools', 'som_app_bar_saved.json')
OFF = '--off' in sys.argv
INC = 'comsAppIndex.script'
ARGS = "allShellOrgs.data, comsApplications.data"
PICK = "(queryParams.pick ?? '')"
APP = "(queryParams.appCode ?? '')"
FAM = "(queryParams.family ?? '')"

OLD_RA = "ra.organization.descriptor.startsWith((empty(queryParams.appCode) ? 'X:' : queryParams.appCode))"
NEW_RA = ("(empty(queryParams.appCode) ? ra.organization.descriptor.startsWith('X:') : (ra.organization.descriptor == queryParams.appCode"
          " || ra.organization.descriptor.startsWith(queryParams.appCode + ':') || ra.organization.descriptor.startsWith(queryParams.appCode + ' ')))")
OLD_ROWS = "(comsApplications.data ?? []).filter(a => { !empty(a.patternSchema) }).map(a => { a.appId }).distinct().sort().map(appCode => { {'appCode': appCode} })"
NEW_ROWS = f"comsAppIndex.appIds({ARGS}).map(appCode => {{ {{'appCode': appCode}} }})"
OLD_FMT = "comsPatterns.summary(comsApplications.data, app.appCode)"
NEW_FMT = "(empty(comsPatterns.recordFor(comsApplications.data, app.appCode)) ? 'No pattern yet' : comsPatterns.summary(comsApplications.data, app.appCode))"
OLD_ADD = "(comsApplications.data ?? []).filter(a => { a.appId == (queryParams.appCode ?? '') && a.active == false }).size() == 0"
NEW_ADD = "(comsApplications.data ?? []).filter(a => { a.appId == (queryParams.appCode ?? '') && a.active != false }).size() > 0"
OLD_WARN = "You selected <b><% queryParams.appCode ?? '' %></b> from the Application Patterns tab. Only shell organizations matching this application are shown below. <a href=\"javascript:void(0)\" style=\"color:#0055B7\">View all organizations</a> by navigating to Shell Org Manager without an application selected."
NEW_WARN = "Narrowed to <b><% queryParams.appCode ?? '' %></b>: only its shell organizations are shown below. Use Show all applications on the Application card above to see every organization."
OLD_EMPTY = "No shell org patterns found for this application. Use the Add Pattern button above to create one."
REC = "(comsApplications.data ?? []).filter(a => { a.appId == (queryParams.appCode ?? '')"
NEW_EMPTY = ("<% " + REC + " }).size() == 0"
             " ? 'No pattern format is set up for this application yet. Use Set Up Pattern Format above first, then add patterns.'"
             " : (" + REC + " && a.active != false }).size() == 0"
             " ? 'The pattern format for this application is inactive. Reactivate it in Maintain Application Pattern to add patterns.'"
             " : '" + OLD_EMPTY + "') %>")
SWAPS = [(OLD_EMPTY, NEW_EMPTY), (OLD_RA, NEW_RA), (OLD_ROWS, NEW_ROWS), (OLD_FMT, NEW_FMT), (OLD_ADD, NEW_ADD), (OLD_WARN, NEW_WARN)]


def containers():
    return [
        {"type": "cardContainer", "id": "appBarCardContainer", "layout": "masonry",
         "cards": [
             {"type": "card", "cardId": "AppBarAllCard", "render": "<% empty(queryParams.appCode) %>",
              "parameters": f"<% comsAppIndex.barAll({ARGS}, {PICK}) %>"},
             {"type": "card", "cardId": "AppBarNarrowedCard", "render": "<% !empty(queryParams.appCode) %>",
              "parameters": f"<% comsAppIndex.barNarrowed({ARGS}, {APP}, {PICK}) %>"}],
         "dynamicCards": {"on": f"<% comsAppIndex.familyCards({ARGS}, {PICK}, {FAM}, {APP}) %>", "as": "fam",
                          "template": {"cardId": "FamilyPickCard", "parameters": "<% fam %>"}}},
        {"type": "cardContainer", "id": "appPickCardContainer", "layout": "masonry",
         "render": f"<% {PICK} == '1' && !empty(queryParams.family) %>",
         "dynamicCards": {"on": f"<% comsAppIndex.appCards({ARGS}, {PICK}, {FAM}, {APP}) %>", "as": "pickApp",
                          "template": {"cardId": "AppPickCard", "parameters": "<% pickApp %>"}}},
    ]


SETUP_BTN = {"type": "button", "id": "setupPatternBtn", "label": "Set Up Pattern Format", "action": "AUXILIARY",
             "render": "<% !empty(queryParams.appCode) && (comsApplications.data ?? []).filter(a => { a.appId == (queryParams.appCode ?? '') }).size() == 0 %>",
             "taskReference": {"taskId": "editAppPattern"}}


def find(n, pred, parent=None):
    if isinstance(n, dict):
        if pred(n): return n, parent
        for v in n.values():
            r = find(v, pred, n)
            if r: return r
    elif isinstance(n, list):
        for v in n:
            r = find(v, pred, n)
            if r: return r
    return None


def swap(n, a, b, guard=True):
    """Replace a with b in every string; with guard, skip strings that already hold b (b may contain a)."""
    rep = lambda v: v if (guard and b in v) else v.replace(a, b)
    if isinstance(n, dict):
        for k, v in n.items():
            if isinstance(v, str): n[k] = rep(v)
            else: swap(v, a, b, guard)
    elif isinstance(n, list):
        for i, v in enumerate(n):
            if isinstance(v, str): n[i] = rep(v)
            else: swap(v, a, b, guard)


d = json.load(open(P))
nav = find(d['presentation'], lambda x: x.get('id') == 'navSection')[0]
kids = nav['children']
kids[:] = [k for k in kids if k.get('id') not in ('appBarCardContainer', 'appPickCardContainer')]
navfs = next(k for k in kids if k.get('id') == 'navFieldSet')
fs_kids = navfs['children']
banner = next((k for k in fs_kids if k.get('id') == 'scopeWarning'), None)
patfs = find(d['presentation'], lambda x: x.get('id') == 'patternsFieldSet')[0]
patfs['children'] = [k for k in patfs['children'] if k.get('id') != 'setupPatternBtn']

if OFF:
    if os.path.exists(SAVE) and banner is None:
        fs_kids.append(json.load(open(SAVE))['scopeWarning'])
    for a, b in SWAPS: swap(d['presentation'], b, a, guard=False)
    d['include'] = [i for i in d.get('include', []) if i != INC]
else:
    if banner is not None:
        json.dump({'scopeWarning': banner}, open(SAVE, 'w'), indent=1, ensure_ascii=False)
        fs_kids.remove(banner)
    for a, b in SWAPS: swap(d['presentation'], a, b)
    raw = []
    def texts(n):
        if isinstance(n, dict): [texts(v) for v in n.values()]
        elif isinstance(n, list): [texts(v) for v in n]
        elif isinstance(n, str): raw.append(n)
    texts(d['presentation'])
    for a, b in SWAPS: assert any(b in t for t in raw), 'not applied: ' + a[:60]
    kids.extend(containers())
    add = next(i for i, k in enumerate(patfs['children']) if k.get('id') == 'addPatternBtn')
    patfs['children'].insert(add + 1, SETUP_BTN)
    if INC not in d.get('include', []): d.setdefault('include', []).append(INC)

open(P, 'w').write(json.dumps(d, indent=2, ensure_ascii=False) + '\n')
print('shellOrgManager: Application bar ' + ('removed' if OFF else 'on (all applications, narrow down by family)'))
