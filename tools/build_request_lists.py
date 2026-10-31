#!/usr/bin/env python3
"""Same layout on both request list pages (Assignable Role Manager, AAA Role Provisioning):
back link only in the nav, 'About this page' heading, cards Pending / Decided / Actions (three per row),
one empty message in the shared style. Idempotent."""
import json, os, re
ROOT = os.path.join(os.path.dirname(__file__), '..', 'presentation')
load = lambda n: json.load(open(os.path.join(ROOT, n)))
def save(n, d): open(os.path.join(ROOT, n), 'w').write(json.dumps(d, indent=2, ensure_ascii=False) + '\n')
PAGES = {
  'assignableRoleManagerView.pmd': ('ListAssignableActionsCard', 'Assignable role requests', [("Submit New Request", "assignableRoleManager", None), ("Withdraw Request", "deleteAssignableRole", "assignable")], 'assignableRolesEmptyText'),
  'adminProvisioningView.pmd': ('ListAaaActionsCard', 'AAA role requests', [("Submit AAA Role Request", "adminProvisioning", None), ("Withdraw Request", "deleteAssignableRole", "aaa")], 'aaaRolesEmptyText'),
}
for page, (card_id, sub, pills, my_empty) in PAGES.items():
    card = {"id": card_id, "header": {"title": "Actions", "subtitle": sub, "icon": "wd-accent-clipboard-checklist"},
            "body": {"type": "pillCard", "pills": [
                {"label": l, "taskReference": ({"taskId": t, "parameterBindings": {"view": v}} if v else {"taskId": t})} for l, t, v in pills]}}
    open(os.path.join(ROOT, 'cards', card_id + '.card'), 'w').write(json.dumps(card, indent=2, ensure_ascii=False) + '\n')
    d = load(page); secs = d['presentation']['body']['sections']
    for s in secs:
        if s.get('id') == 'navSection':
            s['children'] = [b for b in s['children'] if b.get('action') == 'LINK']
        if s.get('id') == 'descSection':
            kids = s['children']
            if not any(k.get('type') == 'fieldSet' for k in kids):
                desc = next(k for k in kids if k.get('id') == 'pageDesc')
                kids[kids.index(desc)] = {"type": "fieldSet", "id": "aboutFieldSet", "title": "About this page", "children": [desc]}
        for k in s.get('children', []):
            if k.get('type') == 'cardContainer' and len(k.get('cards', [])) >= 3 and k['cards'][0]['cardId'] == 'CountCard':
                cards = [c for c in k['cards'] if c['cardId'] == 'CountCard']
                titles = [re.search(r"'title': '(\w+)'", c['parameters']).group(1) for c in cards]
                if titles[:3] == ['Pending', 'Approved', 'Denied']:
                    count = lambda c: c['parameters'].split("'countText': ")[1].rsplit(' }', 1)[0]
                    decided = ("<% { 'title': 'Decided', 'subtitle': 'Approved, denied or withdrawn', 'countText': "
                               + count(cards[1]) + " + ' · ' + " + count(cards[2]) + " } %>")
                    k['cards'] = [cards[0], {"type": "card", "cardId": "CountCard", "parameters": decided}, {"type": "card", "cardId": card_id}]
            if k.get('type') == 'fieldSet':
                kids = k['children']
                orig = next((c for c in kids if c.get('id') == 'emptyStateMsg'), None)
                if orig:   # keep the page's own message, in the shared style; drop the duplicate
                    kids[kids.index(orig)] = {"type": "text", "id": "emptyStateMsg", "enabled": False, "label": "ⓘ Nothing to show",
                        "visible": orig['visible'], "value": re.sub(r'<[^>]+>', '', orig['value']).replace('Click', 'Use').strip()}
                k['children'] = [c for c in k['children'] if c.get('id') != my_empty]
    save(page, d)
print('ok')
