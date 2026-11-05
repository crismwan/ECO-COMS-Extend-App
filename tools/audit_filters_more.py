#!/usr/bin/env python3
"""Audit Log: Changed By and Organization filters (2026-11-04).

- Changed By card: "Anyone" / "Only my changes" (query param `by` = a changedByWid).
- Organization card, shown only while an organization is picked (query params orgId, orgCode, orgName):
  "All organizations" clears it. Shell Org Detail links here with its org ("View changes in Audit Log").
  A record belongs to the org by the same rule Shell Org Detail uses: orgWid, coReferenceId or coName.
- Filtering runs in the page on the newest 500 records, like the time-period and change-type filters
  (comsAuditFilters.filterOrgBy wraps the loaded list before filterLogs).
- Every pill carries all four choices along, so switching one filter keeps the others.
Pills have no `render` (developer.workday.com "pillCard"), so the Organization card hides as a whole
through the card's own `render`. Runs after graphql_audit.py. Idempotent.
"""
import json, os, re

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'presentation')
load = lambda n: json.load(open(os.path.join(ROOT, n), encoding='utf-8'))
def save(n, d): open(os.path.join(ROOT, n), 'w', encoding='utf-8').write(json.dumps(d, indent=2, ensure_ascii=False) + '\n')

KEYS = ['period', 'changeType', 'by', 'orgId', 'orgCode', 'orgName']


def binds(**over):
    # card scripts take double-quoted literals only
    b = {k: '<% ' + k + ' ?? "" %>' for k in KEYS}
    b.update(over)
    return b


def pill(label, cond, **over):
    return {"label": '<% (' + cond + ') ? "✓ ' + label + '" : "' + label + '" %>',
            "taskReference": {"taskId": "auditLogViewer", "parameterBindings": binds(**over)}}


PERIODS = [("All time", "all"), ("Last 24 hours", "24h"), ("Last 7 days", "7d"), ("Last 30 days", "30d")]
TYPES = [("All types", ""), ("Shell Org", "Shell Org"), ("Pattern", "Shell Org Pattern"), ("Org Status", "Org Status"),
         ("Role Assignment", "Role Assignment"), ("Assignable Role", "Assignable Role"),
         ("Application Pattern", "Application Pattern")]
ORG_SET = '(!empty(orgId) || !empty(orgCode) || !empty(orgName))'
cards = {
    "AuditPeriodPillCard": {"id": "AuditPeriodPillCard", "parameters": KEYS,
        "header": {"title": "Time Period", "icon": "wd-accent-calendar"},
        "body": {"type": "pillCard", "pills": [
            pill(l, ('empty(period) || period == "all"' if k == "all" else 'period == "' + k + '"'), period=k) for l, k in PERIODS]}},
    "AuditTypePillCard": {"id": "AuditTypePillCard", "parameters": KEYS,
        "header": {"title": "Change Type", "icon": "wd-accent-scroll-shield"},
        "body": {"type": "pillCard", "pills": [
            pill(l, ('empty(changeType)' if k == "" else 'changeType == "' + k + '"'), changeType=k) for l, k in TYPES]}},
    "AuditByPillCard": {"id": "AuditByPillCard", "parameters": KEYS + ['me'],
        "header": {"title": "Changed By", "icon": "wd-accent-person"},
        "body": {"type": "pillCard", "pills": [
            pill("Anyone", 'empty(by)', by=""),
            pill("Only my changes", '!empty(by) && by == (me ?? "")', by='<% me ?? "" %>')]}},
    "AuditOrgPillCard": {"id": "AuditOrgPillCard", "parameters": KEYS,
        "header": {"title": "Organization", "icon": "wd-accent-building"},
        "body": {"type": "pillCard", "pills": [
            {"label": "All organizations", "taskReference": {"taskId": "auditLogViewer",
                "parameterBindings": binds(orgId="", orgCode="", orgName="")}},
            {"label": '<% "✓ " + ((orgCode ?? "") != "" ? orgCode : (orgName ?? "")) %>', "taskReference": {"taskId": "auditLogViewer",
                "parameterBindings": binds()}}]}},
}
for cid, c in cards.items():
    save(os.path.join('cards', cid + '.card'), c)

# ── the page ──
page = load('auditLogViewer.pmd')
if not any(e['name'] == 'selectedWorker' for e in page['endPoints']):
    page['endPoints'].insert(0, {"name": "selectedWorker", "baseUrlType": "COMMON", "url": "/workers/me", "authType": "sso",
                                 "bestEffort": "true", "failOnStatusCodes": [{"code": 400}, {"code": 403}, {"code": 429}]})
P = "<% { " + ", ".join(f"'{k}': queryParams.{k} ?? ''" for k in KEYS) + " } %>"
PME = P[:-4] + ", 'me': selectedWorker.id ?? '' } %>"


def container(n):
    if isinstance(n, dict):
        if n.get('id') == 'auditFilterCardContainer':
            rest = [c for c in n['cards'] if c.get('cardId') not in cards]
            n['cards'] = [
                {"type": "card", "cardId": "AuditPeriodPillCard", "parameters": P},
                {"type": "card", "cardId": "AuditTypePillCard", "parameters": P},
                {"type": "card", "cardId": "AuditByPillCard", "parameters": PME},
                {"type": "card", "cardId": "AuditOrgPillCard", "parameters": P,
                 "render": "<% !empty(queryParams.orgId) || !empty(queryParams.orgCode) || !empty(queryParams.orgName) %>"},
            ] + rest
            return True
        return any(container(v) for v in n.values())
    if isinstance(n, list):
        return any(container(v) for v in n)
    return False


if not container(page):
    raise SystemExit('audit_filters_more: auditFilterCardContainer not found')
s = json.dumps(page, ensure_ascii=False)
WRAP_OPEN = 'comsAuditFilters.filterLogs(comsAuditFilters.filterOrgBy(list:flatten(['
WRAP_CLOSE = ("]), queryParams.orgId ?? '', queryParams.orgCode ?? '', queryParams.orgName ?? '', queryParams.by ?? ''), "
              "queryParams.period ?? '', queryParams.changeType ?? '')")
if WRAP_OPEN not in s:
    n_open = s.count('comsAuditFilters.filterLogs(list:flatten([')
    n_close = s.count("]), queryParams.period ?? '', queryParams.changeType ?? '')")
    if not n_open or n_open != n_close:
        raise SystemExit(f'audit_filters_more: filterLogs calls changed shape ({n_open} opens, {n_close} closes)')
    s = s.replace('comsAuditFilters.filterLogs(list:flatten([', WRAP_OPEN)
    s = s.replace("]), queryParams.period ?? '', queryParams.changeType ?? '')", WRAP_CLOSE)
LABEL_OLD = "(empty(queryParams.changeType) ? '' : ', ' + queryParams.changeType) + ')'"
LABEL_NEW = ("(empty(queryParams.changeType) ? '' : ', ' + queryParams.changeType) + "
             "(empty(queryParams.orgCode) && empty(queryParams.orgName) ? '' : ', ' + (!empty(queryParams.orgCode) ? queryParams.orgCode : queryParams.orgName)) + "
             "(empty(queryParams.by) ? '' : ((queryParams.by == (selectedWorker.id ?? '')) ? ', my changes' : ', one person')) + ')'")
if LABEL_NEW not in s:
    if LABEL_OLD not in s:
        raise SystemExit('audit_filters_more: Showing line changed shape')
    s = s.replace(LABEL_OLD, LABEL_NEW, 1)
save('auditLogViewer.pmd', json.loads(s))

# ── the script ──
sp = os.path.join(ROOT, 'scripts', 'comsAuditFilters.script')
src = open(sp, encoding='utf-8').read()
FN = '''/* Organization and Changed By filters (tools/audit_filters_more.py). A record belongs to the org by its
   WID, its code (coReferenceId or coName) or its name, as on Shell Org Detail. */
var filterOrgBy = function(logs, orgId, orgCode, orgName, by) {
  (empty(orgId) && empty(orgCode) && empty(orgName) && empty(by)) ? logs : logs.filter(e => { (empty(by) || (e.changedByWid ?? '') == by) && ((empty(orgId) && empty(orgCode) && empty(orgName)) || (!empty(orgId) && (e.orgWid ?? '') == orgId) || (!empty(orgCode) && ((e.coReferenceId ?? '') == orgCode || (e.coName ?? '') == orgCode)) || (!empty(orgName) && (e.coName ?? '') == orgName)) });
};

'''
if 'var filterOrgBy' not in src:
    src = src.replace('var periodLabel = function', FN + 'var periodLabel = function', 1)
    src = src.replace('  "filterLogs": filterLogs,', '  "filterLogs": filterLogs,\n  "filterOrgBy": filterOrgBy,', 1)
    if '"filterOrgBy": filterOrgBy' not in src:
        raise SystemExit('audit_filters_more: script exports changed shape')
    open(sp, 'w', encoding='utf-8').write(src)

# ── Shell Org Detail: open the Audit Log for this org ──
det = load('shellOrgDetail.pmd')
LINK = {"type": "button", "id": "auditLogButton", "label": "View changes in Audit Log", "action": "LINK",
        "taskReference": {"taskId": "auditLogViewer", "parameterBindings": {
            "orgId": "<% queryParams.orgId ?? '' %>", "orgCode": "<% queryParams.orgCode ?? '' %>", "orgName": "<% queryParams.orgName ?? '' %>"}}}


def nav(n):
    if isinstance(n, dict):
        kids = n.get('children')
        if isinstance(kids, list) and any(isinstance(k, dict) and k.get('id') == 'backButton' for k in kids):
            kids[:] = [k for k in kids if not (isinstance(k, dict) and k.get('id') == 'auditLogButton')]
            i = next(i for i, k in enumerate(kids) if isinstance(k, dict) and k.get('id') == 'backButton')
            kids.insert(i + 1, json.loads(json.dumps(LINK)))
            return True
        return any(nav(v) for v in n.values())
    if isinstance(n, list):
        return any(nav(v) for v in n)
    return False


if not nav(det['presentation']):
    raise SystemExit('audit_filters_more: Shell Org Detail back button not found')
save('shellOrgDetail.pmd', det)
print('audit_filters_more: cards, page filters, script and Shell Org Detail link set')
