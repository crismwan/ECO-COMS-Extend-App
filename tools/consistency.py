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
  'assignableRoleManager': 'ECO-COMS: Submit Assignable Role Request',
  'adminProvisioning': 'ECO-COMS: Submit AAA Role Request',
}
# request forms go back to their list page, not Home
BACK = {'assignableRoleManager': ('← Assignable Role Manager', 'assignableRoleManagerView'),
        'adminProvisioning': ('← AAA Role Provisioning', 'adminProvisioningView')}
PREFIX_SCRIPTED = {  # scripted titles: swap the leading literal
  'editRoleAssignment': ("'Manage Role Assignment: '", "'ECO-COMS: Manage Role Assignment – '"),
  'manageShellOrgStatus': ("'Change Status: '", "'ECO-COMS: Change Status – '"),
}
NAV = {'Back to Shell Org Manager': 'View in Shell Org Manager', 'Manage this role again': 'Manage This Role Again', '← Go to Home': '← Home', '← My Role Requests': '← Assignable Role Manager', '← Admin Provisioning': '← AAA Role Provisioning'}
HEADINGS = {'About This Page': 'About this page', 'Changes applied': 'Changes Applied Successfully', 'Status Change Warning': 'Before you submit'}
WIZARD_TITLE = 'ECO-COMS: Shell Org Manager'
TS = re.compile(r"<% (\w+)\.timestamp \?\? '' %>")
changes = []
for f in sorted(glob.glob(os.path.join(ROOT, '*.pmd'))):
    n = os.path.basename(f)[:-4]; d = json.load(open(f)); before = json.dumps(d)
    pr = d.get('presentation', {})
    if n in TITLES and pr.get('title', {}).get('label') != TITLES[n]: pr['title']['label'] = TITLES[n]
    body = pr.get('body', {})
    if isinstance(body, dict) and body.get('type') == 'editWizard' and body.get('title') != WIZARD_TITLE:
        body['title'] = WIZARD_TITLE
    if n in PREFIX_SCRIPTED:
        old, new = PREFIX_SCRIPTED[n]; pr['title']['label'] = pr['title']['label'].replace(old, new)
    def walk(o):
        if isinstance(o, dict):
            if o.get('type') == 'button' and o.get('label') in NAV: o['label'] = NAV[o['label']]
            if o.get('type') == 'fieldSet' and o.get('title') in HEADINGS: o['title'] = HEADINGS[o['title']]
            if o.get('type') == 'richText' and isinstance(o.get('value'), str):
                o['value'] = re.sub(r'font-size:1[13]px', 'font-size:12px', o['value']).replace('ℹ', 'ⓘ')
            if n in BACK and o.get('type') == 'button' and o.get('label') == '← Home':
                o['label'], o['taskReference'] = BACK[n][0], {"taskId": BACK[n][1]}
            if isinstance(o.get('value'), str):
                o['value'] = TS.sub(lambda m: "<% (" + m.group(1) + ".timestamp ?? '').replace('T', ' ').replace('Z', ' UTC') %>", o['value'])
            # edit pages: one back link (the page-specific one); the form's Cancel covers the rest
            kids0 = o.get('children')
            if (pr.get('pageType') == 'EDIT' and isinstance(kids0, list) and len(kids0) >= 2
                    and all(isinstance(k, dict) and k.get('type') == 'button' and k.get('action') == 'LINK' for k in kids0)
                    and any(k.get('label') == '← Home' for k in kids0) and any(str(k.get('label', '')).startswith('←') and k.get('label') != '← Home' for k in kids0)):
                o['children'] = [k for k in kids0 if k.get('label') != '← Home']
            # back links: the page-specific link first, Home last
            kids = o.get('children')
            if isinstance(kids, list) and len(kids) >= 2 and all(isinstance(k, dict) and k.get('type') == 'button' and k.get('action') == 'LINK' for k in kids[:2]):
                if kids[0].get('label') == '← Home' and str(kids[1].get('label', '')).startswith('←'):
                    kids[0], kids[1] = kids[1], kids[0]
            for v in o.values(): walk(v)
        elif isinstance(o, list):
            for v in o: walk(v)
    walk(pr)
    # success pages: the confirmation message first, then the receipt card
    if n.endswith('Success') and isinstance(pr.get('body'), dict):
        secs = pr['body'].get('sections', [])
        kinds = [('card' if any(k.get('type') == 'cardContainer' for k in s_.get('children', [])) else
                  'msg' if any(k.get('type') == 'fieldSet' for k in s_.get('children', [])) else 'other') for s_ in secs]
        if 'card' in kinds and 'msg' in kinds and kinds.index('card') < kinds.index('msg'):
            i, j = kinds.index('card'), kinds.index('msg'); secs[i], secs[j] = secs[j], secs[i]
    if json.dumps(d) != before:
        open(f, 'w').write(json.dumps(d, indent=2, ensure_ascii=False) + '\n'); changes.append(n)
print('changed:', changes)
