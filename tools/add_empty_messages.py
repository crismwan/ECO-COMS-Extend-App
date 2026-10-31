#!/usr/bin/env python3
"""Adds a 'Nothing to show' text (visible only when the grid has no rows) just before main grids,
explaining why the grid is empty. Idempotent. Re-run after a page builder rewrites a page."""
import json, os
ROOT = os.path.join(os.path.dirname(__file__), '..', 'presentation')
MESSAGES = {
  'assignableRoleManagerView.pmd': {'assignableRolesGrid': "You haven't submitted any assignable role requests. Use Submit New Request to start one."},
  'adminProvisioningView.pmd': {'aaaRolesGrid': "No AAA role requests yet. Use Submit AAA Role Request to start one."},
  'iscRoleRequestsView.pmd': {'allPendingGrid': "No requests match this view and status. Choose All to see every request."},
  # the org and pattern grids already have their own empty messages
  'shellOrgManager.pmd': {'roleAssignmentsGrid': "No shell roles are assigned on these organizations."},
  'bulkRoleResults.pmd': {'uploadsGrid': "You haven't uploaded a file yet. Download the template, fill in the Action column, and upload it.",
                          'rowResultsGrid': "No row results for this upload yet. If its status is Uploaded, Queued or Running, click Refresh in a minute."},
  'auditLogViewer.pmd': {},
}
def strip(rows): return rows.strip()[2:-2].strip()
for page, grids in MESSAGES.items():
    path = os.path.join(ROOT, page); d = json.load(open(path)); done = []
    def walk(o):
        if isinstance(o, dict):
            kids = o.get('children')
            if o.get('type') == 'fieldSet' and isinstance(kids, list):
                for i, k in enumerate(list(kids)):
                    if isinstance(k, dict) and k.get('type') == 'grid' and k.get('id') in grids:
                        tid = k['id'].replace('Grid', '') + 'EmptyText'
                        if any(isinstance(x, dict) and x.get('id') == tid for x in kids): done.append(k['id']); continue
                        rows = k.get('rows', '')
                        if not (rows.strip().startswith('<%') and rows.strip().endswith('%>')): continue
                        kids.insert(kids.index(k), {"type": "text", "id": tid, "enabled": False, "label": "ⓘ Nothing to show",
                            "visible": "<% size(" + strip(rows) + ") == 0 %>", "value": grids[k['id']]})
                        done.append(k['id'])
            for v in list(o.values()): walk(v)
        elif isinstance(o, list):
            for v in list(o): walk(v)
    walk(d['presentation'])
    missing = set(grids) - set(done)
    if missing: print(page, 'NOT ADDED (grid not directly in a fieldSet):', missing)
    open(path, 'w').write(json.dumps(d, indent=2, ensure_ascii=False) + '\n')
print('done')
