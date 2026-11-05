#!/usr/bin/env python3
"""Moves logic two orchestrations share into one sub-orchestration they both call (product owner 2026-11-04).
Runs LAST in rebuild_all.sh, after every builder and patcher has written the parents in full.

How a sub-orchestration works (confirmed against App Hub builds 2026-11-04, see CLAUDE.md "Sub-orchestrations"):
  - the file is orchestration/<Name>.suborchestration, flow type .maya.FlowSubflow; nothing else registers it
  - StartSubflow lists typed inputs (ExprParameter), read inside as data.start.<input>
  - the caller's step is CallSubflow; its subflowId is the sub-orchestration's 32-hex `id`, not its name

ProcessBulkRoleRow: BulkRoleApply and BulkRoleGridApply each loop over rows as `Row` (CSV vs grid JSON) then
`ActionBranch` (look up position, check, Assign_Roles, result record, audit record). ActionBranch is identical in both
apart from the audit wording, so it moves into the sub-orchestration with every value it reads passed in, and each
loop becomes Row -> CallProcessRow. Idempotent: a parent that already calls the sub is left alone."""
import json, copy, glob, hashlib, os, re, shutil, sys
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'orchestration')
# Full (un-extracted) copies of the parents. Earlier build steps patch the parents in place by step name, so
# `--restore` (first in rebuild_all.sh) puts these back before they run; this script extracts again at the end.
SRC = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'subflow_src')
if '--restore' in sys.argv:
    for f in sorted(glob.glob(os.path.join(SRC, '*.orchestration'))):
        shutil.copyfile(f, os.path.join(ROOT, os.path.basename(f)))
        print('   restored', os.path.basename(f))
    sys.exit(0)
S = lambda v: {"_type": "String", "_value": v}
I = lambda v: {"_type": "Identifier", "_value": v}
B = lambda v: {"_type": "Boolean", "_value": v}
TYPE = lambda t: {"_type": "Type", "_value": t}
def EXPR(src, t):
    return {"_type": ["Expr", t], "_value": {"type": TYPE(t), "source": S(src), "isAuto": B(False)}}
def NOTES(text):
    return {"_type": ["List", "Note"], "_value": [{"_type": "Note", "_value": {"key": S("description"), "value": S(text)}}]}
def flow_id(name):
    return hashlib.md5(('eco-coms-subflow:' + name).encode()).hexdigest()

def load(name, ext='.orchestration'):
    return json.load(open(os.path.join(ROOT, name + ext)))
def save(name, d, ext='.orchestration'):
    open(os.path.join(ROOT, name + ext), 'w').write(json.dumps(d, separators=(',', ':')))

def find(n, nm):
    if isinstance(n, dict):
        v = n.get('_value')
        if isinstance(v, dict) and isinstance(v.get('name'), dict) and v['name'].get('_value') == nm:
            return n
        for x in n.values():
            r = find(x, nm)
            if r is not None: return r
    elif isinstance(n, list):
        for x in n:
            r = find(x, nm)
            if r is not None: return r
    return None

def inputs_of(node):
    """(name, type) of each value a CreateValues node makes."""
    return [(a['_value']['param']['_value']['name']['_value'], a['_value']['param']['_value']['type']['_value'])
            for a in node['_value']['values']['_value']]


def map_strings(n, fn):
    """Apply fn to every string value in a JSON tree (in place)."""
    if isinstance(n, dict):
        for k, v in n.items():
            if isinstance(v, str): n[k] = fn(v)
            else: map_strings(v, fn)
    elif isinstance(n, list):
        for i, v in enumerate(n):
            if isinstance(v, str): n[i] = fn(v)
            else: map_strings(v, fn)


def extract(sub_name, parents, steps, sources, call_name, norm=None, args=None, notes=None):
    """Move the consecutive `steps` (a list of step names, inside each parent) into sub_name.
    norm:  {parent: [(old, new), ...]} text replacements in the block's strings, so the parents' copies become identical
           (the differing wording turns into data.<source>.<input> references);
    args:  {parent: {input: expression}} what the parent passes for inputs that aren't plain data.<source>.<input>
           values of its own (renamed or constant ones);
    notes: (flow, start, end) descriptions for the sub-orchestration.
    Everything the block reads as data.<source>.<field> becomes an input of the same name."""
    norm, args = norm or {}, args or {}
    sid = flow_id(sub_name)
    blocks = {}
    for p in parents:
        d = load(p)
        nodes = [find(d, n) for n in steps]
        if any(n is None for n in nodes):
            if find(d, call_name) is not None:
                print(f'   {p}: already calls {sub_name}'); continue
            sys.exit(f'{p}: missing one of {steps}')
        os.makedirs(SRC, exist_ok=True)
        open(os.path.join(SRC, p + '.orchestration'), 'w').write(json.dumps(d, separators=(',', ':')))
        blk = copy.deepcopy(nodes)
        for old, new in norm.get(p, []):
            map_strings(blk, lambda v, o=old, n=new: v.replace(o, n))
        blocks[p] = (d, nodes, json.dumps(blk, sort_keys=True))
    if not blocks:
        return
    if len(set(b[2] for b in blocks.values())) != 1:
        import difflib
        (pa, a), (pb, b) = [(k, v[2]) for k, v in list(blocks.items())[:2]]
        diff = [l for l in difflib.unified_diff(json.dumps(json.loads(a), indent=0, sort_keys=True).splitlines(),
                json.dumps(json.loads(b), indent=0, sort_keys=True).splitlines(), lineterm='', n=0) if l[:1] in '+-'][2:12]
        sys.exit(f'{steps} still differ between {pa} and {pb} after normalizing:\n' + '\n'.join(diff))
    body_text = next(iter(blocks.values()))[2]
    inner = set(re.findall(r'"name": \{"_type": "Identifier", "_value": "([^"]+)"', body_text))
    src_re = re.compile(r'data\.(' + '|'.join(sources) + r')\.([A-Za-z_][A-Za-z0-9_]*)')
    pairs = sorted(set((m.group(1), m.group(2)) for m in src_re.finditer(body_text)))
    used = sorted(set(f for _, f in pairs))
    clash = [f for f in used if len([1 for s_, f_ in pairs if f_ == f]) > 1]
    if clash: sys.exit(f'{steps}: {clash} read from more than one of {sources}; rename one first')
    src_of = {f: s_ for s_, f in pairs}
    other = sorted(set(re.findall(r'data\.([A-Za-z_]+)\.', body_text)) - inner - set(sources))
    if other: sys.exit(f'{steps} also read {other} from outside; pass them in first')
    types = {}
    for p, (d, _, _) in blocks.items():
        for f in used:
            node = find(d, src_of[f])
            t = dict(inputs_of(node)).get(f) if node is not None and f not in args.get(p, {}) else None
            if t and types.setdefault(f, t) != t: sys.exit(f'{p}: input {f} is {t} here, {types[f]} elsewhere')
    for p in blocks:
        for f, v in args.get(p, {}).items():
            if isinstance(v, tuple) and types.setdefault(f, v[1]) != v[1]: sys.exit(f'{p}: input {f} is {v[1]} here, {types[f]} elsewhere')
    for f in used: types.setdefault(f, 'String')
    body = json.loads(src_re.sub(lambda m: 'data.start.' + m.group(2), body_text))

    first = next(iter(blocks.values()))[0]['_value']
    flow_note, start_note, end_note = notes
    sub = {"flowVersion": next(iter(blocks.values()))[0]['flowVersion'], "_type": "Flow", "_value": {
        "id": S(sid), "name": I(sub_name), "type": {"_type": "FlowType", "_value": ".maya.FlowSubflow"},
        "start": {"_type": "StartSubflow", "_value": {
            "parameters": {"_type": ["List", "ExprParameter"], "_value": [
                {"_type": "ExprParameter", "_value": {"name": I(n), "type": TYPE(types[n]),
                                                      "expr": {"_type": ["Opt", ["Expr", ["Opt", "Any"]]], "_value": None}}} for n in used]},
            "notes": NOTES(start_note + ", ".join(used))}},
        "end": {"_type": "EndSubflow", "_value": {"exports": {"_type": ["List", "Assignment"], "_value": []},
                                                  "notes": NOTES(end_note)}},
        "nodes": {"_type": ["List", "Node"], "_value": body},
        "notes": NOTES(flow_note),
        "resources": copy.deepcopy(first['resources']),
        "defaultWorkdayCredentialRef": copy.deepcopy(first['defaultWorkdayCredentialRef']),
        "defaultTlsConfigRef": copy.deepcopy(first['defaultTlsConfigRef']),
        "defaultFtpCredRef": copy.deepcopy(first['defaultFtpCredRef']),
        "mayaVersion": copy.deepcopy(first['mayaVersion']),
        "errorHandler": {"_type": ["Opt", "ErrorHandler"], "_value": None},
        "cancelBarrier": {"_type": ["Opt", "Identifier"], "_value": None},
        "defaultLocale": copy.deepcopy(first['defaultLocale']),
        "securityDomains": {"_type": ["Opt", ["List", "String"]], "_value": None}}}
    save(sub_name, sub, '.suborchestration')

    for p, (d, nodes, _) in blocks.items():
        def arg(n):
            v = args.get(p, {}).get(n)
            src = (v[0] if isinstance(v, tuple) else v) or f'data.{src_of[n]}.{n}'
            return {"_type": "Assignment", "_value": {
                "param": {"_type": "Parameter", "_value": {"name": I(n), "type": TYPE(types[n]), "default": {"_type": ["Opt", "Any"], "_value": None}}},
                "expr": EXPR(src, types[n])}}
        for n in used:
            if n not in args.get(p, {}):
                node = find(d, src_of[n])
                if node is None or n not in dict(inputs_of(node)): sys.exit(f'{p}: input {n} has no value; add it to args')
        call = {"_type": "CallSubflow", "_value": {
            "name": I(call_name), "isDisabled": B(False), "errorHandler": {"_type": ["Opt", "ErrorHandler"], "_value": None},
            "subflowId": S(sid), "parameters": {"_type": ["List", "Assignment"], "_value": [arg(n) for n in used]},
            "executionDelay": {"_type": ["Opt", "SubflowExecutionDelay"], "_value": None}}}
        def swap(n):
            if isinstance(n, list):
                for i, x in enumerate(n):
                    if x is nodes[0]:
                        n[i] = call
                        n[:] = [y for y in n if not any(y is z for z in nodes[1:])]
                        return True
                    if swap(x): return True
            elif isinstance(n, dict):
                for x in n.values():
                    if swap(x): return True
            return False
        if not swap(d): sys.exit(f'{p}: could not replace {steps}')
        save(p, d)
        print(f'   {p}: {" + ".join(steps)} -> {call_name} ({len(used)} inputs)')


# Bulk pair: the per-row work (look up position, check, Assign_Roles, result record, audit record).
extract('ProcessBulkRoleRow', ['BulkRoleApply', 'BulkRoleGridApply'], ['ActionBranch'], ['GetInputParams', 'Row'], 'CallProcessRow',
        norm={'BulkRoleApply': [('Bulk upload {{data.GetInputParams.ref}}', '{{data.GetInputParams.sourceLabel}} {{data.GetInputParams.ref}}')],
              'BulkRoleGridApply': [('Bulk edit {{data.GetInputParams.ref}}', '{{data.GetInputParams.sourceLabel}} {{data.GetInputParams.ref}}')]},
        args={'BulkRoleApply': {'sourceLabel': '"Bulk upload"'}, 'BulkRoleGridApply': {'sourceLabel': '"Bulk edit"'}},
        notes=("Shared by BulkRoleApply and BulkRoleGridApply: ActionBranch for one row. Built by tools/extract_subflows.py.",
               "One row's values plus the run's: ", "No outputs: the row's result and audit records are written here."))

# Shell org pair: the Workday add-organization call, the "was it accepted" check, and the result branch (log + audit record).
# Each parent keeps its own inputs, application lookup and (for patterns) the name check before the call.
SHELL_NORM = [
    ('Call Workday Add_Update_Organization WWS to create the Custom Organization shell org pattern in Workday',
     'Call Workday Add_Update_Organization WWS to create the Shell Organization in Workday'),
]
extract('CreateShellOrganization', ['AddShellOrg', 'AddShellOrgPattern'],
        ['CallAddUpdateOrganization', 'CheckWWSAccepted', 'CheckWWSResult'], ['GetInputParams', 'ExtractOrgType'], 'CallCreateShellOrg',
        norm={
          'AddShellOrg': SHELL_NORM + [
            ('data.GetInputParams.organizationName', 'data.GetInputParams.orgName'),
            ('{{data.GetInputParams.organizationCode}}', '{{data.GetInputParams.orgCode}}'),
            ('"objectType": "Shell Org",', '"objectType": "{{data.GetInputParams.objectType}}",'),
            ('"details": "Shell org {{', '"details": "{{data.GetInputParams.objectLabel}} {{'),
            ('"Shell Org created successfully in Workday: "', 'data.GetInputParams.objectType + " created successfully in Workday: "'),
            ('"Add_Update_Organization WWS call failed for org: "', '"Add_Update_Organization WWS call failed for " + data.GetInputParams.objectLabel + ": "'),
          ],
          'AddShellOrgPattern': SHELL_NORM + [
            ('"coReferenceId": "{{data.GetInputParams.patternName}}"', '"coReferenceId": "{{data.GetInputParams.orgCode}}"'),
            ('data.GetInputParams.patternName', 'data.GetInputParams.orgName'),
            ('X:SHELL</bsvc:Organization_Subtype_Name>', '{{data.GetInputParams.orgSubtype}}</bsvc:Organization_Subtype_Name>'),
            ('"objectType": "Shell Org Pattern",', '"objectType": "{{data.GetInputParams.objectType}}",'),
            ('"details": "Shell org pattern {{', '"details": "{{data.GetInputParams.objectLabel}} {{'),
            ('"Shell Org Pattern created successfully in Workday: "', 'data.GetInputParams.objectType + " created successfully in Workday: "'),
            ('"Add_Update_Organization WWS call failed for pattern: "', '"Add_Update_Organization WWS call failed for " + data.GetInputParams.objectLabel + ": "'),
          ]},
        args={
          'AddShellOrg': {'orgName': 'data.GetInputParams.organizationName', 'orgCode': 'data.GetInputParams.organizationCode',
                          'objectType': '"Shell Org"', 'objectLabel': '"Shell org"'},
          'AddShellOrgPattern': {'orgName': 'data.GetInputParams.patternName', 'orgCode': 'data.GetInputParams.patternName',
                                 'orgSubtype': '"X:SHELL"', 'objectType': '"Shell Org Pattern"', 'objectLabel': '"Shell org pattern"'}},
        notes=("Shared by AddShellOrg and AddShellOrgPattern: create the organization in Workday (Organization_Add_Update), "
               "stop if Workday rejects it, then log and write the audit record. Built by tools/extract_subflows.py.",
               "The organization to create and the audit wording: ", "No outputs: the audit record is written here."))

# Review-start pair: two copies only because an orchestration takes one security domain (each parent keeps its own).
# Everything after GetInputParams: find the request, start the review event, save the event on the request, audit, log.
REVIEW_DETAILS = ('"details": "{{data.GetInputParams.requestLabel}} request submitted: {{data.ExtractRequest.roleName}}'
                  '{{#if data.GetInputParams.showOrg}} for org {{data.AuditValues.coName}}{{/if}}'
                  '{{#if data.GetInputParams.showEffective}} effective {{data.AuditValues.effectiveDate}}{{/if}}"')
extract('StartRequestReview', ['StartRoleRequestReview', 'StartAAARequestReview'],
        ['FindRequest', 'ExtractRequest', 'StartReview', 'ExtractEvent', 'SaveEventOnRequest', 'AuditValues', 'WriteAuditLog', 'LogStarted'],
        ['GetInputParams'], 'CallStartReview',
        norm={'StartRoleRequestReview': [('"details": "Assignable role request submitted: {{data.ExtractRequest.roleName}} for org {{data.AuditValues.coName}}"', REVIEW_DETAILS)],
              'StartAAARequestReview': [('"details": "AAA role request submitted: {{data.ExtractRequest.roleName}} effective {{data.AuditValues.effectiveDate}}"', REVIEW_DETAILS)]},
        args={'StartRoleRequestReview': {'requestLabel': '"Assignable role"', 'showOrg': ('true', 'Boolean'), 'showEffective': ('false', 'Boolean')},
              'StartAAARequestReview': {'requestLabel': '"AAA role"', 'showOrg': ('false', 'Boolean'), 'showEffective': ('true', 'Boolean')}},
        notes=("Shared by StartRoleRequestReview and StartAAARequestReview (two copies only for their different security domains): "
               "start the review event for one request, save it on the request, write the REQUEST audit record. Built by tools/extract_subflows.py.",
               "The request and the audit wording: ", "No outputs: the event is saved on the request and the audit record is written here."))
