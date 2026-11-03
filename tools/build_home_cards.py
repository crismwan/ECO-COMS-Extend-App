#!/usr/bin/env python3
"""Workday Home card data (product owner 2026-11-02: "create true Home cards ... everything on the code end").

A Workday Home card is an orchestration of type "Workday Home Card" (developer.workday.com doc mwd1629844754304;
available in WCP development tenants, and needs Workday Journeys elsewhere). This writes, from the same steps:
  orchestration/MyRoleRequestsCardData.orchestration   synchronous; for the signed-in worker
  orchestration/IscQueueCardData.orchestration         synchronous; for ISC reviewers
Each makes the same calls the Home card will make and returns the card content as JSON:
  {"title": ..., "subtitle": ..., "linkText": ..., "linkPath": "/<tenant>/d/wday/app/<app>/<app>/<task>.htmld"}
They can be launched and tested like any synchronous orchestration (test suite: HomeCards.*).
  orchestration/MyRoleRequestsHomeCard.orchestration   the same steps as a Workday Home Card orchestration
  orchestration/IscQueueHomeCard.orchestration         (add with the tenant task Create External Card)
Idempotent.
"""
import copy, hashlib, json, os, sys
ROOT = os.path.join(os.path.dirname(__file__), '..')
O = lambda n: json.load(open(os.path.join(ROOT, 'orchestration', n + '.orchestration')))


def save(name, flow):
    p = os.path.join(ROOT, 'orchestration', name + '.orchestration')
    open(p, 'w').write(json.dumps(flow, separators=(',', ':'), ensure_ascii=False))


def S(s):
    return {"_type": ["Expr", "String"], "_value": {"type": {"_type": "Type", "_value": "String"}, "source": {"_type": "String", "_value": s}, "isAuto": {"_type": "Boolean", "_value": False}}}


base = O('StartRoleRequestReview')          # FlowSync, StartBasic, EndSync, flowVersion 3.7.0
deny = O('DenyRoleRequest')
nodes = lambda f: f['_value']['nodes']['_value']
find = lambda f, n: copy.deepcopy([x for x in nodes(f) if x['_value']['name']['_value'] == n][0])


def rename(n, name, note=None):
    n['_value']['name']['_value'] = name
    n['_value']['notes']['_value'] = [] if not note else [{"_type": "Note", "_value": {"key": {"_type": "String", "_value": "description"}, "value": {"_type": "String", "_value": note}}}]
    return n


def get(name, path, note):
    n = rename(find(deny, 'GetRequest'), name, note)
    n['_value']['path'] = S(path)
    n['_value']['responseType']['_value'] = 'Json'
    return n


CV = find(base, 'GetInputParams')


def values(name, pairs, note):
    n = rename(copy.deepcopy(CV), name, note)
    proto = n['_value']['values']['_value'][0]
    out = []
    for pname, src in pairs:
        a = copy.deepcopy(proto)
        a['_value']['param']['_value']['name']['_value'] = pname
        a['_value']['param']['_value']['type']['_value'] = 'String'
        a['_value']['expr'] = S(src)
        out.append(a)
    n['_value']['values']['_value'] = out
    return n


# CreateTextTemplate node as in Workday's salesCommission sample (flowVersion 3.3.0; its node keys match our 3.7.0 nodes).
# EndSync body: in 3.7.0 files a null Opt names the supertype (ResponseBody, HttpBody) while a set one names the
# concrete type (CreateTextTemplateBody), so a set end body is ["Opt","DataRefBody"] as in the samples.
def template(name, message, note):
    return {"_type": "CreateTextTemplate", "_value": {
        "name": {"_type": "Identifier", "_value": name}, "isDisabled": {"_type": "Boolean", "_value": False},
        "errorHandler": {"_type": ["Opt", "ErrorHandler"], "_value": None},
        "message": {"_type": "TextTemplate", "_value": message},
        "contentType": {"_type": "String", "_value": "application/json"},
        "formatRef": {"_type": ["Opt", "TextFormatRef"], "_value": None},
        "notes": {"_type": ["List", "Note"], "_value": [{"_type": "Note", "_value": {"key": {"_type": "String", "_value": "description"}, "value": {"_type": "String", "_value": note}}}]}}}


# EndSync returning a node's output as JSON (DataRefBody, as in the samples' synchronous orchestrations)
def end_with(ref):
    e = copy.deepcopy(base['_value']['end'])
    e['_value']['body'] = {"_type": ["Opt", "DataRefBody"], "_value": {"_type": "DataRefBody", "_value": {
        "dataRef": {"_type": ["Expr", "Data"], "_value": {"type": {"_type": "Type", "_value": "Data"}, "source": {"_type": "String", "_value": ref}, "isAuto": {"_type": "Boolean", "_value": False}}},
        # compiler 3.406 (App Hub build 2026-11-02): contentType must be an expression, not a plain String
        "contentType": {"_type": ["Opt", ["Expr", "String"]], "_value": S('"application/json"')}}}}
    return e


def flow(name, domain, steps, description):
    f = copy.deepcopy(base)
    v = f['_value']
    v['id']['_value'] = hashlib.md5(name.encode()).hexdigest()   # stable id per orchestration
    v['name']['_value'] = name
    v['nodes']['_value'] = steps
    v['end'] = end_with('data.Card.message')
    v['notes']['_value'] = [{"_type": "Note", "_value": {"key": {"_type": "String", "_value": "description"}, "value": {"_type": "String", "_value": description}}}]
    v['securityDomains'] = {"_type": ["Opt", ["List", "String"]], "_value": {"_type": ["List", "String"], "_value": [{"_type": "String", "_value": domain}]}}
    return f


APP = 's"${"/apps/"}${context.appReferenceId()}'
# number of ids in a JSON array rendered as text: commas + 1, no division (avoids "3.0")
# arrayAtJsonPath on a filtered path fails at run time ("Expected array but found string", 2026-11-02), so count the
# quoted status value in the response text: len(text with X -> X + "#") - len(text) = occurrences of X, no division
COUNT = lambda text, value: f'({text}.replace("\\"{value}\\"", "\\"{value}\\"#").length() - {text}.length()).toString()'
LINK = lambda task: f'"/".append(context.tenant()).append("/d/wday/app/").append(context.appReferenceId()).append("/").append(context.appReferenceId()).append("/{task}.htmld")'
CARD = ('{"title": "{{data.Counts.title}}", "subtitle": "{{data.Counts.subtitle}}", '
        '"linkText": "{{data.Counts.linkText}}", "linkPath": "{{data.Counts.linkPath}}"}')

my = flow('MyRoleRequestsCardData', 'ManageCOMSAssignableRoles', [
    get('GetMe', '"/common/v1/workers/me"', 'The worker viewing the card'),
    values('Me', [('wid', 'data.GetMe.response.asJSON().stringAtJsonPath("$.id")')], 'Viewer WID'),
    get('GetMine', APP + '${"/v1/comsAssignableRoles?limit=100&requestedBy="}${data.Me.wid}"', "The viewer's own role requests (requestedBy is indexed)"),
    values('Counts', [
        ('text', 'data.GetMine.response.asJSON().toString()'),
        ('pending', COUNT('data.Counts.text', 'Pending ISC Review')),
        ('approved', COUNT('data.Counts.text', 'Approved')),
        ('title', '"My Role Requests"'),
        ('subtitle', '(if (data.Counts.pending.equals("0") && data.Counts.approved.equals("0")) "You have no role requests" else data.Counts.pending.append(" pending ISC review · ").append(data.Counts.approved).append(" approved"))'),
        ('linkText', '"Open My Requests"'),
        ('linkPath', LINK('assignableRoleManagerView')),
    ], 'Card text'),
    template('Card', CARD, 'Home card content'),
], 'Data for the My Role Requests Workday Home card: the signed-in worker\'s pending and approved requests, and a link to My Assignable Role Requests.')

isc = flow('IscQueueCardData', 'MaintainCOMSAssignableRoles', [
    get('GetRequests', APP + '${"/v1/comsAssignableRoles?limit=100"}"', 'Role requests (first 100; the collection returns oldest first, so the oldest pending are included)'),
    values('Counts', [
        ('text', 'data.GetRequests.response.asJSON().toString()'),
        # a filtered path read as a string gives the first match (the collection is oldest first) (unverified)
        ('oldest', 'data.GetRequests.response.asJSON().stringAtJsonPathWithDefault("$.data[?(@.status == \'Pending ISC Review\')].requestedDate", "")'),
        ('pending', COUNT('data.Counts.text', 'Pending ISC Review')),
        ('title', '"ISC Queue"'),
        ('subtitle', '(if (data.Counts.pending.equals("0")) "Nothing waiting for review" else data.Counts.pending.append(" waiting for review · oldest requested ").append(data.Counts.oldest.truncate(10)))'),
        ('linkText', '"Open ISC Queue"'),
        ('linkPath', LINK('iscRoleRequestsView')),
    ], 'Card text'),
    template('Card', CARD, 'Home card content'),
], 'Data for the ISC Queue Workday Home card: requests waiting for ISC review and the oldest request date, with a link to the ISC Queue.')

save('MyRoleRequestsCardData', my)
save('IscQueueCardData', isc)

# the ISC orchestration is secured by Maintain: COMS Assignable Roles, which must allow orchestration security
p = os.path.join(ROOT, 'model', 'MaintainCOMSAssignableRoles.securitydomain')
d = json.load(open(p))
if not d.get('enabledForOrchestrationSecurity'):
    d['enabledForOrchestrationSecurity'] = True
    open(p, 'w').write(json.dumps(d, indent=2) + '\n')


# ── Workday Home Card orchestrations ─────────────────────────────────────────────────────────────────────────────
# Shapes from Orchestration Builder's own type schema (flowbuilder bundle on developer.workday.com, read 2026-11-02):
#   flow type ".maya.FlowWorkdayTodayCard"; start StartWorkdayTodayCard (no properties);
#   CreateWorkdayTodayCard {name, isDisabled, errorHandler, source: String, title/subtitle/linkText: Expr String,
#                           linkDestination: Expr Url};
#   EndWorkdayTodayCard {refreshFrequency: Int (seconds; the builder offers 0 = don't cache ... 4 weeks),
#                        card: Expr Json} - the card step's output is "card" (Json), as the builder's data picker
#                        lists it ("json" fails the build: "Upstream Card does not produce an output named json").
# Default credential AccessTokenFromInitiatingUser (the builder's default for this type; ours already use it), so
# /workers/me is the person viewing Workday Home.
REFRESH_SECONDS = 3600     # "1 hour" in the builder's list: counts stay cheap to serve, at most an hour old


def expr(type_name, source):
    return {"_type": ["Expr", type_name], "_value": {"type": {"_type": "Type", "_value": type_name},
            "source": {"_type": "String", "_value": source}, "isAuto": {"_type": "Boolean", "_value": False}}}


def to_home_card(data_flow, name, description):
    f = copy.deepcopy(data_flow)
    v = f['_value']
    # new id: the first ids were deleted in App Hub on 2026-11-02 and an upload reusing them was refused
    v['id']['_value'] = hashlib.md5((name + ':2').encode()).hexdigest()
    v['name']['_value'] = name
    v['type'] = {"_type": "FlowType", "_value": ".maya.FlowWorkdayTodayCard"}
    v['start'] = {"_type": "StartWorkdayTodayCard", "_value": {"notes": {"_type": ["List", "Note"], "_value": []}}}
    card = {"_type": "CreateWorkdayTodayCard", "_value": {
        "name": {"_type": "Identifier", "_value": "Card"},
        "isDisabled": {"_type": "Boolean", "_value": False},
        "errorHandler": {"_type": ["Opt", "ErrorHandler"], "_value": None},
        "source": {"_type": "String", "_value": "ECO-COMS"},
        "title": expr("String", "data.Counts.title"),
        "subtitle": expr("String", "data.Counts.subtitle"),
        "linkDestination": expr("Url", "data.Counts.linkPath"),
        "linkText": expr("String", "data.Counts.linkText"),
        "notes": {"_type": ["List", "Note"], "_value": [{"_type": "Note", "_value": {"key": {"_type": "String", "_value": "description"}, "value": {"_type": "String", "_value": "The Workday Home card"}}}]}}}
    v['nodes']['_value'] = [n for n in v['nodes']['_value'] if n['_value']['name']['_value'] != 'Card'] + [card]
    v['end'] = {"_type": "EndWorkdayTodayCard", "_value": {
        "refreshFrequency": {"_type": "Int", "_value": REFRESH_SECONDS},
        "card": expr(["Json", {"_type": ["Opt", "JsonSchemaRef"], "_value": None}], "data.Card.card"),
        "notes": {"_type": ["List", "Note"], "_value": []}}}
    v['notes']['_value'] = [{"_type": "Note", "_value": {"key": {"_type": "String", "_value": "description"}, "value": {"_type": "String", "_value": description}}}]
    # App Hub build (2026-11-02): "Security domains can only be defined for Sync and Async orchestrations". Who sees
    # the card is set in the tenant (Create External Card, Custom Card policies), and the card only reads data
    v['securityDomains'] = {"_type": ["Opt", ["List", "String"]], "_value": None}
    return f


save('MyRoleRequestsHomeCard', to_home_card(my, 'MyRoleRequestsHomeCard',
     'Workday Home card: the viewer\'s pending and approved role requests, linking to My Assignable Role Requests.'))
save('IscQueueHomeCard', to_home_card(isc, 'IscQueueHomeCard',
     'Workday Home card: requests waiting for ISC review and the oldest request date, linking to the ISC Queue.'))
print('home card data + Workday Home Card orchestrations written')
