#!/usr/bin/env python3
"""Pending Requests by Age on the RBAC Hub (product owner 2026-11-04): role requests waiting for ISC review today,
grouped by business days waited (0-1, 2-3, 4-5, over 5), stacked by assignable vs AAA. From the request pages the
hub already loads (pendingRequestsPage0..2), so no new endpoint. Sits in the Home actions card row beside Role
Requests. No footer: the ISC Queue card on the same page opens the queue. Chart: stackedBarChart2 (as App Activity).
Idempotent."""
import json, os

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'presentation')
def save(n, d): open(os.path.join(ROOT, n), 'w', encoding='utf-8').write(json.dumps(d, indent=2, ensure_ascii=False) + '\n')

SCRIPT = '''/* Pending Requests by Age (tools/build_pending_age.py). Pure functions; dates compared as yyyy-MM-dd. */
var isWeekday = function(d) {
  let day = d.format('E');
  day != 'Sat' && day != 'Sun';
};

var isAaa = function(r) {
  (r.roleName ?? '').startsWith('Organizations and Roles Assignment Administrator');
};

/* Business days a request has waited (0 = requested today); 99 when older than 60 days. Same count as the ISC Queue's Waiting column. */
var businessAge = function(r, days, keys) {
  let i = keys.indexOf(('' + r.requestedDate).substring(0, 10));
  i < 0 ? 99 : days.subList(0, i).filter(d => { isWeekday(d) }).size();
};

var bucketOf = function(n) {
  n <= 1 ? '0-1 days' : (n <= 3 ? '2-3 days' : (n <= 5 ? '4-5 days' : 'Over 5 days'));
};

var pending = function(list) {
  list.filter(r => { r.status == 'Pending ISC Review' && !empty(r.requestedDate) });
};

var buckets = function(list) {
  let days = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59].map(n => { date:now().minusDays(n) });
  let keys = days.map(d => { d.format('yyyy-MM-dd') });
  let aged = pending(list).map(r => { { 'b': bucketOf(businessAge(r, days, keys)), 'aaa': isAaa(r) } });
  ['0-1 days', '2-3 days', '4-5 days', 'Over 5 days'].map(b => { { 'age': b, 'assignable': aged.filter(a => { a.b == b && !a.aaa }).size(), 'aaa': aged.filter(a => { a.b == b && a.aaa }).size() } });
};

var totalText = function(list) {
  let n = pending(list).size();
  n == 0 ? 'Nothing waiting for ISC review' : ('' + n + ' waiting for ISC review');
};

{
  "isWeekday": isWeekday,
  "isAaa": isAaa,
  "businessAge": businessAge,
  "bucketOf": bucketOf,
  "pending": pending,
  "buckets": buckets,
  "totalText": totalText
}
'''
open(os.path.join(ROOT, 'scripts', 'comsPendingAge.script'), 'w', encoding='utf-8').write(SCRIPT)

save(os.path.join('cards', 'PendingAgeChart.card'), {
    "id": "PendingAgeChart",
    "parameters": ["ages", "totalText"],
    "header": {"title": "Pending Requests by Age", "subtitle": "<% totalText ?? \"\" %>", "icon": "wd-accent-data-loading"},  # waiting over time; the only clock icon (time) is App Activity's
    "body": {"type": "chartCard", "chart": {
        "type": "stackedBarChart2",
        "id": "pendingAgeStackedBarChart",
        "data": "<% ages ?? [] %>",
        "dataVariableName": "age",
        "categoryDataSet": {"name": "Business days waiting", "value": "<% age.age %>"},
        "measurementDataSets": [
            {"name": "Assignable roles", "value": "<% age.assignable %>"},
            {"name": "AAA roles", "value": "<% age.aaa %>"}],
        "measurementAxisOptions": {"axisTitle": "Requests"}}}})

hub = json.load(open(os.path.join(ROOT, 'hubLanding.pmd'), encoding='utf-8'))
if 'comsPendingAge.script' not in hub.setdefault('include', []):
    hub['include'].append('comsPendingAge.script')
REQS = "list:flatten([pendingRequestsPage0.data ?? [], pendingRequestsPage1.data ?? [], pendingRequestsPage2.data ?? []])"
card = {"type": "card", "cardId": "PendingAgeChart",
        "parameters": "<% { 'ages': comsPendingAge.buckets(" + REQS + "), 'totalText': comsPendingAge.totalText(" + REQS + ") } %>"}
found = False


def walk(n):
    global found
    if isinstance(n, dict):
        if n.get('id') == 'actionsCardContainer':
            found = True
            n['cards'] = [c for c in n['cards'] if c.get('cardId') != 'PendingAgeChart'] + [card]
            n['layout'] = 'masonry'   # a 4th card in a grid row wraps onto its own row on narrower screens (Static.cardRow)
        for v in n.values(): walk(v)
    elif isinstance(n, list):
        for v in n: walk(v)


walk(hub)
if not found:
    raise SystemExit('build_pending_age: actionsCardContainer not found on the RBAC Hub')
save('hubLanding.pmd', hub)
print('Pending Requests by Age chart on the RBAC Hub')
