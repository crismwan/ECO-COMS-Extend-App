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
import json, copy, hashlib, os, re, sys
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'orchestration')
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


def extract(sub_name, parents, block_name, sources, labels, call_name):
    """Move `block_name` (inside each parent) into sub_name; its reads of data.<src>.<field> for src in `sources`
    become inputs. `labels` maps parent -> sourceLabel text (the one wording that differs)."""
    sid = flow_id(sub_name)
    blocks, types = {}, {}
    for p in parents:
        d = load(p)
        blk = find(d, block_name)
        if blk is None:
            if find(d, call_name) is not None:
                print(f'   {p}: already calls {sub_name}'); continue
            sys.exit(f'{p}: no {block_name} step')
        for src in sources:
            for n, t in inputs_of(find(d, src)):
                if types.setdefault(n, t) != t: sys.exit(f'{p}: input {n} is {t} here, {types[n]} elsewhere')
        blocks[p] = (d, blk)
    if not blocks:
        return
    # the block, with the one differing wording replaced by an input
    norm = {}
    for p, (d, blk) in blocks.items():
        s = json.dumps(blk, sort_keys=True).replace(labels[p] + ' {{data.GetInputParams.ref}}', '{{data.GetInputParams.sourceLabel}} {{data.GetInputParams.ref}}')
        norm[p] = s
    if len(set(norm.values())) != 1:
        sys.exit(f'{block_name} differs between {list(norm)} beyond the audit wording; compare them before extracting')
    body = json.loads(next(iter(norm.values())))
    inner = set(re.findall(r'"name": \{"_type": "Identifier", "_value": "([^"]+)"', json.dumps(body)))
    src_re = re.compile(r'data\.(' + '|'.join(sources) + r')\.([A-Za-z_][A-Za-z0-9_]*)')
    used = sorted(set(m.group(2) for m in src_re.finditer(json.dumps(body))))
    types['sourceLabel'] = 'String'
    missing = [u for u in used if u not in types]
    if missing: sys.exit(f'{block_name} reads {missing}, which none of {sources} makes')
    other = sorted(set(re.findall(r'data\.([A-Za-z_]+)\.', json.dumps(body))) - inner - set(sources))
    if other: sys.exit(f'{block_name} also reads {other} from outside; pass them in first')
    body = json.loads(src_re.sub(lambda m: 'data.start.' + m.group(2), json.dumps(body)))

    first = next(iter(blocks.values()))[0]['_value']
    sub = {"flowVersion": next(iter(blocks.values()))[0]['flowVersion'], "_type": "Flow", "_value": {
        "id": S(sid), "name": I(sub_name), "type": {"_type": "FlowType", "_value": ".maya.FlowSubflow"},
        "start": {"_type": "StartSubflow", "_value": {
            "parameters": {"_type": ["List", "ExprParameter"], "_value": [
                {"_type": "ExprParameter", "_value": {"name": I(n), "type": TYPE(types[n]),
                                                      "expr": {"_type": ["Opt", ["Expr", ["Opt", "Any"]]], "_value": None}}} for n in used]},
            "notes": NOTES("One row's values plus the run's: " + ", ".join(used))}},
        "end": {"_type": "EndSubflow", "_value": {"exports": {"_type": ["List", "Assignment"], "_value": []},
                                                  "notes": NOTES("No outputs: the row's result and audit records are written here.")}},
        "nodes": {"_type": ["List", "Node"], "_value": [body]},
        "notes": NOTES(""),
        "resources": copy.deepcopy(first['resources']),
        "defaultWorkdayCredentialRef": copy.deepcopy(first['defaultWorkdayCredentialRef']),
        "defaultTlsConfigRef": copy.deepcopy(first['defaultTlsConfigRef']),
        "defaultFtpCredRef": copy.deepcopy(first['defaultFtpCredRef']),
        "mayaVersion": copy.deepcopy(first['mayaVersion']),
        "errorHandler": {"_type": ["Opt", "ErrorHandler"], "_value": None},
        "cancelBarrier": {"_type": ["Opt", "Identifier"], "_value": None},
        "defaultLocale": copy.deepcopy(first['defaultLocale']),
        "securityDomains": {"_type": ["Opt", ["List", "String"]], "_value": None}}}
    sub['_value']['notes'] = NOTES(f"Shared by {' and '.join(parents)}: {block_name} for one row. Built by tools/extract_subflows.py.")
    save(sub_name, sub, '.suborchestration')

    for p, (d, blk) in blocks.items():
        def arg(n):
            src = f'"{labels[p]}"' if n == 'sourceLabel' else next(f'data.{s}.{n}' for s in sources if n in dict(inputs_of(find(d, s))))
            return {"_type": "Assignment", "_value": {
                "param": {"_type": "Parameter", "_value": {"name": I(n), "type": TYPE(types[n]), "default": {"_type": ["Opt", "Any"], "_value": None}}},
                "expr": EXPR(src, types[n])}}
        call = {"_type": "CallSubflow", "_value": {
            "name": I(call_name), "isDisabled": B(False), "errorHandler": {"_type": ["Opt", "ErrorHandler"], "_value": None},
            "subflowId": S(sid), "parameters": {"_type": ["List", "Assignment"], "_value": [arg(n) for n in used]},
            "executionDelay": {"_type": ["Opt", "SubflowExecutionDelay"], "_value": None}}}
        def swap(n):
            if isinstance(n, list):
                for i, x in enumerate(n):
                    if x is blk: n[i] = call; return True
                    if swap(x): return True
            elif isinstance(n, dict):
                for x in n.values():
                    if swap(x): return True
            return False
        if not swap(d): sys.exit(f'{p}: could not replace {block_name}')
        save(p, d)
        print(f'   {p}: {block_name} -> {call_name} ({len(used)} inputs)')


extract('ProcessBulkRoleRow', ['BulkRoleApply', 'BulkRoleGridApply'], 'ActionBranch', ['GetInputParams', 'Row'],
        {'BulkRoleApply': 'Bulk upload', 'BulkRoleGridApply': 'Bulk edit'}, 'CallProcessRow')
