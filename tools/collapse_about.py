#!/usr/bin/env python3
"""Collapsible About boxes (product owner 2026-11-02): on the long pages the help text starts closed, so the form
or grid shows without scrolling. The back links sit beside the fieldSet in the same box (merge_nav_about.py), so
they stay visible. fieldSet attributes from Workday's sample apps: collapsible + initializeCollapsed. Idempotent.
"""
import json, os
ROOT = os.path.join(os.path.dirname(__file__), '..', 'presentation')
# 2026-11-02 (UI recommendations, item 4): also the daily-use list pages with long About text; a one-line summary
# under each page's title tile stays visible (ux_improvements.py --tiles)
# 2026-11-04: also every other page whose About text runs to 350+ characters
PAGES = ['bulkRoleChanges', 'bulkRoleTemplate', 'newSchemaPattern', 'iscRoleRequestsView', 'auditLogViewer', 'shellOrgManager',
         'bulkRoleGrid', 'bulkRoleResults', 'comsInsights', 'shellOrgDetail', 'bulkTemplateUpload', 'adminProvisioningView', 'accessReview']
done = []


def walk(n, page):
    if isinstance(n, dict):
        if n.get('type') == 'fieldSet' and str(n.get('title', '')).startswith('About This'):
            n['collapsible'] = True
            n['initializeCollapsed'] = True
            done.append(f"{page}.{n.get('id')}")
        for v in n.values(): walk(v, page)
    elif isinstance(n, list):
        for v in n: walk(v, page)


for page in PAGES:
    f = os.path.join(ROOT, page + '.pmd')
    d = json.load(open(f))
    walk(d['presentation'], page)
    open(f, 'w').write(json.dumps(d, indent=2, ensure_ascii=False) + '\n')
print('collapsible About boxes:', ', '.join(done))
