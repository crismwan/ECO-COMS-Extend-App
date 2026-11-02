#!/usr/bin/env python3
"""Collapsible About boxes (product owner 2026-11-02): on the long pages the help text starts closed, so the form
or grid shows without scrolling. The back links sit beside the fieldSet in the same box (merge_nav_about.py), so
they stay visible. fieldSet attributes from Workday's sample apps: collapsible + initializeCollapsed. Idempotent.
"""
import json, os
ROOT = os.path.join(os.path.dirname(__file__), '..', 'presentation')
PAGES = ['bulkRoleChanges', 'bulkRoleTemplate', 'newSchemaPattern']
done = []
for page in PAGES:
    f = os.path.join(ROOT, page + '.pmd')
    d = json.load(open(f))
    for sec in d['presentation']['body']['sections']:
        for k in sec.get('children', []):
            if k.get('type') == 'fieldSet' and k.get('id') == 'aboutFieldSet':
                k['collapsible'] = True
                k['initializeCollapsed'] = True
                done.append(page)
    open(f, 'w').write(json.dumps(d, indent=2, ensure_ascii=False) + '\n')
print('collapsible About boxes:', ', '.join(done))
