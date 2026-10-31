#!/usr/bin/env python3
"""Builds orchestration/BulkRoleApply.orchestration by cloning node prototypes from the
orchestrations already in this repo (CLAUDE.md: don't hand-type orchestration JSON).
Re-run after editing this script: python3 tools/build_bulk_orchestration.py"""
import json, copy, os
ROOT = os.path.join(os.path.dirname(__file__), '..')
O = lambda n: json.load(open(os.path.join(ROOT, 'orchestration', n + '.orchestration')))
arp, deny = O('AssignRolePositions'), O('DenyRoleRequest')
def node(src, name):
    return copy.deepcopy([n for n in src['_value']['nodes']['_value'] if n['_value']['name']['_value'] == name][0])
def rename(n, name):
    n['_value']['name']['_value'] = name
    if 'notes' in n['_value']: n['_value']['notes']['_value'] = []
    return n
def S(s):  # a String expression
    return {"_type": ["Expr", "String"], "_value": {"type": {"_type": "Type", "_value": "String"}, "source": {"_type": "String", "_value": s}, "isAuto": {"_type": "Boolean", "_value": False}}}
def B(s):
    return {"_type": ["Expr", "Boolean"], "_value": {"type": {"_type": "Type", "_value": "Boolean"}, "source": {"_type": "String", "_value": s}, "isAuto": {"_type": "Boolean", "_value": False}}}

CV = node(arp, 'GetInputParams')
def create_values(name, pairs):  # pairs: (name, type 'String'|'Boolean', source)
    n = rename(copy.deepcopy(CV), name)
    proto = n['_value']['values']['_value'][0]
    out = []
    for pname, typ, src in pairs:
        a = copy.deepcopy(proto)
        a['_value']['param']['_value']['name']['_value'] = pname
        a['_value']['param']['_value']['type']['_value'] = typ
        a['_value']['expr'] = S(src) if typ == 'String' else B(src)
        out.append(a)
    n['_value']['values']['_value'] = out
    return n

GET = node(deny, 'GetRequest')
def get(name, path, response_type='Json'):
    n = rename(copy.deepcopy(GET), name)
    n['_value']['path'] = S(path)
    n['_value']['responseType']['_value'] = response_type
    return n

TPL = node(deny, 'MarkDenied')  # PATCH with a JSON text template
def send(name, method, path, template):
    n = rename(copy.deepcopy(TPL), name)
    n['_value']['method']['_value'] = method
    n['_value']['path'] = S(path)
    n['_value']['body']['_value']['_value']['message']['_value'] = template
    return n

COC = node(arp, 'CheckMode')
def continue_on(name, checks):
    n = rename(copy.deepcopy(COC), name)
    proto = n['_value']['assertions']['_value'][0]
    out = []
    for cond, msg in checks:
        a = copy.deepcopy(proto)
        a['_value']['assertion'] = B(cond); a['_value']['message'] = S(msg)
        out.append(a)
    n['_value']['assertions']['_value'] = out
    return n

BR = node(arp, 'CheckWWSResult')
def branch(name, cases, else_nodes=()):
    """cases: list of (branchName, condition, nodes); the first true condition runs."""
    n = rename(copy.deepcopy(BR), name)
    proto = n['_value']['ifBranches']['_value'][0]
    out = []
    for bname, cond, nodes in cases:
        w = copy.deepcopy(proto)
        w['_value']['name']['_value'] = bname
        w['_value']['condition'] = B(cond)
        w['_value']['group']['_value']['name']['_value'] = '_group_' + bname + '_' + name
        w['_value']['group']['_value']['nodes']['_value'] = list(nodes)
        out.append(w)
    n['_value']['ifBranches']['_value'] = out
    n['_value']['elseBranch']['_value']['name']['_value'] = '_else_' + name
    n['_value']['elseBranch']['_value']['nodes']['_value'] = list(else_nodes)
    return n

LOG = node(arp, 'LogWWSResponse')
def log(name, msg):
    n = rename(copy.deepcopy(LOG), name); n['_value']['message'] = S(msg); return n

SOAP = node(arp, 'CallOrganizationUpdate')
LOOP = {"_type": "Loop", "_value": {"name": {"_type": "Identifier", "_value": "ProcessRows"}, "isDisabled": {"_type": "Boolean", "_value": False}, "errorHandler": {"_type": ["Opt", "ErrorHandler"], "_value": None},
  "inputData": {"_type": ["Expr", ["Iterator", ["Opt", "Any"]]], "_value": {"type": {"_type": "Type", "_value": ["Iterator", ["CsvRow", {"_type": ["Opt", "CsvFormatRef"], "_value": None}]]}, "source": {"_type": "String", "_value": "data.GetFile.response.asCSV().rows()"}, "isAuto": {"_type": "Boolean", "_value": False}}},
  "filter": {"_type": ["Opt", ["Expr", "Boolean"]], "_value": None}, "aggregateNode": {"_type": ["Opt", "Aggregate"], "_value": None},
  "earlyStopCondition": {"_type": ["Opt", "EarlyStopCondition"], "_value": None}, "sorts": {"_type": ["List", "SortedBy"], "_value": []},
  "locale": {"_type": ["Opt", "Locale"], "_value": None},
  "group": {"_type": "ImplicitGroup", "_value": {"name": {"_type": "Identifier", "_value": "_group_ProcessRows"}, "isDisabled": {"_type": "Boolean", "_value": False}, "errorHandler": {"_type": ["Opt", "ErrorHandler"], "_value": None}, "nodes": {"_type": ["List", "Node"], "_value": []}, "notes": {"_type": ["List", "Note"], "_value": []}}},
  "notes": {"_type": ["List", "Note"], "_value": []}}}

APP = 's"${"/apps/"}${context.appReferenceId()}${"/v1/'
q = lambda p: 'data("start", "queryParams").getParam("%s", "")' % p
clean = lambda e: e + '.normalizeSpace().replace("\\\\", "/").replace("\\"", "\'")'
col = lambda i: 'data.ProcessRows.item.columnValueAtIndex(%d).trim()' % i

nodes = []
nodes.append(create_values('GetInputParams', [
    ('ref', 'String', q('ref')), ('mode', 'String', q('mode')), ('effectiveDate', 'String', q('effectiveDate')),
    ('changedBy', 'String', clean(q('changedBy'))), ('changedByWid', 'String', q('changedByWid')),
    ('isApply', 'Boolean', 'data("start", "queryParams").getParam("mode", "").equals("APPLY")'),
    ('timestamp', 'String', 'datetime.now("UTC").format("yyyy-MM-dd\'T\'HH:mm:ss\'Z\'")'),
]))
nodes.append(continue_on('CheckInputs', [
    ('data.GetInputParams.mode.equals("APPLY").or(data.GetInputParams.mode.equals("VALIDATE"))', '"mode must be VALIDATE or APPLY, got " + data.GetInputParams.mode'),
    ('data.GetInputParams.ref.isEmpty().not()', '"ref (the upload batch reference) is required"'),
    ('data.GetInputParams.effectiveDate.isEmpty().not()', '"effectiveDate is required"'),
]))
nodes.append(get('FindUpload', APP + 'comsBulkUploads?limit=100&batchRef="}${data.GetInputParams.ref}"'))
nodes.append(create_values('ExtractUpload', [
    ('uploadId', 'String', 'data.FindUpload.response.asJSON().stringAtJsonPathWithDefault("$.data[0].id", "")'),
    ('uploadRef', 'String', 'data.FindUpload.response.asJSON().stringAtJsonPathWithDefault("$.data[0].batchRef", "")'),
]))
nodes.append(continue_on('CheckUpload', [
    ('data.ExtractUpload.uploadRef.equals(data.GetInputParams.ref)', '"no upload found with batch reference " + data.GetInputParams.ref + " (found " + data.ExtractUpload.uploadRef + ")"'),
]))
nodes.append(send('MarkRunning', 'PATCH', APP + 'comsBulkUploads/"}${data.ExtractUpload.uploadId}"',
    '{\n  "status": "Running",\n  "runMode": "{{data.GetInputParams.mode}}",\n  "statusMessage": "Processing started {{data.GetInputParams.timestamp}}"\n}'))
nodes.append(get('GetFile', APP + 'comsBulkUploads/"}${data.ExtractUpload.uploadId}"', 'Any'))
nodes.append(create_values('FileInfo', [
    ('tooMany', 'Boolean', 'data.GetFile.response.asCSV().countRows() > 201'),
]))

# ── per-row work ──
row = create_values('Row', [
    ('rowAction', 'String', col(0) + '.upperCase()'),
    ('roleName', 'String', clean(col(1))), ('roleWid', 'String', clean(col(2))),
    ('orgName', 'String', clean(col(3))), ('orgWid', 'String', clean(col(4))),
    ('positionName', 'String', clean(col(5))), ('positionId', 'String', clean(col(6))),
    ('assigneeWid', 'String', clean(col(7))),
    ('isAdd', 'Boolean', 'data.Row.rowAction.equals("ADD")'),
    ('isRemove', 'Boolean', 'data.Row.rowAction.equals("REMOVE")'),
    ('isAction', 'Boolean', 'data.Row.isAdd.or(data.Row.isRemove)'),
    ('complete', 'Boolean', 'data.Row.roleWid.isEmpty().or(data.Row.orgWid.isEmpty()).or(if (data.Row.isAdd) data.Row.positionId.isEmpty() else data.Row.assigneeWid.isEmpty()).not()'),
    ('idType', 'String', 'if (data.Row.isAdd) "Position_ID" else "WID"'),
    ('idValue', 'String', '(if (data.Row.isAdd) data.Row.positionId else data.Row.assigneeWid).escapeXml()'),
    # same WQL the single-change page uses (posWidLookup); quotes stripped so the cell can't change the query
    ('wql', 'String', '"SELECT workdayID, cf_PositionID, cf_PositionIsFilled FROM allPositions WHERE cf_PositionID = \'".append(data.Row.positionId.replace("\'", "")).append("\'")'),
])
lookup = get('LookupPosition', 's"${"/wql/v1/data?limit=1&query="}${data.Row.wql.urlEncode().replace("+", "%20")}"')
check = create_values('Check', [
    ('found', 'Boolean', 'data.LookupPosition.response.asJSON().stringAtJsonPathWithDefault("$.data[0].workdayID", "").isEmpty().not()'),
    ('unfilled', 'Boolean', 'data.LookupPosition.response.toString().replace(" ", "").contains("\\"cf_PositionIsFilled\\":false")'),
    ('isValid', 'Boolean', 'if (data.Row.complete) (if (data.Row.isAdd) data.Check.found else true) else false'),
    ('doApply', 'Boolean', 'if (data.Check.isValid) data.GetInputParams.isApply else false'),
    ('doCheck', 'Boolean', 'data.Check.doApply.not()'),
    ('checkResult', 'String', 'if (data.Check.isValid) "VALID" else "INVALID"'),
    ('checkMessage', 'String', 'if (data.Row.complete.not()) (if (data.Row.isAdd) "Missing Role WID, Organization WID or Position ID." else "Missing Role WID, Organization WID or Assignee WID.") else (if (data.Check.isValid) (if (data.Check.unfilled) "Row is complete; not applied (validation run). Note: the position is unfilled, and Workday may reject it." else "Row is complete; not applied (validation run).") else "Position ID ".append(data.Row.positionId).append(" was not found in Workday."))'),
])
soap = rename(copy.deepcopy(SOAP), 'CallAssignRoles')
tpl = soap['_value']['body']['_value']['_value']['message']['_value']
tpl = (tpl.replace('{{data.GetInputParams.effectiveDate}}', '{{data.GetInputParams.effectiveDate}}')
          .replace('{{data.GetInputParams.positionIdType}}', '{{data.Row.idType}}')
          .replace('{{data.GetInputParams.positionId}}', '{{data.Row.idValue}}')
          .replace('{{data.GetInputParams.orgId}}', '{{data.Row.orgWid}}')
          .replace('{{data.GetInputParams.roleId}}', '{{data.Row.roleWid}}')
          .replace('{{#if data.ExtractMode.isAdd}}', '{{#if data.Row.isAdd}}')
          .replace('{{#if data.ExtractMode.isRemove}}', '{{#if data.Row.isRemove}}'))
assert 'GetInputParams.position' not in tpl and 'ExtractMode' not in tpl, tpl
soap['_value']['body']['_value']['_value']['message']['_value'] = tpl
OK = 'data.CallAssignRoles.responseStatusCode.is2xxStatusCode().not().or(data.CallAssignRoles.response.isSoapFault()).not()'
outcome = create_values('Outcome', [
    ('ok', 'Boolean', OK),
    ('failed', 'Boolean', 'data.Outcome.ok.not()'),
    ('fault', 'String', '(if (data.Outcome.ok) "" else data.CallAssignRoles.response.toString().substringAfter("faultstring>").substringBefore("<")).normalizeSpace().replace("\\"", "\'").truncate(500)'),
])
RESULT = ('{\n  "batchRef": "{{data.GetInputParams.ref}}",\n  "runMode": "{{data.GetInputParams.mode}}",\n  "rowAction": "{{data.Row.rowAction}}",\n'
          '  "roleName": "{{data.Row.roleName}}",\n  "roleWid": "{{data.Row.roleWid}}",\n  "orgName": "{{data.Row.orgName}}",\n  "orgWid": "{{data.Row.orgWid}}",\n'
          '  "positionName": "{{data.Row.positionName}}",\n  "positionId": "{{data.Row.positionId}}",\n  "assigneeWid": "{{data.Row.assigneeWid}}",\n'
          '  "timestamp": "{{data.GetInputParams.timestamp}}",\n  RESULT_FIELDS\n}')
applied = send('WriteAppliedResult', 'POST', APP + 'comsBulkRowResults"}"',
    RESULT.replace('RESULT_FIELDS', '"result": "{{#if data.Outcome.ok}}DONE{{/if}}{{#if data.Outcome.failed}}FAILED{{/if}}",\n  "message": "{{#if data.Outcome.ok}}Applied in Workday.{{/if}}{{#if data.Outcome.failed}}Workday rejected the change: {{data.Outcome.fault}}{{/if}}"'))
checked = send('WriteCheckResult', 'POST', APP + 'comsBulkRowResults"}"',
    RESULT.replace('RESULT_FIELDS', '"result": "{{data.Check.checkResult}}",\n  "message": "{{data.Check.checkMessage}}"'))
audit = rename(node(deny, 'WriteAuditLog'), 'WriteAuditLog')
audit['_value']['body']['_value']['_value']['message']['_value'] = (
    '{\n  "timestamp": "{{data.GetInputParams.timestamp}}",\n  "objectType": "Role Assignment",\n'
    '  "action": "{{#if data.Row.isAdd}}ASSIGN POSITION{{/if}}{{#if data.Row.isRemove}}REMOVE POSITION{{/if}}",\n'
    '  "coReferenceId": "{{data.Row.positionId}}",\n  "coName": "{{data.Row.orgName}}",\n  "roleName": "{{data.Row.roleName}}",\n'
    '  "positionName": "{{data.Row.positionName}}",\n  "effectiveDate": "{{data.GetInputParams.effectiveDate}}",\n'
    '  "changedByWid": "{{data.GetInputParams.changedByWid}}",\n  "orgWid": "{{data.Row.orgWid}}",\n  "roleWid": "{{data.Row.roleWid}}",\n'
    '  "positionWid": "{{#if data.Row.isRemove}}{{data.Row.assigneeWid}}{{/if}}",\n  "triggeredBy": "{{data.GetInputParams.changedBy}}",\n'
    '  "details": "Bulk upload {{data.GetInputParams.ref}}: {{#if data.Row.isAdd}}assigned{{/if}}{{#if data.Row.isRemove}}removed{{/if}} position {{data.Row.positionName}} on role {{data.Row.roleName}}"\n}')
row_branch = branch('RowBranch', [
    ('IF_Apply', 'data.Check.doApply', [soap, outcome, applied, branch('AuditBranch', [('IF_Done', 'data.Outcome.ok', [audit])])]),
    ('IF_Check', 'data.Check.doCheck', [checked]),
])
action_branch = branch('ActionBranch', [('IF_Action', 'data.Row.isAction', [lookup, check, row_branch])])
loop = copy.deepcopy(LOOP)
loop['_value']['group']['_value']['nodes']['_value'] = [row, action_branch]

finish = send('MarkFinished', 'PATCH', APP + 'comsBulkUploads/"}${data.ExtractUpload.uploadId}"',
    '{\n  "status": "{{#if data.GetInputParams.isApply}}Completed{{/if}}{{#if data.FileInfo.notApply}}Validated{{/if}}",\n'
    '  "finishedAt": "{{data.GetInputParams.timestamp}}",\n  "statusMessage": "Finished. See the row results."\n}')
reject = send('MarkTooMany', 'PATCH', APP + 'comsBulkUploads/"}${data.ExtractUpload.uploadId}"',
    '{\n  "status": "Rejected",\n  "statusMessage": "The file has more than 200 rows. Split it and upload again."\n}')
nodes[-1]['_value']['values']['_value'].append(create_values('tmp', [('notApply', 'Boolean', 'data.GetInputParams.isApply.not()')])['_value']['values']['_value'][0])
nodes.append(branch('SizeBranch', [('IF_TooMany', 'data.FileInfo.tooMany', [reject])], [loop, finish]))
nodes.append(log('LogDone', '"Bulk upload " + data.GetInputParams.ref + " (" + data.GetInputParams.mode + ") finished"'))

flow = json.load(open(os.path.join(ROOT, 'tools', 'orchestration_async_skeleton.json')))
v = flow['_value']
v['id']['_value'] = 'bulkroleapply001'
v['name']['_value'] = 'BulkRoleApply'
v['nodes']['_value'] = nodes
v['securityDomains'] = {"_type": ["Opt", ["List", "String"]], "_value": {"_type": ["List", "String"], "_value": [{"_type": "String", "_value": "ManageCOMSShellOrgs"}]}}
v['notes']['_value'] = [{"_type": "Note", "_value": {"key": {"_type": "String", "_value": "description"}, "value": {"_type": "String", "_value": "Bulk role changes from an uploaded CSV (COMSBulkUpload). Asynchronous: the launch returns at once. mode=VALIDATE checks every row and records VALID/INVALID; mode=APPLY calls Assign_Roles per valid row, records DONE/FAILED and writes an audit record per change. Built by tools/build_bulk_orchestration.py."}}}]
open(os.path.join(ROOT, 'orchestration', 'BulkRoleApply.orchestration'), 'w').write(json.dumps(flow, separators=(',', ':'), ensure_ascii=False))
print('nodes:', [n['_value']['name']['_value'] for n in nodes])
