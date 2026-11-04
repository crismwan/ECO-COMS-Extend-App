#!/usr/bin/env python3
"""Audit records carry the Workday business process event they belong to (field eventWid).

The Audit Log turns it into an event link with related actions (instanceList + widKey, VIEW page).
Where each writer gets the event:
- Role assignment changes (AssignRolePositions, BulkRoleApply, BulkRoleGridApply): the
  Assign_Roles_Event_Reference WID in the Staffing SOAP response, read as text like the bulk
  orchestrations already read faultstring: response.toString().substringAfter(...).substringBefore("<").
  An ExtractEvent CreateValues node is added right before WriteAuditLog.
- DENY (DenyRoleRequest): the request's reviewEventWid (ExtractRequest already reads it).
- APPROVE (reviewRoleRequestAssignableRole page): the step's event, bpStep.event.id.
- Withdraw (deleteAssignableRole page): the event the page cancels.
- REQUEST: none. The page writes the record before StartRoleRequestReview creates the event.
"""
import copy, json, os

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
RUN = '"runId": "{{data.GetInputParams.runId}}",'
ROLE_CALLS = {'AssignRolePositions': 'CallOrganizationUpdate', 'BulkRoleApply': 'CallAssignRoles',
              'BulkRoleGridApply': 'CallAssignRoles'}
EVENT_EXPR = ('data.{call}.response.toString().substringAfter("Assign_Roles_Event_Reference")'
              '.substringAfter("type=\\"WID\\">").substringBefore("<").trim()')


def nodes(n):
    if isinstance(n, dict):
        yield n
        for v in n.values():
            yield from nodes(v)
    elif isinstance(n, list):
        for v in n:
            yield from nodes(v)


def name_of(n):
    v = n.get('_value') if isinstance(n, dict) else None
    return v.get('name', {}).get('_value') if isinstance(v, dict) and isinstance(v.get('name'), dict) else None


def add_template(d, value_expr):
    """Put "eventWid" right after "runId" in the audit text template."""
    line = f'"eventWid": "{{{{{value_expr}}}}}",'
    n_done = 0
    for n in nodes(d):
        v = n.get('_value')
        if n.get('_type') == 'TextTemplate' and isinstance(v, str) and '"objectType"' in v and RUN in v and '"eventWid"' not in v:
            n['_value'] = v.replace(RUN, RUN + ' ' + line, 1)
            n_done += 1
    return n_done


def patch_role_orchestration(name, call):
    p = os.path.join(ROOT, 'orchestration', name + '.orchestration')
    raw = open(p, encoding='utf-8').read()
    d = json.loads(raw)
    added = 0
    proto = next(n for n in nodes(d) if n.get('_type') == 'CreateValues')
    # the node list that holds WriteAuditLog
    for n in nodes(d):
        if isinstance(n, dict) and n.get('_type') == ['List', 'Node'] or (isinstance(n, dict) and isinstance(n.get('_value'), list)):
            lst = n.get('_value')
            if not isinstance(lst, list):
                continue
            idx = next((i for i, x in enumerate(lst) if name_of(x) == 'WriteAuditLog'), None)
            if idx is None or any(name_of(x) == 'ExtractEvent' for x in lst):
                continue
            cv = copy.deepcopy(proto)
            cv['_value']['name']['_value'] = 'ExtractEvent'
            a = copy.deepcopy(cv['_value']['values']['_value'][0])
            a['_value']['param']['_value']['name']['_value'] = 'eventWid'
            a['_value']['param']['_value']['type']['_value'] = 'String'
            a['_value']['expr'] = {"_type": ["Expr", "String"], "_value": {
                "type": {"_type": "Type", "_value": "String"},
                "source": {"_type": "String", "_value": EVENT_EXPR.format(call=call)},
                "isAuto": {"_type": "Boolean", "_value": False}}}
            cv['_value']['values']['_value'] = [a]
            lst.insert(idx, cv)
            added += 1
    t = add_template(d, 'data.ExtractEvent.eventWid')
    if not any(name_of(n) == 'ExtractEvent' for n in nodes(d)):
        raise SystemExit(f"audit_event_ref: no WriteAuditLog node list found in {name}")
    if added or t:
        open(p, 'w', encoding='utf-8').write(json.dumps(d, separators=(',', ':'), ensure_ascii=False) + ('\n' if raw.endswith('\n') else ''))
    return added, t


def patch_deny():
    p = os.path.join(ROOT, 'orchestration', 'DenyRoleRequest.orchestration')
    raw = open(p, encoding='utf-8').read()
    d = json.loads(raw)
    t = add_template(d, 'data.ExtractRequest.reviewEventWid')
    if t:
        open(p, 'w', encoding='utf-8').write(json.dumps(d, separators=(',', ':'), ensure_ascii=False) + ('\n' if raw.endswith('\n') else ''))
    return t


def patch_page(page, expr_fn):
    p = os.path.join(ROOT, 'presentation', page + '.pmd')
    raw = open(p, encoding='utf-8').read()
    d = json.loads(raw)
    eps = d['outboundData']['outboundEndPoints']
    audit = next(e for e in eps if e['name'] == 'postAuditLog')
    want = {"outboundPath": "eventWid", "value": expr_fn(eps)}
    vals = audit['values']
    cur = next((v for v in vals if v['outboundPath'] == 'eventWid'), None)
    if cur == want:
        return 0
    if cur:
        vals.remove(cur)
    vals.append(want)
    open(p, 'w', encoding='utf-8').write(json.dumps(d, indent=2, ensure_ascii=False) + '\n')
    return 1


def withdraw_event(eps):
    url = next(e for e in eps if e['name'] == 'cancelReview')['url']
    head, tail = "<% 'events/' + ", " + '/cancel' %>"
    if not (url.startswith(head) and url.endswith(tail)):
        raise SystemExit("audit_event_ref: deleteAssignableRole cancelReview url changed shape")
    return '<% ' + url[len(head):-len(tail)] + ' %>'


def add_field():
    p = os.path.join(ROOT, 'model', 'COMSAuditLog.businessobject')
    d = json.load(open(p, encoding='utf-8'))
    if any(f['name'] == 'eventWid' for f in d['fields']):
        return 0
    d['fields'].append({"id": max(f['id'] for f in d['fields']) + 1, "name": "eventWid",
                        "label": "Workday Event WID", "type": "TEXT"})
    open(p, 'w', encoding='utf-8').write(json.dumps(d, indent=2, ensure_ascii=False) + '\n')
    return 1


def main():
    out = [f"field {'added' if add_field() else 'present'}"]
    for name, call in ROLE_CALLS.items():
        a, t = patch_role_orchestration(name, call)
        out.append(f"{name}: +{a} node, +{t} template")
    out.append(f"DenyRoleRequest: +{patch_deny()} template")
    out.append(f"approve page: {patch_page('reviewRoleRequestAssignableRole', lambda eps: "<% (!empty(bpStep.event)) ? (bpStep.event.id ?? '') : '' %>")}")
    out.append(f"withdraw page: {patch_page('deleteAssignableRole', withdraw_event)}")
    print('audit_event_ref: ' + '; '.join(out))


if __name__ == '__main__':
    main()
