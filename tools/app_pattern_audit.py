#!/usr/bin/env python3
"""Application Pattern records in the Audit Log link to their application (product owner 2026-11-05).

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
d['endPoints'] = [e for e in d['endPoints'] if e.get('name') != 'auditApplications'] + [EP]

APP = ("(logEntry.objectType == 'Application Pattern' ? (auditApplications.data ?? [])"
       ".filter(a => { a.appId == (logEntry.coReferenceId ?? '') }) : [])")
ORG = "(empty(logEntry.orgWid) ? [] : [{'id': logEntry.orgWid, 'descriptor': logEntry.coName ?? ''}])"
VALUES = f"<% let o = {ORG}; o.size() > 0 ? o : {APP}.map(a => {{ {{'id': a.id, 'descriptor': (logEntry.coName ?? '') + ' (application pattern)'}} }}) %>"
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
print('Audit Log: Application Pattern rows link to their application record')
