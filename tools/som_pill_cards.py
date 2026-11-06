#!/usr/bin/env python3
"""Shell Org Manager Application bar, Option E (2026-11-05): the cards the bar is built from.

Workday pill cards have a fixed list of pills and a pill can't be hidden, so a bar card with n pills uses the card
file SomPills<n> (n = 1..10, Workday's maximum per card), picked by a dynamic cardId in the page's dynamicCards.
Every pill reloads Shell Org Manager with its own appCode / family (empty = not set). comsAppIndex.barCards builds
the list: All applications (family pills) + No pattern format yet, a family's applications (10 per card), or the
narrowed application (previous, next, Change, All) + its pattern format card (Setup / Ready / Inactive).

Idempotent: rewrites the generated cards every run. `--off` removes them.
"""
import json, os, sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
CARDS = os.path.join(ROOT, 'presentation', 'cards')
OFF = '--off' in sys.argv
ICON = 'wd-accent-building'
FMT_ICON = 'wd-accent-worksheets'


def q(expr):
    return '<% ' + expr + ' %>'


def pills(n):
    params = ['titleText', 'subtitleText'] + [f'p{i}{k}' for i in range(1, n + 1) for k in ('Label', 'App', 'Fam')]
    return {
        "id": f"SomPills{n}",
        "parameters": params,
        "header": {"title": q('titleText ?? ""'), "subtitle": q('subtitleText ?? ""'), "icon": ICON},
        "body": {"type": "pillCard", "pills": [
            {"label": q(f'p{i}Label ?? ""'),
             "taskReference": {"taskId": "shellOrgManager", "parameterBindings": {
                 "appCode": q(f'p{i}App ?? ""'), "appName": q(f'p{i}App ?? ""'), "family": q(f'p{i}Fam ?? ""')}}}
            for i in range(1, n + 1)]},
    }


def fmt(cid, params, indicator, color, subtitle, body, footer):
    return {"id": cid, "parameters": params,
            "header": {"title": "Pattern format", "subtitle": subtitle, "icon": FMT_ICON,
                       "indicator": {"label": indicator, "color": color}},
            "body": {"type": "simpleCard", "value": body}, "footer": footer}


MAINTAIN = {"label": "Maintain Application Pattern",
            "taskReference": {"taskId": "editAppPattern", "parameterBindings": {"recordId": q('recordId ?? ""')}}}
GEN = {f"SomPills{n}": pills(n) for n in range(1, 11)}
GEN["AppFormatSetupCard"] = fmt(
    "AppFormatSetupCard", ["appCode"], "No pattern yet", "orange", q('"Not set up for " + (appCode ?? "")'),
    "Patterns can be added once the format is set.",
    [{"label": "Set Up Pattern Format", "taskReference": {"taskId": "editAppPattern"}}])
GEN["AppFormatReadyCard"] = fmt(
    "AppFormatReadyCard", ["appCode", "recordId", "summaryText"], "Ready", "green", q('appCode ?? ""'), q('summaryText ?? ""'),
    [{"label": "Add Pattern", "taskReference": {"taskId": "newSchemaPattern", "parameterBindings": {"appCode": q('appCode ?? ""')}}},
     MAINTAIN])
GEN["AppFormatInactiveCard"] = fmt(
    "AppFormatInactiveCard", ["appCode", "recordId"], "Inactive", "gray", q('appCode ?? ""'),
    "This application's pattern format is inactive, so no patterns can be added until it is reactivated.", [MAINTAIN])
OLD = ["AppBarAllCard", "AppBarNarrowedCard", "FamilyPickCard", "AppPickCard"]   # Option D cards, replaced

for cid in OLD:
    p = os.path.join(CARDS, cid + '.card')
    if os.path.exists(p): os.remove(p)
for cid, card in GEN.items():
    p = os.path.join(CARDS, cid + '.card')
    if OFF:
        if os.path.exists(p): os.remove(p)
    else:
        open(p, 'w').write(json.dumps(card, indent=2, ensure_ascii=False) + '\n')
print('Shell Org Manager bar cards: ' + ('removed' if OFF else f'{len(GEN)} written'))
