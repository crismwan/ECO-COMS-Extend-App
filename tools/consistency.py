#!/usr/bin/env python3
"""One-pass UI consistency fixes across hand-written pages (idempotent):
'ECO-COMS: ' title prefix, back-link wording and order, 'About this page' casing,
help text at 12px, timestamps shown as 'yyyy-MM-dd HH:mm:ss UTC'. Builders produce the same style."""
import json, os, re, glob
ROOT = os.path.join(os.path.dirname(__file__), '..', 'presentation')
TITLES = {
  'hubLanding': 'ECO-COMS: RBAC Hub', 'iscRoleRequestsHub': 'ECO-COMS: ISC Role Requests',
  'fuhLandingPage': 'ECO-COMS: Functional Unit Hierarchy Administration',
  'manageShellOrgStatusSuccess': 'ECO-COMS: Status Updated', 'newShellOrgPatternSuccess': 'ECO-COMS: Pattern Created',
  'newShellOrgSuccess': 'ECO-COMS: Shell Organization Created', 'roleAssignmentSuccess': 'ECO-COMS: Role Assignment Updated',
  'errorPage': 'ECO-COMS: Something went wrong',
}
PREFIX_SCRIPTED = {  # scripted titles: swap the leading literal
  'editRoleAssignment': ("'Manage Role Assignment: '", "'ECO-COMS: Manage Role Assignment – '"),
  'manageShellOrgStatus': ("'Change Status: '", "'ECO-COMS: Change Status – '"),
}
NAV = {'← Go to Home': '← Home', '← My Role Requests': '← Assignable Role Manager', '← Admin Provisioning': '← AAA Role Provisioning'}
HEADINGS = {'About This Page': 'About this page', 'Changes applied': 'Changes Applied Successfully'}
TS = re.compile(r"<% (\w+)\.timestamp \?\? '' %>")
changes = []
for f in sorted(glob.glob(os.path.join(ROOT, '*.pmd'))):
    n = os.path.basename(f)[:-4]; d = json.load(open(f)); before = json.dumps(d)
    pr = d.get('presentation', {})
    if n in TITLES and pr.get('title', {}).get('label') != TITLES[n]: pr['title']['label'] = TITLES[n]
    if n in PREFIX_SCRIPTED:
        old, new = PREFIX_SCRIPTED[n]; pr['title']['label'] = pr['title']['label'].replace(old, new)
    def walk(o):
        if isinstance(o, dict):
            if o.get('type') == 'button' and o.get('label') in NAV: o['label'] = NAV[o['label']]
            if o.get('type') == 'fieldSet' and o.get('title') in HEADINGS: o['title'] = HEADINGS[o['title']]
            if o.get('type') == 'richText' and isinstance(o.get('value'), str):
                o['value'] = re.sub(r'font-size:1[13]px', 'font-size:12px', o['value'])
            if isinstance(o.get('value'), str):
                o['value'] = TS.sub(lambda m: "<% (" + m.group(1) + ".timestamp ?? '').replace('T', ' ').replace('Z', ' UTC') %>", o['value'])
            # back links: the page-specific link first, Home last
            kids = o.get('children')
            if isinstance(kids, list) and len(kids) >= 2 and all(isinstance(k, dict) and k.get('type') == 'button' and k.get('action') == 'LINK' for k in kids[:2]):
                if kids[0].get('label') == '← Home' and str(kids[1].get('label', '')).startswith('←'):
                    kids[0], kids[1] = kids[1], kids[0]
            for v in o.values(): walk(v)
        elif isinstance(o, list):
            for v in o: walk(v)
    walk(pr)
    if json.dumps(d) != before:
        open(f, 'w').write(json.dumps(d, indent=2, ensure_ascii=False) + '\n'); changes.append(n)
print('changed:', changes)
