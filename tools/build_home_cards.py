#!/usr/bin/env python3
"""Workday Home card data (product owner 2026-11-02: "create true Home cards ... everything on the code end").

A Workday Home card is an orchestration built from the "Workday Home Card" template (developer.workday.com doc
mwd1629844754304; needs Workday Journeys, which UBC has in production). That template isn't offered for this app
in ubc_wcpdev2 yet, so its start/end JSON can't be copied (CLAUDE.md: don't hand-type orchestration JSON or guess it;
a wrong guess fails the App Hub build for the whole app).

What this builds now, cloned from orchestrations in this repo and Workday's sample apps:
  orchestration/MyRoleRequestsCardData.orchestration   synchronous; for the signed-in worker
  orchestration/IscQueueCardData.orchestration         synchronous; for ISC reviewers
Each makes the same calls the Home card will make and returns the card content as JSON:
  {"title": ..., "subtitle": ..., "linkText": ..., "linkPath": "/<tenant>/d/wday/app/<app>/<app>/<task>.htmld"}
They deploy and can be launched and tested today (test suite: HomeCards.*).

When the Home Card template appears (tenant admin turns on People Experience + Journeys): create one Home Card
orchestration in Orchestration Builder, copy its JSON (Settings → Open Current Source Code), save its start node and
end node as tools/home_card_template.json ({"type", "start", "end"}), and rerun this script: it then also writes
MyRoleRequestsHomeCard / IscQueueHomeCard with the same steps, mapping title/subtitle/link into the card's end step
(see to_home_card below; the end-step field mapping is filled in from that template).
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
COUNT = lambda ids: f'(if ({ids}.equals("[]")) "0" else ({ids}.length() - {ids}.replace(",", "").length() + 1).toString())'
LINK = lambda task: f'"/".append(context.tenant()).append("/d/wday/app/").append(context.appReferenceId()).append("/").append(context.appReferenceId()).append("/{task}.htmld")'
CARD = ('{"title": "{{data.Counts.title}}", "subtitle": "{{data.Counts.subtitle}}", '
        '"linkText": "{{data.Counts.linkText}}", "linkPath": "{{data.Counts.linkPath}}"}')

my = flow('MyRoleRequestsCardData', 'ManageCOMSAssignableRoles', [
    get('GetMe', '"/common/v1/workers/me"', 'The worker viewing the card'),
    values('Me', [('wid', 'data.GetMe.response.asJSON().stringAtJsonPath("$.id")')], 'Viewer WID'),
    get('GetMine', APP + '${"/v1/comsAssignableRoles?limit=100&requestedBy="}${data.Me.wid}"', "The viewer's own role requests (requestedBy is indexed)"),
    values('Counts', [
        ('pendingIds', 'data.GetMine.response.asJSON().arrayAtJsonPath("$.data[?(@.status == \'Pending ISC Review\')].id").toString()'),
        ('approvedIds', 'data.GetMine.response.asJSON().arrayAtJsonPath("$.data[?(@.status == \'Approved\')].id").toString()'),
        ('pending', COUNT('data.Counts.pendingIds')),
        ('approved', COUNT('data.Counts.approvedIds')),
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
        ('pendingIds', 'data.GetRequests.response.asJSON().arrayAtJsonPath("$.data[?(@.status == \'Pending ISC Review\')].id").toString()'),
        ('oldest', 'data.GetRequests.response.asJSON().arrayAtJsonPath("$.data[?(@.status == \'Pending ISC Review\')].requestedDate").asJSON().stringAtJsonPathWithDefault("$[0]", "")'),
        ('pending', COUNT('data.Counts.pendingIds')),
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


def to_home_card(data_flow, name, tpl):
    """Home Card version: the template's start/end, the same steps; the end step's title/subtitle/link fields read
    data.Counts.*. Called only when tools/home_card_template.json exists (copied from Orchestration Builder)."""
    f = copy.deepcopy(data_flow)
    v = f['_value']
    v['type'] = tpl['type']; v['start'] = tpl['start']
    v['nodes']['_value'] = [n for n in v['nodes']['_value'] if n['_value']['name']['_value'] != 'Card']
    end = json.dumps(tpl['end'])
    for k in ('title', 'subtitle', 'linkText', 'linkPath'):
        end = end.replace('__' + k.upper() + '__', 'data.Counts.' + k)   # placeholders put into the saved template by hand
    v['end'] = json.loads(end)
    v['name']['_value'] = name
    v['id']['_value'] = hashlib.md5(name.encode()).hexdigest()
    return f


tp = os.path.join(os.path.dirname(__file__), 'home_card_template.json')
if os.path.exists(tp):
    tpl = json.load(open(tp))
    save('MyRoleRequestsHomeCard', to_home_card(my, 'MyRoleRequestsHomeCard', tpl))
    save('IscQueueHomeCard', to_home_card(isc, 'IscQueueHomeCard', tpl))
    print('home card data + Home Card orchestrations written')
else:
    print('home card data orchestrations written (Home Card template not captured yet: tools/home_card_template.json)')
