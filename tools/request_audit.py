#!/usr/bin/env python3
"""REQUEST audit records are written by the orchestration that starts the review, so they carry the
review event and the run ID like every other audit record (2026-11-04).

Before: the request pages wrote the REQUEST record themselves, before the review event existed, so it
had no event. Now IORC_0037_XFD_SEC_Start_Role_Request_Review / IORC_0037_XFD_SEC_Start_Admin_Request_Review write it after SaveEventOnRequest,
from the request record they already read (FindRequest), and the pages no longer write it (one writer
per change). Nodes are cloned from the same orchestration (SaveEventOnRequest, ExtractRequest) so the
credential and wrappers stay as App Builder writes them. Idempotent.
"""
import copy, json, os

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
FLOWS = {
    'IORC_0037_XFD_SEC_Start_Role_Request_Review': ('assignableRoleManager',
        'Assignable role request submitted: {{data.ExtractRequest.roleName}} for org {{data.AuditValues.coName}}'),
    'IORC_0037_XFD_SEC_Start_Admin_Request_Review': ('adminProvisioning',
        'AAA role request submitted: {{data.ExtractRequest.roleName}} effective {{data.AuditValues.effectiveDate}}'),
}
J = 'data.FindRequest.response.asJSON().stringAtJsonPathWithDefault("$.data[0].{f}", "")'
CLEAN = '.normalizeSpace().replace("\\\\", "/").replace("\\"", "\'")'   # free text into a JSON template


def expr(src):
    return {"_type": ["Expr", "String"], "_value": {"type": {"_type": "Type", "_value": "String"},
            "source": {"_type": "String", "_value": src}, "isAuto": {"_type": "Boolean", "_value": False}}}


def assignment(proto, name, src):
    a = copy.deepcopy(proto)
    a['_value']['param']['_value']['name']['_value'] = name
    a['_value']['param']['_value']['type']['_value'] = 'String'
    a['_value']['expr'] = expr(src)
    return a


def named(lst, name):
    return next((n for n in lst if n['_value']['name']['_value'] == name), None)


def patch_flow(name, details):
    p = os.path.join(ROOT, 'orchestration', name + '.orchestration')
    raw = open(p, encoding='utf-8').read()
    d = json.loads(raw)
    nodes = d['_value']['nodes']['_value']
    if named(nodes, 'WriteAuditLog'):
        return 0
    gip = named(nodes, 'GetInputParams')
    proto = gip['_value']['values']['_value'][0]
    have = {a['_value']['param']['_value']['name']['_value'] for a in gip['_value']['values']['_value']}
    for n_, src in [('timestamp', 'datetime.now("UTC").format("yyyy-MM-dd\'T\'HH:mm:ss\'Z\'")'), ('runId', 'context.orchestrateId()')]:
        if n_ not in have:
            gip['_value']['values']['_value'].append(assignment(proto, n_, src))
    vals = copy.deepcopy(named(nodes, 'ExtractRequest'))
    vals['_value']['name']['_value'] = 'AuditValues'
    V = 'data.AuditValues.'
    vals['_value']['values']['_value'] = [assignment(proto, k, s) for k, s in [
        ('referenceId', J.format(f='referenceId')),
        ('orgCode', J.format(f='shellOrgCode')),
        ('application', J.format(f='application')),
        ('coName', f'if ({V}orgCode.equals("")) {V}application else {V}orgCode'),
        ('positionWids', J.format(f='positions')),
        ('positionNames', J.format(f='positionNames') + CLEAN),
        ('positions', f'if ({V}positionNames.equals("")) {V}positionWids else {V}positionNames'),
        ('effectiveDate', J.format(f='effectiveDate')),
        ('requesterName', J.format(f='requestedBy.descriptor') + CLEAN),
        ('requesterWid', J.format(f='requestedBy.id')),
    ]]
    write = copy.deepcopy(named(nodes, 'SaveEventOnRequest'))
    write['_value']['name']['_value'] = 'WriteAuditLog'
    write['_value']['method']['_value'] = 'POST'
    write['_value']['path'] = expr('s"${"/apps/"}${context.appReferenceId()}${"/v1/comsAuditLogs"}"')
    tpl = ('{\n  "timestamp": "{{data.GetInputParams.timestamp}}", "runId": "{{data.GetInputParams.runId}}", '
           '"eventWid": "{{data.ExtractEvent.eventId}}",\n'
           '  "objectType": "Assignable Role",\n  "action": "REQUEST",\n'
           '  "coReferenceId": "{{data.ExtractRequest.roleName}}",\n  "coName": "{{data.AuditValues.coName}}",\n'
           '  "roleName": "{{data.ExtractRequest.roleName}}",\n  "positionName": "{{data.AuditValues.positions}}",\n'
           '  "positionWid": "{{data.AuditValues.positionWids}}",\n  "effectiveDate": "{{data.AuditValues.effectiveDate}}",\n'
           '  "triggeredBy": "{{data.AuditValues.requesterName}}",\n  "changedByWid": "{{data.AuditValues.requesterWid}}",\n'
           '  "details": "' + details + '"\n}')
    write['_value']['body']['_value']['_value']['message']['_value'] = tpl
    i = next(i for i, n in enumerate(nodes) if n['_value']['name']['_value'] == 'SaveEventOnRequest')
    nodes[i + 1:i + 1] = [vals, write]
    open(p, 'w', encoding='utf-8').write(json.dumps(d, separators=(',', ':'), ensure_ascii=False) + ('\n' if raw.endswith('\n') else ''))
    return 1


def drop_page_write(page):
    p = os.path.join(ROOT, 'presentation', page + '.pmd')
    d = json.load(open(p, encoding='utf-8'))
    eps = d['outboundData']['outboundEndPoints']
    keep = [e for e in eps if e['name'] != 'postAuditLog']
    if len(keep) == len(eps):
        return 0
    d['outboundData']['outboundEndPoints'] = keep
    open(p, 'w', encoding='utf-8').write(json.dumps(d, indent=2, ensure_ascii=False) + '\n')
    return 1


out = []
for flow, (page, details) in FLOWS.items():
    out.append(f"{flow} +{patch_flow(flow, details)}, {page} page write removed {drop_page_write(page)}")
print('request_audit: ' + '; '.join(out))
