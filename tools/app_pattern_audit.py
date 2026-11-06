#!/usr/bin/env python3
"""Application Pattern records in the Audit Log link to their application's organization (product owner 2026-11-06;
until then they linked the application record, labelled "(application pattern)").

The Organization cell of an "Application Pattern" row shows the application-level organization (code = the application
ID, e.g. X:ADM) as a Workday instance, so its related actions are the organization's own. The organization is found by
code through a small WQL list (`code in (...)` over the application IDs that have a record; developer.workday.com
"WHERE": `in` works on text). Records of an application with no such organization show the ID as text.

Before 2026-11-06:

The Organization cell of an "Application Pattern" row shows the application record (COMSApplication) as an instance,
so its related actions include "Maintain Application Pattern" (model/MaintainApplicationPattern.task), which opens the
format. The record is found by the application ID the audit record stores (coReferenceId), through a small list of the
application records; this also covers records written when an application was added, whose record ID wasn't known yet.
The list leaves 403 out of failOnStatusCodes: someone who can read the Audit Log but not the application setup just
sees the ID as text. Idempotent; runs after audit_filters_more.py.
"""
import json, os
ROOT = os.path.join(os.path.dirname(__file__), '..', 'presentation')
f = os.path.join(ROOT, 'auditLogViewer.pmd')
d = json.load(open(f, encoding='utf-8'))

EP = {"name": "auditApplications", "baseUrlType": "BUSINESS-OBJECT", "url": "/comsApplications?limit=100", "authType": "sso",
      "isCollection": True, "bestEffort": "true", "failOnStatusCodes": [{"code": 400}, {"code": 429}]}
# Application IDs come from the app's own records; quotes are stripped all the same before they go into WQL.
CODES = "(auditApplications.data ?? []).map(a => { '\\'' + (a.appId ?? '').replace('\\'', '').replace('\\\\', '') + '\\'' }).join(',')"
ORGS = {"name": "auditAppOrgs", "baseUrlType": "workday-wql", "authType": "sso", "bestEffort": "true",
        "url": "<% 'data?limit=200&query=' + string:pathEncode('SELECT workdayID, code FROM topLevelOrganizations WHERE code in (' + "
               + CODES + " + ')') %>",
        "exclude": "<% empty(auditApplications.data) %>",
        "failOnStatusCodes": [{"code": 429}]}
d['endPoints'] = [e for e in d['endPoints'] if e.get('name') not in ('auditApplications', 'auditAppOrgs')] + [EP, ORGS]

# Lookup by position, with no closure and no list:filter on the row's value: both found nothing inside a grid cell
# (live 2026-11-05), while indexOf on a plain list of codes works.
IDX = "(auditAppOrgs.data ?? []).map(o => { o.code ?? '' }).indexOf(logEntry.coName ?? '')"
APP = (f"((logEntry.objectType == 'Application Pattern' && {IDX} >= 0) ? "
       f"[(auditAppOrgs.data ?? []).get({IDX})] : [])")
ORG = "(empty(logEntry.orgWid) ? [] : [{'id': logEntry.orgWid, 'descriptor': logEntry.coName ?? ''}])"
VALUES = f"<% let o = {ORG}; o.size() > 0 ? o : {APP}.map(a => {{ {{'id': a.workdayID ?? '', 'descriptor': logEntry.coName ?? ''}} }}) %>"
HAS = f"(!empty(logEntry.orgWid) || {APP}.size() > 0)"

done = []
def walk(n):
    if isinstance(n, dict):
        if n.get('columnId') == 'columnOrganization':
            for c in n['cellTemplate']['children']:
                if c.get('id') == 'organizationInstanceList':
                    c['values'] = VALUES
                    c['visible'] = f"<% {HAS} %>"
                elif c.get('id') == 'organizationText':
                    c['visible'] = f"<% !{HAS} %>"
            done.append('columnOrganization')
        for v in n.values(): walk(v)
    elif isinstance(n, list):
        for v in n: walk(v)
walk(d)
if not done: raise SystemExit('auditLogViewer: Organization column not found')
open(f, 'w', encoding='utf-8').write(json.dumps(d, indent=2, ensure_ascii=False) + '\n')
print('Audit Log: Application Pattern rows link to their application organization')
