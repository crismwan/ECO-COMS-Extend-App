#!/usr/bin/env python3
"""Audit records through the Graph API instead of REST paging.

REST returns audit records oldest first, so pages fetched a count and then offset pages that
depended on it (6 calls, one after another). The Graph API sorts on the server
(orderBy timestamp DESC), so each page is independent and the calls run side by side.
Fields come back with the same names; the record id is workdayID.id (the pages don't read it).
Confirmed by the graphql test suite (2026-11-04). Docs: developer.workday.com
"Run Graph API Queries on a Page", "Graph Query Components", "Pagination of Graph API Query Results".

Graph paging is cache based: a request with an offset fails ("Requests with offsets need to be run
after an initial request without an offset", HTTP 200 + error, and the page shows an endpoint error
even without failOnStatusCodes) unless the same query ran first with offset 0. So pages 1..N read
page 0's total in their offset, which makes them wait for it, and repeat offset 0 when not needed.

Pages in PAGES get: auditLogCount removed, auditPage0..N replaced by Graph endpoints with the same
names, and every `auditPageK.data ?? []` / `auditLogCount.total` reference rewritten.
"""
import json, os, re

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
APP = 'ecocomsphase_xclw_cm_sync2_vmzvxm'
PAGES = ['auditLogViewer']
QUERY_ID = 'auditLogsNewest'
PROVIDER = 'workday-graph'
FIELDS = ('workdayID { id } timestamp action objectType coName coReferenceId triggeredBy details '
          'effectiveDate roleName positionName changedByWid orgWid roleWid positionWid')
FAIL = [{"code": 400}, {"code": 403}, {"code": 429}]


def write_query():
    q = {
        "id": QUERY_ID,
        "parameters": ["offset"],
        "query": (f"query auditLogsNewest($offset: BigInt) {{ r: {APP}_COMSAuditLog("
                  f"dataSource: {{{APP}_comsAuditLogs: {{}}}}, orderBy: {{timestamp: DESC}}, limit: 100, offset: $offset) "
                  f"{{ total data {{ {FIELDS} }} }} }}"),
        "variables": {"offset": "<% offset %>"},
    }
    d = os.path.join(ROOT, 'presentation', 'graphQueries')
    os.makedirs(d, exist_ok=True)
    p = os.path.join(d, QUERY_ID + '.graphquery')
    new = json.dumps(q, indent=2) + '\n'
    if not os.path.exists(p) or open(p).read() != new:
        open(p, 'w').write(new)
        return 1
    return 0


def add_provider():
    p = os.path.join(ROOT, 'presentation', APP + '.amd')
    d = json.load(open(p, encoding='utf-8'))
    if any(x.get('key') == PROVIDER for x in d['dataProviders']):
        return 0
    d['dataProviders'].append({"key": PROVIDER, "value": "<% `{{apiGatewayEndpoint}}/graphql/v1` %>"})
    open(p, 'w', encoding='utf-8').write(json.dumps(d, indent=2, ensure_ascii=False) + '\n')
    return 1


TOTAL = "((!empty(auditPage0.data) && !empty(auditPage0.data.r)) ? (auditPage0.data.r.total ?? 0) : 0)"


def rows(k):
    # A Graph error comes back as HTTP 200 with data.r null, so guard each level before reading it.
    # Page k > 0 asks for offset 0 (a repeat of page 0) when there are too few records; skip it then.
    g = f"!empty(auditPage{k}.data) && !empty(auditPage{k}.data.r)"
    if k:
        g = f"{TOTAL} > {k * 100} && " + g
    return f"(({g}) ? (auditPage{k}.data.r.data ?? []) : [])"


def convert(page):
    p = os.path.join(ROOT, 'presentation', page + '.pmd')
    raw = open(p, encoding='utf-8').read()
    d = json.loads(raw)
    eps = d['endPoints']
    pages = sorted(int(m.group(1)) for e in eps for m in [re.fullmatch(r'auditPage(\d+)', e['name'])] if m)
    out = []
    for e in eps:
        if e['name'] == 'auditLogCount':
            continue
        m = re.fullmatch(r'auditPage(\d+)', e['name'])
        if m:
            k = int(m.group(1))
            e = {"name": e['name'], "baseUrlType": PROVIDER, "httpMethod": "POST", "authType": "sso",
                 "failOnStatusCodes": FAIL if k == 0 else [{"code": 429}],
                 "graphQuery": {"queryId": QUERY_ID, "parameters": {"offset": 0 if k == 0 else f"<% {TOTAL} > {k * 100} ? {k * 100} : 0 %>"}}}
        out.append(e)
    d['endPoints'] = out
    s = json.dumps(d, indent=2, ensure_ascii=False)
    # Undo an earlier run (this pass or an older version of it) so the rewrite below always applies.
    for k in pages:
        plain = f"((!empty(auditPage{k}.data) && !empty(auditPage{k}.data.r)) ? (auditPage{k}.data.r.data ?? []) : [])"
        s = s.replace(rows(k), f"auditPage{k}.data ?? []").replace(plain, f"auditPage{k}.data ?? []")
    s = s.replace(TOTAL, "auditLogCount.total ?? 0")
    for k in pages:
        s = s.replace(f"auditPage{k}.data ?? []", rows(k).replace('"', '\\"'))
    s = s.replace("(auditLogCount.total ?? 0)", TOTAL).replace("auditLogCount.total ?? 0", TOTAL)
    left = re.findall(r'auditLogCount|auditPage\d+\.data(?!\)|\.r)', s)
    if left:
        raise SystemExit(f"graphql_audit: {page} still has REST-style references: {sorted(set(left))}")
    new = s + '\n'
    if new != raw:
        open(p, 'w', encoding='utf-8').write(new)
        return 1
    return 0


def main():
    n = write_query() + add_provider() + sum(convert(pg) for pg in PAGES)
    print(f"graphql_audit: {n} file(s) changed")


if __name__ == '__main__':
    main()
