#!/usr/bin/env python3
"""Every audit record an orchestration writes carries that run's ID (field runId).

context.orchestrateId() (developer.workday.com "Reference: Context Global Functions") is the
orchestration instance ID. Stored as text it lets an admin find the run on developer.workday.com
(app > Orchestration Activity / Logs) from the Audit Log.

For each orchestration that POSTs to comsAuditLogs: add `runId = context.orchestrateId()` to the
GetInputParams CreateValues node (cloned from its first assignment), and put
"runId": "{{data.GetInputParams.runId}}" right after "timestamp" in the audit text template.
Files stay single-line JSON (CLAUDE.md "Orchestrations — debugging").
"""
import copy, glob, json, os

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
TS = '"timestamp": "{{data.GetInputParams.timestamp}}",'
RUN = '"runId": "{{data.GetInputParams.runId}}",'


def nodes(n):
    if isinstance(n, dict):
        yield n
        for v in n.values():
            yield from nodes(v)
    elif isinstance(n, list):
        for v in n:
            yield from nodes(v)


def patch(path):
    raw = open(path, encoding='utf-8').read()
    if 'comsAuditLogs' not in raw:
        return None
    d = json.loads(raw)
    added_param = added_tpl = 0
    for n in nodes(d):
        v = n.get('_value')
        if n.get('_type') == 'CreateValues' and isinstance(v, dict) and v.get('name', {}).get('_value') == 'GetInputParams':
            vals = v['values']['_value']
            if not any(a['_value']['param']['_value']['name']['_value'] == 'runId' for a in vals):
                a = copy.deepcopy(vals[0])
                a['_value']['param']['_value']['name']['_value'] = 'runId'
                a['_value']['param']['_value']['type']['_value'] = 'String'
                a['_value']['expr'] = {"_type": ["Expr", "String"], "_value": {
                    "type": {"_type": "Type", "_value": "String"},
                    "source": {"_type": "String", "_value": "context.orchestrateId()"},
                    "isAuto": {"_type": "Boolean", "_value": False}}}
                vals.append(a)
                added_param += 1
        if n.get('_type') == 'TextTemplate' and isinstance(v, str) and '"objectType"' in v and TS in v and RUN not in v:
            n['_value'] = v.replace(TS, TS + ' ' + RUN, 1)
            added_tpl += 1
    if RUN not in json.dumps(d, ensure_ascii=False) and RUN.replace('"', '\\"') not in json.dumps(d):
        raise SystemExit(f"audit_run_id: no audit template with {TS} in {os.path.basename(path)}")
    new = json.dumps(d, separators=(',', ':'), ensure_ascii=False)
    if new != raw.rstrip('\n') and (added_param or added_tpl):
        open(path, 'w', encoding='utf-8').write(new + ('\n' if raw.endswith('\n') else ''))
    return added_param, added_tpl


def add_field():
    p = os.path.join(ROOT, 'model', 'COMSAuditLog.businessobject')
    d = json.load(open(p, encoding='utf-8'))
    if any(f['name'] == 'runId' for f in d['fields']):
        return 0
    d['fields'].append({"id": max(f['id'] for f in d['fields']) + 1, "name": "runId",
                        "label": "Orchestration Run ID", "type": "TEXT"})
    open(p, 'w', encoding='utf-8').write(json.dumps(d, indent=2, ensure_ascii=False) + '\n')
    return 1


def main():
    out = [f"field {'added' if add_field() else 'present'}"]
    for p in sorted(glob.glob(os.path.join(ROOT, 'orchestration', '*.orchestration'))):
        r = patch(p)
        if r is not None:
            out.append(f"{os.path.basename(p)}: +{r[0]} param, +{r[1]} template")
    print('audit_run_id: ' + '; '.join(out))


if __name__ == '__main__':
    main()
