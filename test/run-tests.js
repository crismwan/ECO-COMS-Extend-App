#!/usr/bin/env node
/**
 * ECO-COMS tests: one runner for every suite.
 *
 *   node test/run-tests.js static            repo checks, no tenant access (blocks upload; every push)
 *   node test/run-tests.js smoke             read-only live checks (after every deploy)
 *   node test/run-tests.js full              smoke + write tests for every flow (manual; leaves TEST data)
 *   node test/run-tests.js cleanup [--apply] list (default) or remove TEST data
 *   node test/run-tests.js isu               ISU lockdown checks: only once ISU writes are live (see README)
 *   node test/run-tests.js repair [--apply] [--unassign P-id]  one-off data fixes (dry run by default)
 *   node test/run-tests.js seconduser      requester vs admin checks (needs WD_SECOND_TOKEN; leaves 3 Denied TEST requests)
 *
 * Suites can be combined: `node test/run-tests.js static,smoke`. The isu suite never runs unless named.
 * Options: --verbose, --token <t>, --role <assignable role> (full/cleanup), --also <ids>, --effective
 * <yyyy-MM-dd>, --only <org codes> (cleanup). `--suite <name>` also works.
 *
 * Token for live suites (never printed): --token, else WD_DEV_TOKEN, else
 * ~/.config/@workday/wdcli/config.json (wcpTenantAccessToken.ubc_wcpdev2).
 *
 * Results: console, test/results.json, and the GitHub run summary. Exit 1 if any test fails.
 * Coverage map and manual checklist: test/README.md.
 */

'use strict';
const https = require('https');
const fs = require('fs');
const path = require('path');
const os = require('os');

// Effective dates in the tenant's own time zone (Vancouver). A UTC date is already tomorrow after 5 pm
// Pacific, and Workday then schedules the change for tomorrow (seen 2026-10-31: an ADD dated 2026-11-01
// didn't show on the role, so the test never removed it).
const TENANT_TZ = 'America/Los_Angeles';
const tenantDate = (offsetDays = 0, from = Date.now()) =>
  new Intl.DateTimeFormat('en-CA', { timeZone: TENANT_TZ, year: 'numeric', month: '2-digit', day: '2-digit' }).format(new Date(from + offsetDays * 86400000));

const ROOT = path.join(__dirname, '..');
const APP_ID = 'ecocomsphase_xclw_cm_sync2_vmzvxm';
const TENANT = 'ubc_wcpdev2';
const API = 'https://api.workday.com';
const BO = `${API}/apps/${APP_ID}/v1`;
const WQL = `${API}/wql/v1/data`;
const BP = `${API}/businessProcess/v1`;
const ORCH = `${API}/orchestrate/v1/apps/${APP_ID}/orchestrations`;

const argv = process.argv.slice(2);
const arg = (name) => { const i = argv.indexOf(name); return i === -1 ? null : argv[i + 1]; };
const VERBOSE = argv.includes('--verbose');
const SUITES_ALL = ['static', 'smoke', 'full', 'cleanup', 'isu', 'repair', 'seconduser', 'purge', 'demoseed', 'datacheck', 'probe', 'bulkvalidate', 'subflows', 'seedapps', 'patternguard', 'orgguard', 'gateway', 'prompts', 'possearch', 'postree', 'orgtree', 'aaaname', 'appsummary', 'graphql', 'eventlinks', 'timing', 'bulkapply'];
const suiteArg = arg('--suite') || argv.find((a) => !a.startsWith('--') && SUITES_ALL.some((s) => a.split(',').includes(s))) || 'smoke';
const SUITES = suiteArg.split(',').map((s) => s.trim()).filter(Boolean);
for (const s of SUITES) if (!SUITES_ALL.includes(s)) { console.error(`Unknown suite "${s}". Use: ${SUITES_ALL.join(', ')}`); process.exit(2); }

// Fixed vocabulary (CLAUDE.md "Audit log design"). A new value here means a page or
// orchestration started writing something the viewer and reports don't expect.
const OBJECT_TYPES = ['Shell Org', 'Shell Org Pattern', 'Org Status', 'Role Assignment', 'Assignable Role', 'Application Pattern'];
const ACTIONS = ['ADD', 'INACTIVATE', 'REACTIVATE', 'ASSIGN POSITION', 'REMOVE POSITION', 'REQUEST', 'APPROVE', 'DENY', 'DELETE', 'REVIEW', 'UPDATE'];
const TEST_ROLE = arg('--role') || process.env.E2E_ROLE || 'X:BPMS(ODMT):ROLE:ADVISORS';
const BO_COLLECTIONS = ['comsApplications', 'comsAssignableRoles', 'comsAuditLogs'];

// ─── Results ──────────────────────────────────────────────────────────────────
const results = [];
// Everything printed is also kept for the GitHub run summary (job logs are often truncated).
const transcript = [];
for (const k of ['log', 'error']) {
  const orig = console[k].bind(console);
  console[k] = (...a) => { transcript.push(a.join(' ')); orig(...a); };
}
const record = (status, name, msg) => {
  results.push({ status, name, msg });
  (status === 'FAIL' ? console.error : console.log)(`  ${status.padEnd(4)}  ${name}: ${msg}`);
};
const pass = (n, m) => record('PASS', n, m);
const fail = (n, m) => record('FAIL', n, m);
const skip = (n, m) => record('SKIP', n, m);
const warn = (n, m) => record('WARN', n, m);
async function test(name, fn) {
  try { await fn(); } catch (e) { fail(name, e.message); }
}

// ═══ Static suite: repo checks, no tenant access ═════════════════════════════
// Each check encodes a platform pitfall that broke this app before (CLAUDE.md). Failures block upload.

// Known issues: reported as WARN instead of FAIL until fixed. Each needs a reason.
// Remove an entry as soon as the issue is fixed so the check protects it again.
const KNOWN_ISSUES = {
};
const AMD_PATH = 'presentation/ecocomsphase_xclw_cm_sync2_vmzvxm.amd';
const MAX_FILE_BYTES = 100 * 1024; // platform limit for .pmd/.amd/.smd/.pod/.script
const MAX_PAGES = 75;              // platform limit for pages per app
const PROTECTED_KEYS = ['endPoints', 'outboundData', 'securityDomains', 'include']; // must sit at page root

function listFiles(dir, recursive) {
  const abs = path.join(ROOT, dir);
  if (!fs.existsSync(abs)) return [];
  const out = [];
  for (const e of fs.readdirSync(abs, { withFileTypes: true })) {
    const rel = path.posix.join(dir, e.name);
    if (e.isDirectory()) { if (recursive) out.push(...listFiles(rel, true)); } else out.push(rel);
  }
  return out.sort();
}
// Call fn(node, parentKey) for every object in a JSON tree (list items inherit the list's key).
function walk(node, fn, parentKey = null) {
  if (Array.isArray(node)) node.forEach((v) => walk(v, fn, parentKey));
  else if (node && typeof node === 'object') {
    fn(node, parentKey);
    for (const [k, v] of Object.entries(node)) walk(v, fn, k);
  }
}

function staticSuite() {
  console.log('\n-- Static (repo checks, no tenant access) --');
  const errs = [];
  const err = (check, msg, file) => {
    const reason = KNOWN_ISSUES[`${check}|${file}`];
    if (reason) warn(`Static.${check}`, `KNOWN ISSUE ${msg} (${reason})`); else { errs.push(msg); fail(`Static.${check}`, msg); }
  };

  // 1. Every JSON component parses
  const jsonFiles = new Set([
    ...listFiles('presentation').filter((f) => /\.(pmd|amd|smd|pod|card)$/.test(f)),
    ...listFiles('presentation/pods').filter((f) => f.endsWith('.pod')),
    ...listFiles('presentation/cards').filter((f) => f.endsWith('.card')),
    ...listFiles('model'),
    ...listFiles('orchestration').filter((f) => /\.(orchestration|suborchestration)$/.test(f)),
    ...listFiles('presentation', true).filter((f) => f.endsWith('.wqlquery')),
  ]);
  const docs = {};
  for (const f of jsonFiles) {
    try { docs[f] = JSON.parse(fs.readFileSync(path.join(ROOT, f), 'utf8')); } catch (e) { err('json', `${f}: ${e.message}`); }
  }
  const pmds = Object.fromEntries(Object.entries(docs).filter(([f]) => f.endsWith('.pmd')));
  const cards = Object.fromEntries(Object.entries(docs).filter(([f]) => f.endsWith('.card')));
  const amd = docs[AMD_PATH] || (err('amd', `${AMD_PATH} missing or unreadable`), {});

  // 2. Size and count limits
  for (const f of listFiles('presentation', true).filter((x) => /\.(pmd|amd|smd|pod|script)$/.test(x))) {
    const n = fs.statSync(path.join(ROOT, f)).size;
    if (n > MAX_FILE_BYTES) err('size', `${f}: ${n} bytes exceeds the 100 KB file limit`);
  }
  if (Object.keys(pmds).length > MAX_PAGES) err('size', `${Object.keys(pmds).length} pages exceeds the ${MAX_PAGES}-page app limit`);

  // 3. Page rules
  for (const [f, d] of Object.entries(pmds).concat(Object.entries(docs).filter(([x]) => x.endsWith('.pod')))) {
    const name = path.basename(f);
    const pres = d.presentation || {};
    for (const k of PROTECTED_KEYS) if (k in pres) err('protectedKey', `${name}: '${k}' is inside 'presentation'; move it to the page root`);
    if (pres.footer && pres.footer.type !== 'footer') err('footer', `${name}: footer block needs type "footer" (got ${JSON.stringify(pres.footer.type)})`);
    if (!f.endsWith('.pmd')) continue;
    const pageType = pres.pageType ?? d.pageType;
    if (pageType != null && !['EDIT', 'VIEW'].includes(pageType)) err('pageType', `${name}: pageType ${JSON.stringify(pageType)} must be "EDIT" or "VIEW" (uppercase)`);
    if ([true, 'true'].includes(pres.standardEditButtonsHidden) && !('editButtonBar' in pres)) {
      err('submitButton', `${name}: standardEditButtonsHidden without editButtonBar leaves no way to submit`, name);
    }
    walk(d, (node) => {
      for (const k of Object.keys(node)) if (k.startsWith('_')) err('underscoreAttr', `${name}: App Builder attribute '${k}' on ${node.id || node.type || '?'} is not valid PMD`);
      if (['checkbox', 'dropDown', 'select'].includes(node.type)) err('widgetType', `${name}: widget type '${node.type}' is invalid (use checkBox / dropdown)`);
      if (node.type === 'fieldSet' && 'label' in node && 'title' in node) err('fieldSet', `${name}: fieldSet '${node.id || '?'}' has both 'label' and 'title'; remove one`);
      const tr = node.taskReference;
      if (tr && typeof tr === 'object' && 'parameters' in tr && 'parameterBindings' in tr) err('taskReference', `${name}: ${node.id || '?'} has both parameters and parameterBindings (parameters are dropped)`);
    });
    // queryParams: a bare name in a script is a classic "1 Error"; only known param names are flagged.
    if (/<%[^%]*(?<![\w.])errorCode\b/.test(JSON.stringify(d))) err('queryParams', `${name}: bare 'errorCode' in a script; use queryParams.errorCode`);
  }

  // 3b. Search text typed by the user must not go into a WQL query raw (WQL injection).
  for (const [f, d] of Object.entries(pmds)) {
    walk(d, (node) => {
      const u = String(node.url || '');
      if (/data\?query=/.test(u) && /(instanceListQuery|event\.query)(?!\.replace\('\\'', ''\))/.test(u)) {
        err('wqlInjection', `${path.basename(f)}: endpoint '${node.name || '?'}' puts user search text into WQL without removing quotes; use instanceListQuery.replace('\\'', '').replace('\\\\', '')`);
      }
    });
  }

  // 4. Task references resolve
  const tasks = Object.fromEntries((amd.tasks || []).filter((t) => t && typeof t === 'object').map((t) => [t.id, t]));
  const pageIds = new Set(Object.values(pmds).map((d) => d.id));
  // Extend Cards for Workday pages: the AMD task's page is the .carddefinition (Workday sample workFromAlmostAnywhere)
  for (const f of listFiles('presentation/cards').filter((x) => x.endsWith('.carddefinition'))) pageIds.add(path.basename(f, '.carddefinition'));
  for (const [tid, t] of Object.entries(tasks)) {
    const pid = (t.page || {}).id;
    if (pid && !pageIds.has(pid)) err('amdTask', `AMD task '${tid}' points at page '${pid}', which has no .pmd file`);
  }
  const refs = [];
  for (const [f, d] of [...Object.entries(pmds), ...Object.entries(cards), [AMD_PATH, amd]]) {
    walk(d, (node, pk) => {
      if (['taskReference', 'initialTask', 'task', 'cancelOverride', 'conclusion'].includes(pk) && typeof node.taskId === 'string') refs.push([path.basename(f), node.taskId]);
      for (const s of node.flowSteps || []) if (s && typeof s.taskId === 'string') refs.push([path.basename(f), s.taskId]);
    });
  }
  for (const [src, tid] of refs) if (!tid.includes('<%') && !(tid in tasks)) err('taskRef', `${src}: references taskId '${tid}', which is not in the AMD tasks list`);

  // 5. Orchestration launches point at real orchestrations
  const orchNames = new Set(listFiles('orchestration').filter((f) => f.endsWith('.orchestration')).map((f) => path.basename(f, '.orchestration')));
  for (const [f, d] of Object.entries(pmds)) {
    for (const m of JSON.stringify(d).matchAll(/\/([A-Za-z0-9_]+)\/launch/g)) {
      if (!orchNames.has(m[1])) err('orchestration', `${path.basename(f)}: launches '${m[1]}', but orchestration/${m[1]}.orchestration does not exist`);
    }
  }

  // 5b. Orchestrations a user can launch must be secured by a domain enabled for orchestration security
  // (otherwise anyone who can reach the launch URL can run them). BP-triggered ones run as the
  // tenant's launch user and are exempt.
  const domains = Object.fromEntries(listFiles('model').filter((f) => f.endsWith('.securitydomain'))
    .map((f) => docs[f]).filter(Boolean).map((d) => [d.name, d]));
  for (const f of listFiles('orchestration').filter((x) => x.endsWith('.orchestration'))) {
    const v = (docs[f] || {})._value || {};
    // App Hub allows security domains only on Sync and Async orchestrations (build error 2026-11-02); a sub-orchestration
    // (FlowSubflow) has no launch URL, only its callers do (the builder writes it with securityDomains null)
    if (/BusinessProcessTriggered|WorkdayTodayCard|FlowSubflow/.test(String(v.type?._value || ''))) {
      if (((v.securityDomains || {})._value || {})._value) err('orchSecurity', `${path.basename(f)}: ${v.type._value} can't have securityDomains (App Hub: only Sync and Async)`);
      continue;
    }
    const secured = ((v.securityDomains || {})._value || {})._value || [];
    const names = secured.map((x) => x._value);
    if (!names.length) { err('orchSecurity', `${path.basename(f)}: no securityDomains; anyone who can reach its launch URL can run it`); continue; }
    if (names.length > 1) err('orchSecurity', `${path.basename(f)}: ${names.length} security domains; App Hub allows only one per orchestration (use one orchestration per launching page)`);
    for (const n of names) {
      if (!domains[n]) err('orchSecurity', `${path.basename(f)}: security domain '${n}' is not defined in model/`);
      else if (domains[n].enabledForOrchestrationSecurity !== true) err('orchSecurity', `${path.basename(f)}: domain '${n}' needs "enabledForOrchestrationSecurity": true`);
    }
  }

  // 5c. Sub-orchestrations (orchestration/<Name>.suborchestration, App Hub's own extension; 2026-11-04): each is a
  // FlowSubflow, and every CallSubflow names one by its 32-hex id (the name is rejected: "Invalid Subflow Reference ID")
  // with exactly the inputs its StartSubflow declares.
  const subs = {};
  for (const f of listFiles('orchestration').filter((x) => x.endsWith('.suborchestration'))) {
    const v = (docs[f] || {})._value || {};
    if (v.type?._value !== '.maya.FlowSubflow') err('subflow', `${path.basename(f)}: a .suborchestration must be type .maya.FlowSubflow (is ${v.type?._value})`);
    const ins = ((v.start?._value?.parameters || {})._value || []).map((p) => p._value?.name?._value);
    subs[v.id?._value] = { name: v.name?._value, ins };
  }
  for (const f of listFiles('orchestration').filter((x) => /\.(orchestration|suborchestration)$/.test(x))) {
    if (((docs[f] || {})._value || {}).type?._value === '.maya.FlowSubflow' && f.endsWith('.orchestration'))
      err('subflow', `${path.basename(f)}: a FlowSubflow must be saved as .suborchestration (App Hub ignores it as .orchestration)`);
    walk(docs[f] || {}, (node) => {
      if (node._type !== 'CallSubflow') return;
      const c = node._value || {}; const id = c.subflowId?._value; const step = c.name?._value;
      const sub = subs[id];
      if (!sub) { err('subflow', `${path.basename(f)}: step ${step} calls subflowId '${id}', which is no .suborchestration's id`); return; }
      const args = ((c.parameters || {})._value || []).map((a) => a._value?.param?._value?.name?._value);
      const miss = sub.ins.filter((n) => !args.includes(n)), extra = args.filter((n) => !sub.ins.includes(n));
      if (miss.length || extra.length) err('subflow', `${path.basename(f)}: ${step} -> ${sub.name}: missing inputs [${miss}] extra [${extra}]`);
    });
  }

  // 5c2. Naming standard (2026-11-06): IORC_0037_XFD_SEC_<Functional_Description>, sub-orchestrations ..._Sub_<...>.
  // Underscores only: Orchestration Builder won't take a hyphen in a name (live 2026-11-06). The file is named after it.
  for (const f of listFiles('orchestration').filter((x) => /\.(orchestration|suborchestration)$/.test(x))) {
    const v = (docs[f] || {})._value || {}; const n = v.name?._value || '';
    const sub = v.type?._value === '.maya.FlowSubflow';
    if (!(sub ? /^IORC_0037_XFD_SEC_Sub_[A-Za-z0-9_]+$/ : /^IORC_0037_XFD_SEC_(?!Sub_)[A-Za-z0-9_]+$/).test(n))
      err('orchName', `${path.basename(f)}: name '${n}' doesn't follow IORC_0037_XFD_SEC_${sub ? 'Sub_' : ''}<Description> (letters, digits, underscores)`);
    if (path.basename(f).replace(/\.(sub)?orchestration$/, '') !== n) err('orchName', `${path.basename(f)}: file name differs from the orchestration name '${n}'`);
  }

  // 5d. A template's {{#if x}} needs a Boolean x (App Hub build 2026-11-05: "Actual type of argument (StringType) is not
  // compatible with required type of argument (BooleanType)"). Checks values made by CreateValues steps and sub inputs.
  for (const f of listFiles('orchestration').filter((x) => /\.(orchestration|suborchestration)$/.test(x))) {
    const typeOf = {};
    walk(docs[f] || {}, (node) => {
      if (node._type === 'CreateValues') for (const a of node._value?.values?._value || [])
        typeOf[`${node._value.name?._value}.${a._value?.param?._value?.name?._value}`] = a._value?.param?._value?.type?._value;
      if (node._type === 'StartSubflow') for (const p of node._value?.parameters?._value || [])
        typeOf[`start.${p._value?.name?._value}`] = p._value?.type?._value;
    });
    walk(docs[f] || {}, (node) => {
      if (node._type !== 'TextTemplate' || typeof node._value !== 'string') return;
      for (const m of node._value.matchAll(/\{\{#if data\.([\w.]+)\}\}/g)) {
        const t = typeOf[m[1]];
        if (t && t !== 'Boolean') err('templateIf', `${path.basename(f)}: {{#if data.${m[1]}}} uses a ${t}; App Hub needs a Boolean (make a has<Field> flag with .isEmpty().not())`);
      }
    });
  }

  // 6. Business process routes have matching AMD tasks
  const routes = new Set(Object.values(tasks).map((t) => t.routingPattern));
  for (const f of listFiles('model').filter((x) => x.endsWith('.businessprocess'))) {
    walk(docs[f] || {}, (node) => {
      if (typeof node.pageRoute === 'string' && !routes.has(node.pageRoute)) err('bpRoute', `${path.basename(f)}: pageRoute '${node.pageRoute}' has no AMD task with that routingPattern`);
    });
  }

  // 7. Card rules (both fail the upload)
  for (const [f, d] of Object.entries(cards)) {
    const body = JSON.stringify(Object.fromEntries(Object.entries(d).filter(([k]) => !['id', 'parameters'].includes(k))));
    for (const prm of d.parameters || []) {
      if (!new RegExp(`\\b${prm.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}\\b`).test(body)) err('cardParams', `${path.basename(f)}: parameter '${prm}' is declared but never used`);
    }
    for (const m of body.matchAll(/<%(.*?)%>/g)) {
      if (m[1].includes("'")) { err('cardQuotes', `${path.basename(f)}: single-quoted literal inside <% %> fails tokenization; pass it in as a parameter`); break; }
    }
  }

  // 7b. Business-object collections return 20 rows unless a limit is given (REST default).
  for (const [f, d] of Object.entries(pmds)) {
    for (const e of d.endPoints || []) {
      if (e.baseUrlType === 'BUSINESS-OBJECT' && e.isCollection && !/limit=/.test(String(e.url || ''))) err('restLimit', `${path.basename(f)}: '${e.name}' reads a collection without limit= (only 20 rows come back)`);
    }
  }
  // 7b2. Every grid on a VIEW page offers Excel export; the attribute is for view pages only (developer.workday.com "grid").
  for (const [f, d] of Object.entries(pmds)) {
    const view = (d.presentation?.pageType ?? 'VIEW') === 'VIEW';
    walk(d, (node) => {
      if (node.type !== 'grid') return;
      if (view && !node.excelExportEnabled) err('excelExport', `${path.basename(f)}: grid '${node.id || '?'}' on a VIEW page has no excelExportEnabled`);
      if (!view && node.excelExportEnabled) err('excelExport', `${path.basename(f)}: grid '${node.id || '?'}' sets excelExportEnabled on an EDIT page (view pages only)`);
    });
  }
  // 7b3. UI consistency: one 'nothing to show' message per grid, at most three cards per grid-layout
  //      row (a fourth wraps onto its own row), and every app page titled 'ECO-COMS: ...'.
  const BP_STEP_PAGES = new Set(['reviewRoleRequestDetails', 'reviewRoleRequestApproval', 'reviewRoleRequestSecurityGroup', 'reviewRoleRequestAssignableRole']);
  for (const [f, d] of Object.entries(pmds)) {
    const name = path.basename(f, '.pmd');
    walk(d, (node) => {
      const kids = Array.isArray(node.children) ? node.children : [];
      if (kids.some((c) => c && c.type === 'grid')) {
        const msgs = kids.filter((c) => c && c.visible && ['text', 'richText'].includes(c.type) && /\bno\b|nothing|haven.t/i.test(JSON.stringify(c.value || '')));
        if (msgs.length > 1) err('emptyMsg', `${name}: ${msgs.length} empty-grid messages side by side (${msgs.map((m) => m.id).join(', ')}); keep one`);
      }
      // A grid cell instanceList filled with a literal 'instanceList' renders blank on an EDIT page
      // (seen live on deleteAssignableRole, 2026-10-31); use a text cell or 'values'.
      if (node.type === 'grid' && d.presentation?.pageType === 'EDIT') {
        for (const c of node.columns || []) {
          if (c.cellTemplate?.type === 'instanceList' && c.cellTemplate.instanceList) err('editInstanceList', `${name}: grid '${node.id}' column '${c.columnId}' uses a literal instanceList on an EDIT page; it renders blank`);
        }
      }
      if (node.type === 'fieldSet' && typeof node.title === 'string' && !node.title.includes('<%')) {
        const SMALL = new Set(['a', 'an', 'the', 'and', 'or', 'but', 'of', 'to', 'in', 'on', 'at', 'for', 'by', 'with', 'as', 'vs']);
        const words = node.title.split(' ');
        const bad = words.find((w, i) => { const c = w.replace(/^[("']+|[)"']+$/g, ''); return /^[a-z]+$/.test(c) && !(i > 0 && i < words.length - 1 && SMALL.has(c) && !words[i - 1].endsWith(':')); });
        if (bad) err('headingCase', `${name}: heading "${node.title}" isn't Title Case ("${bad}"); run tools/title_case.py`);
      }
      // A section whose only content can be hidden still draws its box: an empty gap on the page
      // (the 'Requesting again' note, in-platform test 2026-11-01). Put such fields in a box that always shows.
      if (node.type === 'layoutSection' && (node.children || []).length) {
        const leaves = [];
        const collect = (c) => { if (c && c.type === 'fieldSet' && !c.title) (c.children || []).forEach(collect); else leaves.push(c); };
        node.children.forEach(collect);
        if (leaves.length === 1 && typeof leaves[0]?.visible === 'string' && leaves[0].visible.includes('<%')) {
          warn('Static.hiddenSection', `${name}: section '${node.id || '?'}' holds only fields that can be hidden; when they are, an empty box shows`);
        }
      }
      // Workday prints 'n items' next to every grid label, so a count in the label says it twice.
      if (node.type === 'grid' && /\(' \+ size\(|' \(' \+/.test(String(node.label || ''))) {
        err('gridCount', `${name}: grid '${node.id}' puts a count in its label; Workday already shows 'n items' (run tools/polish.py)`);
      }
      if (node.type === 'fieldSet' && String(node.title || '').startsWith('About This')) {
        const first = (node.children || [])[0];
        if (first?.type === 'richText' && typeof first.value === 'string' && !first.value.includes('ⓘ')) err('aboutInfo', `${name}: '${node.title}' text doesn't start with the ⓘ glyph (run tools/polish.py)`);
      }
      if (node.type === 'cardContainer' && (node.layout ?? 'grid') === 'grid' && (node.cards || []).length > 3) {
        err('cardRow', `${name}: cardContainer '${node.id || '?'}' has ${(node.cards || []).length} cards in grid layout; the fourth wraps onto its own row`);
      }
    });
    const title = d.presentation?.title?.label;
    if (title && !BP_STEP_PAGES.has(name) && !/^(<%.*)?'?ECO-COMS: |^<% empty\(queryParams\.appName\) \? 'ECO-COMS: /.test(title) && !title.startsWith('ECO-COMS: ')) {
      err('pageTitle', `${name}: title "${title.slice(0, 60)}" should start with 'ECO-COMS: '`);
    }
  }
  // 7b2. An error OK (onSubmit) sets on a widget the user can't edit (a disabled text, a message line) is never cleared
  // by the user, and Workday refuses OK while any error shows, so the page stays stuck (live 2026-11-04, editAppPattern).
  // Some other handler on the page must clear it (e.g. the onChange of the boxes it's about).
  for (const [f, d] of Object.entries(pmds)) {
    if (typeof d.onSubmit !== 'string') continue;
    const set = [...new Set([...d.onSubmit.matchAll(/(\w+)\.setError\(/g)].map((m) => m[1]))];
    const disabled = new Set();
    walk(d, (node) => { if (node && node.id && node.enabled === false && ['text', 'readOnlyText'].includes(node.type)) disabled.add(node.id); });
    const rest = JSON.stringify({ ...d, onSubmit: '' });
    for (const id of set.filter((x) => disabled.has(x))) {
      if (!rest.includes(id + '.clearError()')) err('stuckError', `${path.basename(f)}: onSubmit sets an error on ${id}, which the user can't edit, and nothing else clears it; OK would stay blocked`);
    }
  }
  // 7c. Only the first richText in a fieldSet renders; the rest are silently dropped.
  for (const [f, d] of Object.entries(pmds)) {
    walk(d, (node) => {
      if (node.type === 'fieldSet' && (node.children || []).filter((c) => c && c.type === 'richText').length > 1) err('richTextPair', `${path.basename(f)}: fieldSet '${node.id || '?'}' has more than one richText; only the first renders`);
    });
  }
  // 7d. Script modules: included files exist, and a page that calls a module includes it.
  const scriptNames = listFiles('presentation/scripts').filter((x) => x.endsWith('.script')).map((x) => path.basename(x, '.script'));
  const usedScripts = new Set();
  for (const [f, d] of Object.entries(pmds)) {
    const inc = (d.include || []).map((x) => x.replace(/\.script$/, ''));
    inc.forEach((x) => usedScripts.add(x));
    for (const x of inc) if (!scriptNames.includes(x)) err('include', `${path.basename(f)}: includes ${x}.script, which doesn't exist`);
    const text = JSON.stringify(Object.fromEntries(Object.entries(d).filter(([k]) => k !== 'include')));
    for (const m of scriptNames) if (new RegExp(`\\b${m}\\.`).test(text) && !inc.includes(m)) err('include', `${path.basename(f)}: calls ${m}.… but doesn't include ${m}.script`);
  }
  for (const m of scriptNames) if (!usedScripts.has(m)) warn('Static.orphan', `presentation/scripts/${m}.script is not included by any page`);
  // 7e. Cards: every cardId exists, and every card is used somewhere (orphans are upload weight).
  const cardIds = new Set(Object.values(cards).map((c) => c.id));
  const usedCards = new Set();
  for (const [f, d] of Object.entries(pmds)) {
    walk(d, (node) => {
      if (typeof node.cardId === 'string' && !node.cardId.includes('<%')) {
        usedCards.add(node.cardId);
        if (!cardIds.has(node.cardId)) err('cardRef', `${path.basename(f)}: cardId '${node.cardId}' has no .card file`);
      }
    });
  }
  // A dynamicCards template may pick its card in a script ("cardId": "<% barCard.cardId %>"): a card id written as a
  // literal in a .script counts as used, and 'Prefix' + n counts every card named Prefix<digits> (Shell Org Manager bar).
  const scriptDir = path.join(ROOT, 'presentation', 'scripts');
  for (const sf of fs.existsSync(scriptDir) ? fs.readdirSync(scriptDir).filter((x) => x.endsWith('.script')) : []) {
    const t = fs.readFileSync(path.join(scriptDir, sf), 'utf8');
    for (const m of t.matchAll(/'([A-Za-z][A-Za-z0-9]*)'/g)) if (cardIds.has(m[1])) usedCards.add(m[1]);
    for (const m of t.matchAll(/'([A-Za-z][A-Za-z0-9]*)' \+ /g)) {
      const fam = [...cardIds].filter((c) => new RegExp(`^${m[1]}\\d+$`).test(c));
      fam.forEach((c) => usedCards.add(c));
    }
  }
  for (const c of cardIds) if (!usedCards.has(c)) warn('Static.orphan', `card ${c} is not used by any page`);
  // 7f. AMD tasks nothing points at (pages count toward the 75-page limit). BP step pages are
  // reached by route, error pages through the SMD.
  const smd = (() => { try { return JSON.parse(fs.readFileSync(path.join(ROOT, AMD_PATH.replace('.amd', '.smd')), 'utf8')); } catch (_) { return {}; } })();
  const reached = new Set(refs.map(([, t]) => t));
  for (const c of smd.errorPageConfigurations || []) reached.add(c.page?.id);
  const bpRoutes = new Set();
  // App Hub build: a card definition may have at most 2 inbound endpoints (build error 2026-11-02)
  for (const f of listFiles('presentation/cards').filter((x) => x.endsWith('.carddefinition'))) {
    const n = (docs[f]?.endPoints || JSON.parse(fs.readFileSync(path.join(ROOT, f), 'utf8')).endPoints || []).length;
    if (n > 2) err('cardEndpoints', `${f} has ${n} inbound endpoints; Workday allows 2 per card`);
  }
  // Workday Script: a helper that calls one defined further down the file is dropped ("Unknown Function call",
  // live 2026-11-02, waitingText -> waitingFor). Define every helper before its first use.
  for (const f of listFiles('presentation/scripts').filter((x) => x.endsWith('.script'))) {
    const src = fs.readFileSync(path.join(ROOT, f), 'utf8').replace(/\/\*[\s\S]*?\*\//g, (c) => c.replace(/[^\n]/g, ' '));
    const defs = [...src.matchAll(/^var\s+(\w+)\s*=\s*function/gm)].map((m) => ({ name: m[1], at: m.index }));
    for (const [i, d] of defs.entries()) {
      const body = src.slice(d.at, i + 1 < defs.length ? defs[i + 1].at : src.length);
      for (const later of defs.slice(i + 1)) {
        if (new RegExp('(^|[^.\\w])' + later.name + '\\s*\\(').test(body)) err('scriptOrder', `${f}: ${d.name} calls ${later.name}, which is defined later in the file`);
      }
    }
  }
  // card tenant settings (cards/*.cardtenantsetting) reach their card task by routePath
  for (const f of listFiles('cards').filter((x) => x.endsWith('.cardtenantsetting'))) { try { bpRoutes.add(JSON.parse(fs.readFileSync(path.join(ROOT, f), 'utf8')).routePath); } catch (_) {} }
  for (const f of listFiles('model').filter((x) => x.endsWith('.businessprocess'))) walk(docs[f] || {}, (n) => { if (typeof n.pageRoute === 'string') bpRoutes.add(n.pageRoute); });
  for (const [tid, t] of Object.entries(tasks)) {
    if (tid === 'home' || reached.has(tid) || reached.has(t.page?.id) || bpRoutes.has(t.routingPattern)) continue;
    warn('Static.orphan', `AMD task '${tid}' is not referenced by any page, card, flow or business process`);
  }

  // 7g. Lookups into capped lists. Workday REST collections (jobs, workers, ...) return 20 rows by
  // default and 100 at most, so filter/find over them silently misses rows (the review pages showed
  // blank Positions this way, 2026-11-01). WQL and paged BO reads are fine.
  for (const [f, d] of Object.entries(pmds)) {
    const raw = JSON.stringify(d);
    for (const e of d.endPoints || []) {
      const bt = String(e.baseUrlType || '');
      if (bt === 'BUSINESS-OBJECT' || bt === 'workday-graph' || /wql/i.test(bt) || bt === 'COMMON' || /orchestr|bp/i.test(bt)) continue;
      if (/limit=(\d{4,})/.test(String(e.url))) continue;
      if (e.name === 'posTreeRoot') continue; // Workday's 6 supervisory-org folders (tools/pos_tree.py), never near the cap
      const re = new RegExp(`\\b${e.name}\\.data\\b[^%]{0,120}?\\.(filter|find)\\(`);
      const m = raw.match(re);
      if (m) {
        // Allowed only as a fallback after stored names (e.g. positionNames) are checked first.
        const before = raw.slice(Math.max(0, m.index - 220), m.index);
        if (!/Names\)\s*\?/.test(before)) warn('Static.cappedLookup', `${f}: ${e.name} (${bt} ${e.url}) is searched with filter/find; REST returns 20-100 rows, so matches beyond that come back blank`);
      }
    }
  }

  // 7g3. Browse pickers (tools/pos_tree.py, tools/unit_tree.py; 2026-11-05). A multilevel instanceList must:
  // read only endpoints that exist, invoke only deferred ones, give its leaves the same id field as its typed search
  // (a browsed pick must save exactly what a searched pick saves), have root values, and say it can be browsed.
  // Every position picker (search over allPositions) should offer the tree.
  for (const [f, d] of Object.entries(pmds)) {
    const eps = new Map((d.endPoints || []).map((e) => [e.name, e]));
    walk(d.presentation || {}, (n) => {
      if (n.type !== 'instanceList') return;
      const search = String(n.searchResultValues || n.onSearch || '');
      const isPos = /posSearch|gridPosSearch/.test(search) || /posSearch|gridPosSearch/.test(String(n.searchEndPoint || ''));
      const lv = n.dynamicMonikerLevels;
      if (!lv) { if (isPos) fail('Static.treePickers', `${f}: position picker ${n.id} has no browse tree (add the page to tools/pos_tree.py)`); return; }
      const label = `${f}: ${n.id}`;
      let ok = true;
      for (const m of String(lv + ' ' + (n.values || '')).matchAll(/\b([A-Za-z]\w*)\.(invoke|data)\b/g)) {
        const e = eps.get(m[1]);
        if (!e) { if (!['self', 'o', 'r', 'first', 'roots'].includes(m[1])) { fail('Static.treePickers', `${label} reads ${m[1]}.${m[2]}, which isn't an endpoint`); ok = false; } continue; }
        if (m[2] === 'invoke' && !(e.deferred === true || e.deferred === 'true')) { fail('Static.treePickers', `${label} invokes ${m[1]}, which isn't deferred`); ok = false; }
      }
      const leaf = [...String(lv).matchAll(/'id': o\.(\w+)/g)].pop();
      const srch = String(search).match(/'id': o\.(\w+)/);
      if (!leaf || !srch) { fail('Static.treePickers', `${label}: can't find the leaf id (${leaf && leaf[1]}) or the search id (${srch && srch[1]})`); ok = false; }
      else if (leaf[1] !== srch[1]) { fail('Static.treePickers', `${label}: browsed leaves use ${leaf[1]} but the typed search uses ${srch[1]}; the page would save different ids`); ok = false; }
      if (/^<%\s*\[\]\s*%>$/.test(String(n.values || '').trim())) { fail('Static.treePickers', `${label}: has levels but empty root values`); ok = false; }
      if (!/Click to browse/.test(String(n.helpText || ''))) { warn('Static.treePickers', `${label}: help text doesn't say it can be browsed`); }
      if (!/return \[[^\]]*, false\]/.test(String(lv))) { fail('Static.treePickers', `${label}: no level returns [list, false] (no selectable leaves)`); ok = false; }
      if (ok) pass('Static.treePickers', `${label}: leaves use ${leaf[1]} like the search; endpoints ok`);
    });
  }

  // 7g6. Calls into an included .script name a function it exports (a typo only fails at run time in Workday).
  {
    const exportsOf = {};
    for (const f of fs.readdirSync(path.join(ROOT, 'presentation/scripts')).filter((x) => x.endsWith('.script'))) {
      const txt = fs.readFileSync(path.join(ROOT, 'presentation/scripts', f), 'utf8');
      const tail = txt.slice(txt.lastIndexOf('{'));
      exportsOf[f.replace('.script', '')] = new Set([...tail.matchAll(/"(\w+)"\s*:/g)].map((m) => m[1]));
    }
    let bad = 0;
    for (const [f, d] of Object.entries(pmds)) {
      const txt = JSON.stringify(d);
      for (const inc of (d.include || [])) {
        const mod = inc.replace('.script', ''); const ex = exportsOf[mod]; if (!ex) continue;
        for (const m of txt.matchAll(new RegExp(mod + '\\.(\\w+)\\(', 'g'))) if (!ex.has(m[1])) { bad++; fail('Static.scriptExports', `${f}: ${mod}.${m[1]} is not exported by ${inc}`); }
      }
    }
    if (!bad) pass('Static.scriptExports', 'every script call names an exported function');
  }

  // 7g5. Brackets in every page script balance (App Hub build 2026-11-05: "PMD Scripting syntax error ... Parsing
  // Error" from a counter missing one ')'). String literals are blanked first.
  for (const [f, d] of Object.entries(pmds)) {
    const seen = new Set();
    walk(d, (n) => {
      if (!n || typeof n !== 'object') return;
      for (const [k, v] of Object.entries(n)) {
        if (typeof v !== 'string' || !v.trim().startsWith('<%')) continue;
        const t = v.replace(/'(?:[^'\\]|\\.)*'/g, "''").replace(/"(?:[^"\\]|\\.)*"/g, '""').replace(/`[^`]*`/g, '``');
        const bad = [['(', ')'], ['{', '}'], ['[', ']']].filter(([o, c]) => t.split(o).length !== t.split(c).length);
        if (bad.length) { const key = `${n.id || n.name || '?'}.${k}`; if (!seen.has(key)) { seen.add(key); fail('Static.scriptBrackets', `${f}: ${key} has unbalanced ${bad.map((b) => b.join('')).join(', ')}`); } }
      }
    });
    if (!seen.size) pass('Static.scriptBrackets', `${f}: brackets balance`);
  }

  // 7g4. A field OK flags must clear its error when the user changes it, or OK stays refused until a reload (found
  // live on Edit Role Assignment 2026-11-05; tools/clear_on_change.py adds the calls on the pages it lists).
  for (const [f, d] of Object.entries(pmds)) {
    const sub = typeof d.onSubmit === 'string' ? d.onSubmit : ''; if (!sub) continue;
    const ids = {}; walk(d.presentation || {}, (n) => { if (n && n.id) ids[n.id] = n; });
    for (const t of new Set([...sub.matchAll(/(\w+)\.setError\(/g)].map((m) => m[1]))) {
      const w = ids[t]; if (!w || w.enabled === false || w.enabled === 'false') continue;
      const oc = String((w.type === 'fileUploader' ? w.onFileAdd : w.onChange) || '');
      if (oc.includes('self.clearError()') || oc.includes(`${t}.clearError()`) || oc.includes('self.setError')) continue;
      warn('Static.clearOnChange', `${f}: OK can flag ${t}, but changing it doesn't clear the error (add the page to tools/clear_on_change.py)`);
    }
  }

  // 7g2. Graph API endpoints (developer.workday.com "Run Graph API Queries on a Page"): POST, a
  // provider in the AMD, a Graph Query component that exists and declares every parameter passed,
  // and guarded reads: a Graph error is HTTP 200 with data.<field> null, so `x.data.r` needs a
  // !empty(x.data) check first.
  {
    const amdDoc = docs[AMD_PATH] || {};
    const providers = new Set((amdDoc.dataProviders || []).map((p) => p.key));
    const gqs = {};
    for (const f of listFiles('presentation/graphQueries').filter((x) => x.endsWith('.graphquery'))) {
      try { const q = JSON.parse(fs.readFileSync(path.join(ROOT, f), 'utf8')); gqs[q.id] = q;
        if (path.basename(f, '.graphquery') !== q.id) err('graphQuery', `${f}: id "${q.id}" must match the file name`, f);
        if (/<%/.test(q.query || '')) err('graphQuery', `${f}: the query string can't contain PMD script; pass values through variables`, f);
        for (const prm of q.parameters || []) if (!JSON.stringify(q.variables || {}).includes(prm)) err('graphQuery', `${f}: parameter "${prm}" isn't used in variables`, f);
      } catch (e) { err('graphQuery', `${f}: ${e.message}`, f); }
    }
    for (const [f, d] of Object.entries(pmds)) {
      const raw = JSON.stringify(d);
      for (const e of d.endPoints || []) {
        if (!e.graphQuery) continue;
        if (String(e.httpMethod).toUpperCase() !== 'POST') err('graphQuery', `${f}: ${e.name} must use httpMethod POST`, f);
        if (!providers.has(e.baseUrlType)) err('graphQuery', `${f}: ${e.name} uses provider "${e.baseUrlType}", not in the AMD`, f);
        const q = e.graphQuery.queryId && gqs[e.graphQuery.queryId];
        if (e.graphQuery.queryId && !q) err('graphQuery', `${f}: ${e.name} references missing Graph Query "${e.graphQuery.queryId}"`, f);
        if (q) for (const k of Object.keys(e.graphQuery.parameters || {})) if (!(q.parameters || []).includes(k)) err('graphQuery', `${f}: ${e.name} passes "${k}", which ${q.id} doesn't declare`, f);
        const unguarded = raw.split(`${e.name}.data.`).length - 1 - (raw.split(`!empty(${e.name}.data)`).length - 1) * 2;
        if (unguarded > 0) err('graphQuery', `${f}: ${e.name}.data.<field> is read without a !empty(${e.name}.data) guard`, f);
      }
    }
  }

  // 7g3. Excel export: a fieldSet cell can't be exported on its own; the whole export then fails with
  // "no exporter found for widget ...StandardFieldSet" (Audit Log, 2026-11-04). Give it an excel value.
  for (const [f, d] of Object.entries(pmds)) {
    walk(d, (n) => {
      if (n.type !== 'grid' || !(n.excelExportEnabled === true || n.excelExportEnabled === 'true')) return;
      for (const c of n.columns || []) {
        if (c.cellTemplate?.type === 'fieldSet' && !(c.excel && (c.excel.value || c.excel.enabled === false)))
          err('excelFieldSet', `${f}: grid ${n.id} column ${c.columnId} is a fieldSet with no excel value or excel.enabled false; Excel export fails`, f);
      }
    });
  }

  // 7h. Application pattern schemas (tools/pattern_schemas.json): regexes compile, spreadsheet examples
  // build the expected names and pass, invalid examples fail, and hints never contain the "fieldLabel"
  // marker that IORC_0037_XFD_SEC_Create_Pattern_Shell_Org counts to know the number of fields.
  try {
    const f = JSON.parse(fs.readFileSync(path.join(ROOT, 'tools', 'pattern_schemas.json'), 'utf8'));
    let n = 0;
    for (const a of f.applications) {
      const fields = a.fields || f.fieldSets[a.fieldsFrom];
      if (!fields || !fields.length || fields.length > 7) { err('schema', `${a.appId}: needs 1 to 7 fields`); continue; }
      if (!/^X:[A-Z0-9()]+$/.test(a.appId)) err('schema', `${a.appId}: application code must be X:CODE`);
      for (const x of fields) {
        if (JSON.stringify(x).replace('"fieldLabel"', '').includes('fieldLabel')) err('schema', `${a.appId}: "fieldLabel" must appear once per field`);
        try { new RegExp(`^(?:${x.regex})$`); } catch (e) { err('schema', `${a.appId} ${x.fieldLabel}: bad regex ${x.regex}`); }
      }
      const ok = (x, v) => (v === '' ? x.blankIsWildcard : new RegExp(`^(?:${x.regex})$`).test(v));
      for (const ex of a.examples || []) {
        const bad = fields.filter((x, i) => !ok(x, ex.values[i] ?? ''));
        const name = `${a.appId}:${ex.prefix || a.prefixes[0]}:${fields.map((x, i) => ex.values[i] || '*').join(':')}`;
        if (bad.length) err('schema', `${a.appId}: example ${ex.name} fails ${bad.map((x) => x.fieldLabel).join(', ')}`);
        if (name !== ex.name) err('schema', `${a.appId}: example builds ${name}, expected ${ex.name}`);
        n++;
      }
      for (const iv of a.invalid || []) {
        if (fields.every((x, i) => ok(x, iv.values[i] ?? ''))) err('schema', `${a.appId}: invalid example ${JSON.stringify(iv.values)} passes (${iv.why})`);
        n++;
      }
    }
    pass('Static.schemas', `${f.applications.length} application schemas, ${n} examples checked`);
  } catch (e) { err('schema', `tools/pattern_schemas.json: ${e.message}`); }

  // 7i. Load-time scripts (value, label, visible, rows, ...) can't use a widget declared later on the
  // page: "Unknown Variable found: x.value" (newSchemaPattern preview, 2026-11-02). Event handlers
  // (onChange, onSubmit, onSearch, ...) run after the page is built, so they may.
  for (const [f, d] of Object.entries(pmds)) {
    const ids = []; const allIds = new Set();
    walk(d.presentation || {}, (n) => { if (n && typeof n.id === 'string') allIds.add(n.id); });
    const visit = (n) => {
      if (Array.isArray(n)) return n.forEach(visit);
      if (!n || typeof n !== 'object') return;
      if (typeof n.id === 'string') ids.push(n.id);
      for (const [k, v] of Object.entries(n)) {
        if (/^on[A-Z]/.test(k)) continue;
        if (typeof v === 'string' && v.includes('<%')) {
          for (const m of v.matchAll(/\b([a-z][A-Za-z0-9]*)\.(value|selectedEntries|rows|childrenMap)\b/g)) {
            if (allIds.has(m[1]) && !ids.includes(m[1]) && m[1] !== n.id) warn('Static.forwardRef', `${f}: ${n.id || n.type} ${k} uses ${m[1]}, declared later on the page: fails if evaluated at page load (guard it so it isn't)`);
          }
        } else visit(v);
      }
    };
    visit(d.presentation || {});
  }

  // 8. No forbidden test text in anything shipped to the tenant (CLAUDE.md "Test data in the tenant")
  const forbidden = new RegExp(['cl', 'aude'].join(''), 'i');
  for (const f of [...listFiles('presentation', true), ...listFiles('model'), ...listFiles('orchestration')]) {
    if (forbidden.test(fs.readFileSync(path.join(ROOT, f), 'utf8'))) err('testText', `${f}: contains forbidden test text`);
  }

  // 9. Inbound endpoints should fail loudly (warning only). Exception, decided 2026-11-05: the browse-tree lists are
  // extras beside the typed search, so a failure must leave an empty tree, not a broken page. They must stay
  // bestEffort and keep no failOnStatusCodes (CLAUDE.md "failOnStatusCodes": be deliberate on side lists).
  const QUIET_OK = new Set(['posTreeRoot', 'fuhTreeAll', 'auTreeAll']);
  let quiet = 0;
  for (const [f, d] of Object.entries(pmds)) {
    walk(d, (node, pk) => {
      if (pk !== 'endPoints' || !('baseUrlType' in node) || node.deferred) return;
      if (QUIET_OK.has(node.name)) {
        if (!(node.bestEffort === true || node.bestEffort === 'true')) fail('Static.failOnStatusCodes', `${f}: ${node.name} is an optional browse list and must be bestEffort`);
        if ('failOnStatusCodes' in node) warn('Static.failOnStatusCodes', `${f}: ${node.name} is an optional browse list; a listed code would fail the whole page`);
        return;
      }
      if (!('failOnStatusCodes' in node)) quiet++;
    });
  }
  if (quiet) warn('Static.failOnStatusCodes', `${quiet} inbound endpoint(s) have no failOnStatusCodes (errors are swallowed)`);
  else pass('Static.failOnStatusCodes', 'every eager endpoint fails loudly, apart from the optional browse lists');

  // 9b. Widget method calls name a widget on the page (an unknown id fails the page at run time:
  //     "Unknown Variable found: changesText", Bulk Edit, 2026-11-03)
  {
    const METHODS = 'setError|clearError|setWarning|clearWarning|setValue|setValues|setVisible|setEnabled|setRequired|setLabel|getValue|isVisible|isEnabled';
    for (const [f, d] of Object.entries(pmds)) {
      const ids = new Set();
      walk(d, (node) => { if (typeof node.id === 'string') ids.add(node.id); });
      const text = JSON.stringify(d);
      const seen = new Set();
      for (const m of text.matchAll(new RegExp(`(?<![\\w.'"])([a-z][A-Za-z0-9]*)\\.(?:${METHODS})\\(`, 'g'))) {
        const name = m[1];
        if (name === 'self' || ids.has(name) || seen.has(name)) continue;
        seen.add(name);
        err('widgetRef', `${f}: script calls ${name}.${m[0].split('.')[1]} but no widget on the page has id '${name}'`, f);
      }
    }
  }

  // 9c. Every onSubmit clears each widget it flags before checking (an error it set stays after the
  //     user fixes the cause, and OK keeps failing until a reload)
  for (const [f, d] of Object.entries(pmds)) {
    const sub = typeof d.onSubmit === 'string' ? d.onSubmit : (d.presentation || {}).onSubmit;
    if (typeof sub !== 'string' || !sub.includes('setError(')) continue;
    const first = sub.indexOf('setError(');
    const flagged = [...new Set([...sub.matchAll(/\b([a-zA-Z][A-Za-z0-9]*)\.setError\(/g)].map((m) => m[1]))].filter((w) => w !== 'self');
    const cleared = new Set([...sub.slice(0, first).matchAll(/\b([a-zA-Z][A-Za-z0-9]*)\.clearError\(\)/g)].map((m) => m[1]));
    const miss = flagged.filter((w) => !cleared.has(w));
    if (miss.length) err('submitClears', `${f}: onSubmit flags ${miss.join(', ')} without clearing it first (run tools/clear_submit_errors.py)`, f);
  }

  // 10. Icons are from Workday's list (developer.workday.com "Reference: Icons"); hub navigation items take wd-icon-* only
  {
    const src = fs.readFileSync(path.join(ROOT, 'tools/apply_icons.py'), 'utf8');
    const grab = (name) => new Set(src.match(new RegExp(`${name} = set\\("""([\\s\\S]*?)"""`))[1].split(/\s+/).filter(Boolean));
    const ACCENT = grab('ACCENT'), NAV = grab('NAV');
    const iconFiles = [...Object.keys(pmds), ...Object.keys(cards),
      ...listFiles('presentation/cards').filter((f) => f.endsWith('.carddefinition'))];
    for (const f of iconFiles) {
      const d = docs[f] || JSON.parse(fs.readFileSync(path.join(ROOT, f), 'utf8'));
      walk(d, (node) => {
        const icon = node.icon;
        if (typeof icon !== 'string' || icon.includes('<%')) return;
        if (node.type === 'item' || node.type === 'group') {
          if (!icon.startsWith('wd-icon-') || !NAV.has(icon.slice(8))) err('icons', `${f}: navigation item '${node.label}' icon ${icon} isn't a wd-icon-* navigation icon`, f);
        } else if (!icon.startsWith('wd-accent-') || !ACCENT.has(icon.slice(10))) {
          err('icons', `${f}: icon ${icon} isn't in Workday's wd-accent-* list`, f);
        }
      });
    }
  }

  if (!errs.length) pass('Static', `${Object.keys(docs).length} JSON components, ${Object.keys(pmds).length} pages, ${Object.keys(tasks).length} AMD tasks, ${orchNames.size} orchestrations, ${Object.keys(cards).length} cards checked`);
  return { pmds };
}

// ISU static check: audit and request writes go through the ISU, so users can be view-only.
// Part of the isu suite only, because it fails until the ISU branch is merged.
function isuStaticCheck() {
  const pmds = Object.fromEntries(listFiles('presentation').filter((f) => f.endsWith('.pmd'))
    .map((f) => [f, JSON.parse(fs.readFileSync(path.join(ROOT, f), 'utf8'))]));
  const smd = listFiles('presentation').find((f) => f.endsWith('.smd'));
  const auth = smd ? JSON.parse(fs.readFileSync(path.join(ROOT, smd), 'utf8'))?.siteAuth?.authTypes || [] : [];
  const bad = [];
  for (const [f, d] of Object.entries(pmds)) {
    for (const e of (d.outboundData || {}).outboundEndPoints || []) {
      const u = String(e.url || '');
      if (e.baseUrlType === 'BUSINESS-OBJECT' && /comsAuditLogs|comsAssignableRoles/.test(u) && e.authType !== 'isuAuth') bad.push(`${path.basename(f)}:${e.name}`);
    }
  }
  if (!auth.some((a) => a.id === 'isuAuth')) throw new Error('the SMD defines no isuAuth auth type');
  if (bad.length) throw new Error(`${bad.length} audit/request write(s) still run as the user, e.g. ${bad[0]} (set authType "isuAuth")`);
  pass('ISU.writesUseIsu', 'every page write to comsAuditLogs / comsAssignableRoles uses isuAuth');
}

// ═══ Live suites: shared helpers ═══════════════════════════════════════════════
// ─── Token ────────────────────────────────────────────────────────────────────
function resolveToken() {
  if (arg('--token')) return arg('--token');
  if (process.env.WD_DEV_TOKEN) return process.env.WD_DEV_TOKEN;
  try {
    const cfg = JSON.parse(fs.readFileSync(path.join(os.homedir(), '.config', '@workday', 'wdcli', 'config.json'), 'utf8'));
    return cfg?.wcpTenantAccessToken?.[TENANT] || null;
  } catch (_) { return null; }
}

// ─── HTTP ─────────────────────────────────────────────────────────────────────
let lastHeaders = {};
function request(method, url, token, body) {
  return new Promise((resolve, reject) => {
    const u = new URL(url);
    const data = body === undefined ? null : JSON.stringify(body);
    const r = https.request({
      hostname: u.hostname, path: u.pathname + u.search, method,
      headers: {
        Authorization: `Bearer ${token}`, Accept: 'application/json',
        ...(data !== null ? { 'Content-Type': 'application/json', 'Content-Length': Buffer.byteLength(data) } : {}),
      },
      timeout: 60000,
    }, (res) => {
      let raw = '';
      res.on('data', (d) => { raw += d; });
      res.on('end', () => {
        if (VERBOSE) console.log(`    ${method} ${u.pathname} -> ${res.statusCode}`);
        lastHeaders = res.headers;
        if (res.statusCode >= 400) return reject(new Error(`HTTP ${res.statusCode} ${u.pathname}: ${raw.slice(0, 200)}`));
        try { resolve(JSON.parse(raw)); } catch (_) { resolve(raw); }
      });
    });
    r.on('timeout', () => r.destroy(new Error(`timeout ${u.pathname}`)));
    r.on('error', reject);
    if (data !== null) r.write(data);
    r.end();
  });
}
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

// Every record of a business-object collection. The REST API returns 100 rows at most per call,
// oldest first, so a single ?limit=100 read misses the newest records once there are more than 100.
async function readAll(token, collection, max = 3000) {
  const out = [];
  for (let offset = 0; offset < max; offset += 100) {
    const page = await request('GET', `${BO}/${collection}?limit=100&offset=${offset}`, token);
    out.push(...(page.data || []));
    if ((page.data || []).length < 100 || out.length >= (page.total ?? 0)) break;
  }
  return out;
}

// ─── Helpers ──────────────────────────────────────────────────────────────────
const wql = (token, query, limit = 100) =>
  request('GET', `${WQL}?limit=${limit}&query=${encodeURIComponent(query)}`, token);
// IORC_0037_XFD_SEC_Change_Shell_Org_Status picks inactivate vs reactivate from includeInactive ("true" = inactivate),
// not from action; action is only written to the audit record. Send both, as the page does.
// Encode like the pages' .urlEncode() (Java URLEncoder: space as +, only A-Z a-z 0-9 . - * _ left as is).
// The API gateway refused (HTML 403) some test launches that the same change sent from a page passed.
const formEncode = (v) => encodeURIComponent(String(v ?? '')).replace(/[!'()~]/g, (c) => '%' + c.charCodeAt(0).toString(16).toUpperCase()).replace(/%20/g, '+');
const launch = (token, name, params) => {
  const qs = Object.entries(params).map(([k, v]) => `${k}=${formEncode(v)}`).join('&');
  return request('POST', `${ORCH}/${name}/launch?${qs}`, token, {});
};
// Same check the pages use (run-and-verify): the orchestration writes an audit record only
// after Workday accepts the change, so a +1 audit total means the call really worked.
async function launchAndVerify(token, name, params) {
  const ids = async () => (await readAll(token, 'comsAuditLogs'));
  const before = new Set((await ids()).map((a) => a.id));
  await launch(token, name, params);
  const launchId = lastHeaders['x-orchestrate-id'] || null;
  for (let i = 0; i < 10; i++) {
    await sleep(2000);
    // Match the new record by id: timestamps can tie, so "newest" is not reliable.
    const fresh = (await ids()).filter((a) => !before.has(a.id));
    if (fresh.length) return Object.assign(fresh[0], { _launchId: launchId });
  }
  throw new Error(`${name}: no new audit record after 20 s (Workday rejected the call or the orchestration failed; check app Logs)`);
}

// The guard in IORC_0037_XFD_SEC_Change_Shell_Org_Status must reject the call: no audit record may appear.
async function expectRejected(token, name, params) {
  const before = new Set((await readAll(token, 'comsAuditLogs')).map((a) => a.id));
  await launch(token, name, params);
  await sleep(20000);
  const fresh = (await readAll(token, 'comsAuditLogs')).filter((a) => !before.has(a.id));
  if (fresh.length) throw new Error(`${name} accepted a call it should reject (audit ${fresh[0].objectType}/${fresh[0].action})`);
}

// ═══ Smoke suite (read-only) ═══ ──────────────────────────────────────────────────
async function smoke(token, me) {
  console.log('\n-- Smoke (read-only) --');

  for (const c of BO_COLLECTIONS) {
    await test(`BO.${c}`, async () => {
      const r = await request('GET', `${BO}/${c}?limit=1`, token);
      if (!Array.isArray(r.data)) throw new Error('response has no data array');
      pass(`BO.${c}`, `readable (total ${r.total ?? '?'})`);
    });
  }

  // Every parameter-free WQL component the pages load must still run.
  const dir = path.join(__dirname, '..', 'presentation', 'wqlQueries');
  for (const f of fs.readdirSync(dir).filter((x) => x.endsWith('.wqlquery')).sort()) {
    const q = JSON.parse(fs.readFileSync(path.join(dir, f), 'utf8'));
    const name = `WQL.${q.id || f}`;
    if ((q.parameters || []).length || /<%/.test(q.query)) { skip(name, 'takes parameters'); continue; }
    await test(name, async () => {
      const r = await wql(token, q.query.replace(/\s+/g, ' ').trim(), 1);
      if (!Array.isArray(r.data)) throw new Error('response has no data array');
      pass(name, `runs (total ${r.total ?? r.data.length})`);
    });
  }

  await test('WQL.shellOrgsExist', async () => {
    const r = await wql(token, "SELECT workdayID, code FROM topLevelOrganizations WHERE code contains 'X:'", 1);
    if (!(r.total > 0 || (r.data || []).length > 0)) throw new Error('no X: shell organizations returned');
    pass('WQL.shellOrgsExist', `shell orgs found (total ${r.total ?? '>0'})`);
  });

  // Pages call WQL without a limit. If Workday's default page is smaller than the data, lists and
  // lookups are cut off silently: compare rows returned with no limit against the total.
  await test('WQL.noLimitReturnsAll', async () => {
    const q = "SELECT workdayID, code FROM topLevelOrganizations WHERE code contains 'X:'";
    const r = await request('GET', `${WQL}?query=${encodeURIComponent(q)}`, token);
    const n = (r.data || []).length;
    const p = await request('GET', `${WQL}?query=${encodeURIComponent('SELECT cf_PositionID FROM allPositions WHERE supervisoryOrganization is not empty')}`, token);
    const msg = `no limit: shell orgs ${n} of ${r.total}, positions ${(p.data || []).length} of ${p.total}`;
    if (n < (r.total ?? n) || (p.data || []).length < (p.total ?? 0)) throw new Error(`${msg}: pages that omit limit see only part of the data`);
    pass('WQL.noLimitReturnsAll', msg);
  });

  let audits = [];
  await test('Audit.read', async () => {
    audits = await readAll(token, 'comsAuditLogs');
    pass('Audit.read', `${audits.length} recent records`);
  });
  // Pages read business-object collections 100 rows at a time. These report the totals, the order
  // the API returns rows in, and whether the offset pages line up, so the pages can be sized right.
  await test('Audit.volume', async () => {
    const one = await request('GET', `${BO}/comsAuditLogs?limit=1`, token);
    const total = one.total ?? 0;
    const first = audits[0]?.timestamp || '', last = audits[audits.length - 1]?.timestamp || '';
    const order = !first || !last || first === last ? 'unknown' : (first < last ? 'oldest first' : 'newest first');
    let page2 = '';
    if (total > 100) {
      const p2 = (await request('GET', `${BO}/comsAuditLogs?limit=100&offset=100`, token)).data || [];
      const overlap = p2.filter((a) => audits.slice(0, 100).some((b) => b.id === a.id)).length;
      page2 = `; offset=100 gave ${p2.length} rows, ${overlap} repeated from the first page`;
    }
    // The viewer asks for offset=total when a page has nothing left to load: that must come back empty.
    const past = ((await request('GET', `${BO}/comsAuditLogs?limit=1&offset=${total}`, token)).data || []).length;
    if (past) throw new Error(`offset=${total} (past the end) returned ${past} row(s); the Audit Log Viewer would show a duplicate`);
    const msg = `${total} audit records in total; the API returns them ${order}${page2}; offset past the end is empty`;
    if (total > 500) warn('Audit.volume', `${msg}. The Audit Log Viewer loads 500 rows`); else pass('Audit.volume', msg);
  });
  await test('Audit.vocabulary', async () => {
    const bad = audits.filter((a) => !OBJECT_TYPES.includes(a.objectType) || !ACTIONS.includes(a.action));
    if (bad.length) throw new Error(`${bad.length} record(s) outside the fixed vocabulary, e.g. ${JSON.stringify({ objectType: bad[0].objectType, action: bad[0].action })}`);
    pass('Audit.vocabulary', 'all objectType/action values are in the fixed vocabulary');
  });
  await test('Audit.positionFullName', async () => {
    const ra = audits.filter((a) => a.objectType === 'Role Assignment');
    if (!ra.length) return skip('Audit.positionFullName', 'no role assignment audit records');
    const bare = ra.filter((a) => /^P-\d+$/.test(String(a.positionName || '').trim()) || !String(a.positionName || '').trim());
    if (bare.length) throw new Error(`${bare.length} role assignment record(s) show only a position ID or nothing, e.g. ${bare[0].id} "${bare[0].positionName || ''}"`);
    pass('Audit.positionFullName', `${ra.length} role assignment record(s) show the full position name`);
  });
  await test('Audit.requiredFields', async () => {
    const bad = audits.filter((a) => !a.timestamp || !a.objectType || !a.action);
    if (bad.length) throw new Error(`${bad.length} record(s) missing timestamp/objectType/action`);
    pass('Audit.requiredFields', 'timestamp, objectType and action present on all');
  });

  // Orchestrations store their run ID on every audit record from 2026-11-05 on (tools/audit_run_id.py).
  // Pages that write their own record have no run: Application Patterns, Access Review, Delete and Approve Assignable Role.
  const PAGE_WRITTEN = (a) => a.objectType === 'Application Pattern' || a.action === 'REVIEW'
    || (a.objectType === 'Assignable Role' && ['DELETE', 'APPROVE'].includes(a.action));
  await test('Audit.runId', async () => {
    const since = '2026-11-05';
    const recent = audits.filter((a) => String(a.timestamp || '') >= since && !PAGE_WRITTEN(a));
    if (!recent.length) return skip('Audit.runId', `no audit records since ${since} yet`);
    const missing = recent.filter((a) => !a.runId);
    (missing.length ? fail : pass)('Audit.runId', `${recent.length - missing.length} of ${recent.length} record(s) since ${since} carry a run ID` + (missing.length ? `; missing on ${missing.slice(0, 3).map((a) => a.objectType + ' ' + a.action + ' ' + a.timestamp).join(', ')}` : ''));
  });

  // Application pattern formats are edited in the app (editAppPattern, 2026-11-04): every saved one must still be usable
  // by the Add Pattern form (prefixes, 1-7 fields, each example matching its format; regex checked in JS, close to Java).
  await test('Apps.patternFormats', async () => {
    const apps = (await request('GET', `${BO}/comsApplications?limit=100`, token)).data || [];
    const bad = [];
    for (const a of apps.filter((x) => x.patternSchema)) {
      let s; try { s = JSON.parse(a.patternSchema); } catch (e) { bad.push(`${a.appId}: patternSchema isn't JSON`); continue; }
      if (!Array.isArray(s.prefixes) || !s.prefixes.length) bad.push(`${a.appId}: no prefixes`);
      if (!Array.isArray(s.fields) || !s.fields.length || s.fields.length > 7) bad.push(`${a.appId}: ${s.fields?.length ?? 0} fields (1-7 allowed)`);
      (s.fields || []).forEach((f, i) => {
        let ok = false; try { ok = new RegExp('^(?:' + f.regex + ')$').test(f.example); } catch (e) { bad.push(`${a.appId} field ${i + 1}: format isn't a valid regex`); return; }
        if (!f.fieldLabel || !ok) bad.push(`${a.appId} field ${i + 1} (${f.fieldLabel || 'no label'}): example ${f.example} doesn't match ${f.regex}`);
      });
      if ((a.namePrefix || '') !== (s.prefixes || []).join(',')) bad.push(`${a.appId}: namePrefix ${a.namePrefix} differs from the format's prefixes`);
    }
    if (bad.length) throw new Error(bad.slice(0, 5).join('; '));
    pass('Apps.patternFormats', `${apps.filter((x) => x.patternSchema).length} application formats valid`);
  });

  // Access Review lists vacant positions that still hold a shell role (tools/build_access_review.py): the same two
  // queries the page makes, so a 0 on the page can be told apart from a broken filter.
  await test('AccessReview.vacant', async () => {
    const pos = (await wql(token, 'SELECT cf_PositionID, cf_PositionIsFilled FROM allPositions WHERE supervisoryOrganization is not empty', 10000)).data || [];
    const vacant = new Set(pos.filter((p) => p.cf_PositionIsFilled === false).map((p) => String(p.cf_PositionID || '')));
    const q = JSON.parse(fs.readFileSync(path.join(ROOT, 'presentation/wqlQueries/allShellAssignableRolesinTenant.wqlquery'), 'utf8')).query;
    const roles = (await wql(token, q, 1000)).data || [];
    const held = roles.flatMap((r) => (r.roleAssignments || []).flatMap((ra) => (ra.cf_ZCF_EE_RoleAssignedToAsPositionRestrictions || []).map((p) => ({ role: r.role?.descriptor, pos: p.descriptor || '' }))));
    const rows = held.filter((h) => vacant.has(h.pos.split(' ')[0]));
    const sample = pos.slice(0, 2).map((p) => JSON.stringify(p)).join(' ');
    if (!pos.length) throw new Error('allPositions returned no positions');
    if (!pos.some((p) => typeof p.cf_PositionIsFilled === 'boolean')) throw new Error(`cf_PositionIsFilled isn't a boolean: ${sample}`);
    pass('AccessReview.vacant', `${pos.length} positions, ${vacant.size} vacant; ${held.length} shell-role assignments, ${rows.length} on vacant positions` +
      (rows.length ? ` (e.g. ${rows[0].role} on ${rows[0].pos})` : '') + `; sample ${sample}`);
  });

  let roles = [];
  await test('Requests.read', async () => {
    roles = await readAll(token, 'comsAssignableRoles');
    pass('Requests.read', `${roles.length} role requests`);
  });
  await test('Requests.deniedInactive', async () => {
    const bad = roles.filter((r) => r.status === 'Denied' && r.active !== false);
    if (bad.length) throw new Error(`${bad.length} Denied request(s) still active, e.g. ${bad[0].roleName}`);
    pass('Requests.deniedInactive', 'every Denied request is inactive (IORC_0037_XFD_SEC_Close_Denied_Role_Request orchestration)');
  });
  await test('Requests.approvedHaveGroup', async () => {
    // TESTROLE1033 was approved before securityGroupName existed and can't be deleted (linked to its review event).
    const LEGACY = ['2ea70ec010b490020488f73e422e0000'];
    const bad = roles.filter((r) => r.status === 'Approved' && r.reviewEventWid && !r.securityGroupName && !LEGACY.includes(r.id));
    if (bad.length) throw new Error(`${bad.length} BP-approved request(s) with no securityGroupName, e.g. ${bad[0].roleName}`);
    pass('Requests.approvedHaveGroup', 'BP-approved requests record their security group');
  });
  // Tamper check: a request's status must match how its Workday review event ended.
  // Catches a status changed outside the business process (e.g. a direct API PATCH).
  await test('BP.statusMatchesEvent', async () => {
    const closed = roles.filter((r) => ['Approved', 'Denied'].includes(r.status) && r.reviewEventWid).slice(0, 25);
    if (!closed.length) return skip('BP.statusMatchesEvent', 'no Approved/Denied requests with a review event');
    let checked = 0;
    for (const r of closed) {
      const ev = await request('GET', `${BP}/events/${r.reviewEventWid}`, token);
      const st = String(ev?.status?.descriptor || ev?.overallStatus?.descriptor || '');
      if (!st) continue;
      checked++;
      const ok = r.status === 'Approved' ? /complete/i.test(st) && !/denied|cancel|rescind|terminat/i.test(st) : /denied|cancel|rescind|terminat/i.test(st);
      if (!ok) throw new Error(`${r.roleName} is ${r.status} in ECO-COMS but its review event is "${st}"`);
    }
    if (!checked) return skip('BP.statusMatchesEvent', 'review event status not readable from the BP API');
    pass('BP.statusMatchesEvent', `${checked} closed request(s) match their review event outcome`);
  });

  await test('Requests.pendingHavePositions', async () => {
    const pending = roles.filter((r) => r.status === 'Pending ISC Review');
    if (!pending.length) return skip('Requests.pendingHavePositions', 'no pending requests');
    const bad = pending.filter((r) => !(r.positions || r.positionWids) || !r.positionNames);
    if (bad.length) throw new Error(`${bad.length} pending request(s) without positions or position names, e.g. ${bad[0].roleName}`);
    pass('Requests.pendingHavePositions', `${pending.length} pending request(s) carry positions and their names`);
  });

  await test('Requests.pendingEnabledFor', async () => {
    const pending = roles.filter((r) => r.status === 'Pending ISC Review');
    if (!pending.length) return skip('Requests.pendingEnabledFor', 'no pending requests');
    // Enabled For is display text: a unit name, never empty and never a bare WID.
    const bad = pending.filter((r) => !r.enabledForOrganizationTypes || /^[0-9a-f]{32}$/.test(r.enabledForOrganizationTypes));
    if (bad.length) throw new Error(`${bad.length} pending request(s) with Enabled For "${bad[0].enabledForOrganizationTypes || ''}", e.g. ${bad[0].roleName}`);
    pass('Requests.pendingEnabledFor', `${pending.length} pending request(s) show an Enabled For name`);
  });

  await test('Requests.volume', async () => {
    const total = (await request('GET', `${BO}/comsAssignableRoles?limit=1`, token)).total ?? 0;
    const msg = `${total} assignable role requests in total`;
    if (total > 100) warn('Requests.volume', `${msg}; pages load the first 100 only`); else pass('Requests.volume', msg);
  });
  // The legacy Maintain page is only needed for pending requests that have no review event.
  await test('Requests.pendingHaveEvent', async () => {
    const legacy = roles.filter((r) => r.status === 'Pending ISC Review' && !r.reviewEventWid);
    if (legacy.length) return warn('Requests.pendingHaveEvent', `${legacy.length} pending request(s) without a review event (only the legacy Maintain page can act on them): ${legacy.map((r) => r.roleName).join(', ')}`);
    pass('Requests.pendingHaveEvent', 'every pending request has a review event');
  });
  // Shape of an event's comments (GET events/{id}/comments), used to copy the Deny comment into the request.
  await test('BP.eventComments', async () => {
    const closed = roles.filter((r) => r.status === 'Denied' && r.reviewEventWid).slice(-1)[0];
    if (!closed) return skip('BP.eventComments', 'no denied request with a review event');
    const c = await request('GET', `${BP}/events/${closed.reviewEventWid}/comments`, token);
    const first = (c.data || [])[0];
    pass('BP.eventComments', `${(c.data || []).length} comment(s) on ${closed.roleName}; first: ${JSON.stringify(first || {}).slice(0, 300)}`);
  });
  await test('BP.pendingEventsOpen', async () => {
    const pending = roles.filter((r) => r.status === 'Pending ISC Review' && r.reviewEventWid).slice(0, 5);
    if (!pending.length) return skip('BP.pendingEventsOpen', 'no pending requests with a review event');
    for (const r of pending) {
      const ev = await request('GET', `${BP}/events/${r.reviewEventWid}`, token);
      const status = ev?.status?.descriptor || ev?.overallStatus?.descriptor || '';
      if (/denied|cancel|rescind|terminat/i.test(status)) throw new Error(`${r.roleName} is Pending in ECO-COMS but its review event is ${status}`);
    }
    pass('BP.pendingEventsOpen', `${pending.length} pending request(s) have an open review event`);
  });
  // The step pages (Link Workday Role) open from an inbox item with an event step id. Print one for a
  // pending TEST request so the page can be loaded in-platform without a real request (read-only:
  // developer.workday.com "Event Steps REST APIs", GET /events/{id}/inProgressSteps).
  await test('BP.inProgressStep', async () => {
    const r = roles.filter((x) => x.status === 'Pending ISC Review' && x.reviewEventWid && /TEST/.test(x.roleName || '')).slice(-1)[0];
    if (!r) return skip('BP.inProgressStep', 'no pending TEST request with a review event');
    const s = await request('GET', `${BP}/events/${r.reviewEventWid}/inProgressSteps`, token);
    const step = (s.data || [])[0];
    if (!step?.id) throw new Error(`no in-progress step on ${r.roleName}'s review event`);
    pass('BP.inProgressStep', `${r.roleName}: step "${step.descriptor || step.stepType?.descriptor || '?'}" id ${step.id} (open reviewRoleRequestAssignableRole/${step.id} to test the step page)`);
  });
  // Workday Home card data (tools/build_home_cards.py): synchronous, read-only orchestrations that return the
  // card's title, subtitle and link. Compare their counts with the same counts worked out here.
  const card = async (name) => {
    const r = await launch(token, name, {});
    let c = r;
    if (typeof r === 'string') { try { c = JSON.parse(r); } catch (_) { throw new Error(`${name}: launch returned text, not the card JSON: ${r.slice(0, 300)}`); } }
    for (const k of ['title', 'subtitle', 'linkText', 'linkPath']) if (typeof c?.[k] !== 'string' || !c[k]) throw new Error(`${name}: no ${k} in ${JSON.stringify(r).slice(0, 300)}`);
    if (!/^\/[^/]+\/d\/wday\/app\/[^/]+\/[^/]+\/[A-Za-z]+\.htmld$/.test(c.linkPath)) throw new Error(`${name}: odd linkPath ${c.linkPath}`);
    return c;
  };
  const first100 = roles.slice(0, 100);   // the orchestrations read ?limit=100 (oldest first)
  await test('HomeCards.myRequests', async () => {
    const c = await card('IORC_0037_XFD_SEC_My_Role_Requests_Card_Data');
    const mine = roles.filter((r) => r.requestedBy?.id === me.id).slice(0, 100);
    const p = mine.filter((r) => r.status === 'Pending ISC Review').length, a = mine.filter((r) => r.status === 'Approved').length;
    const wantTitle = p ? `My Role Requests · ${p} pending` : 'My Role Requests';
    if (c.title !== wantTitle) throw new Error(`title "${c.title}", expected "${wantTitle}"`);
    const wantSub = p + a === 0 ? 'No role requests yet' : (p ? `· ${a} approved` : `Nothing waiting for ISC review · ${a} approved`);
    if (!(p ? c.subtitle.startsWith('Oldest: ') && c.subtitle.endsWith(wantSub) : c.subtitle === wantSub)) throw new Error(`subtitle "${c.subtitle}", expected ${p ? '"Oldest: … ' + wantSub + '"' : '"' + wantSub + '"'}`);
    if (p && !/ · since [A-Z][a-z]{2} \d{1,2} · /.test(c.subtitle)) throw new Error(`subtitle "${c.subtitle}" has no "since Mon D" date`);
    pass('HomeCards.myRequests', `${c.title} | ${c.subtitle} | ${c.linkText} → ${c.linkPath}`);
  });
  await test('HomeCards.iscQueue', async () => {
    const c = await card('IORC_0037_XFD_SEC_ISC_Queue_Card_Data');
    const p = first100.filter((r) => r.status === 'Pending ISC Review');
    const wantTitle = p.length ? `ISC Queue · ${p.length} waiting` : 'ISC Queue';
    if (c.title !== wantTitle) throw new Error(`title "${c.title}", expected "${wantTitle}"`);
    if (p.length ? !/^Oldest: .+ · since [A-Z][a-z]{2} \d{1,2}$/.test(c.subtitle) : c.subtitle !== 'All caught up: nothing waiting for review') throw new Error(`subtitle "${c.subtitle}"`);
    if (c.linkText !== (p.length ? 'Review Now' : 'Open ISC Queue')) throw new Error(`link text "${c.linkText}"`);
    pass('HomeCards.iscQueue', `${c.title} | ${c.subtitle} | ${c.linkText} → ${c.linkPath}`);
  });
}

// ─── Full suite (writes to the tenant) ────────────────────────────────────────
async function full(token, me) {
  console.log('\n-- Full (writes TEST data, then reverts or inactivates it) --');
  // Short, readable run id: the GitHub run number (RUN15), or a random number for local runs.
  const runNo = process.env.GITHUB_RUN_NUMBER || String(100 + Math.floor(Math.random() * 900));
  const run3 = String(runNo).slice(-3).padStart(3, '0');
  const orgName = `X:ADM:TEST:CI:RUN${runNo}`;
  const now = new Date();
  const today = tenantDate(0, now.getTime());
  const later = tenantDate(45, now.getTime());
  // Fresh timestamp per call so each audit record shows when its own change happened.
  const who = () => ({ changedBy: me.descriptor, changedByWid: me.id, timestamp: new Date().toISOString().replace(/\.\d+Z$/, 'Z') });
  const expectAudit = (a, type, action) => {
    if (a.objectType !== type || a.action !== action) throw new Error(`audit record is ${a.objectType}/${a.action}, expected ${type}/${action}`);
  };
  const status = (orgId, code, orgType, inactivate, effectiveDate, validateOnly = 'false') => ({
    orgId, action: inactivate ? 'INACTIVATE' : 'REACTIVATE', orgCode: code, orgName: code,
    includeInactive: inactivate ? 'true' : 'false', effectiveDate, patternName: code,
    orgType, comsAppId: orgType, validateOnly, ...who(),
  });
  const findOrg = async (code) => {
    const r = await wql(token, `SELECT workdayID, code FROM topLevelOrganizations WHERE code = '${code}'`, 1);
    return r.data?.[0]?.workdayID?.id || r.data?.[0]?.workdayID || null;
  };

  // ── Shell org: add → inactivate today → reactivate → inactivate 45 days out ──
  let orgWid = null;
  await test('ShellOrg.add', async () => {
    const a = await launchAndVerify(token, 'IORC_0037_XFD_SEC_Create_Application_Shell_Org', {
      comsAppId: '', orgType: 'X:ADM', organizationName: orgName, organizationCode: orgName,
      workerId: me.id, effectiveDate: today, ...who(),
    });
    expectAudit(a, 'Shell Org', 'ADD');
    orgWid = await findOrg(orgName);
    if (!orgWid) throw new Error(`${orgName} not found by WQL after the audit record was written`);
    pass('ShellOrg.add', `${orgName} created and audited`);
  });

  await test('Guard.actionMismatch', async () => {
    if (!orgWid) return skip('Guard.actionMismatch', 'no org from ShellOrg.add');
    await expectRejected(token, 'IORC_0037_XFD_SEC_Change_Shell_Org_Status', { ...status(orgWid, orgName, 'X:ADM', false, later), action: 'INACTIVATE' });
    pass('Guard.actionMismatch', 'action that disagrees with includeInactive is rejected');
  });

  await test('Guard.notShellOrg', async () => {
    // orgId is a worker, not an X: shell org; validateOnly=true so nothing changes even if the guard failed.
    await expectRejected(token, 'IORC_0037_XFD_SEC_Change_Shell_Org_Status', status(me.id, orgName, 'X:ADM', true, later, 'true'));
    pass('Guard.notShellOrg', 'an orgId outside the X: shell orgs is rejected even with an X: orgCode');
  });

  let inactiveToday = false;
  await test('ShellOrg.inactivateToday', async () => {
    if (!orgWid) return skip('ShellOrg.inactivateToday', 'no org from ShellOrg.add');
    const a = await launchAndVerify(token, 'IORC_0037_XFD_SEC_Change_Shell_Org_Status', status(orgWid, orgName, 'X:ADM', true, today));
    expectAudit(a, 'Org Status', 'INACTIVATE');
    inactiveToday = true;
    pass('ShellOrg.inactivateToday', `${orgName} inactivated effective ${today}`);
  });

  await test('ShellOrg.reactivate', async () => {
    if (!inactiveToday) return skip('ShellOrg.reactivate', 'org was not inactivated today');
    const a = await launchAndVerify(token, 'IORC_0037_XFD_SEC_Change_Shell_Org_Status', status(orgWid, orgName, 'X:ADM', false, today));
    expectAudit(a, 'Org Status', 'REACTIVATE');
    pass('ShellOrg.reactivate', `${orgName} reactivated`);
  });

  await test('ShellOrg.inactivate', async () => {
    if (!orgWid) return skip('ShellOrg.inactivate', 'no org from ShellOrg.add');
    const a = await launchAndVerify(token, 'IORC_0037_XFD_SEC_Change_Shell_Org_Status', status(orgWid, orgName, 'X:ADM', true, later));
    expectAudit(a, 'Org Status', 'INACTIVATE');
    pass('ShellOrg.inactivate', `${orgName} inactivated effective ${later} (left for cleanup)`);
  });

  // ── Shell org pattern: add, then inactivate 45 days out ──
  let pattern = null; // { code, wid, appCode } for the pending-request test
  await test('Pattern.add', async () => {
    const app = ((await request('GET', `${BO}/comsApplications?limit=1`, token)).data || [])[0];
    if (!app) return skip('Pattern.add', 'no COMS application to create a pattern for');
    const appCode = app.appId; // same value the New Pattern page uses (e.g. X:CLW)
    if (!/^X:/.test(appCode || '')) throw new Error(`COMS application appId "${appCode}" is not an X: code`);
    // Clockwork's five fields: Academic Unit, Subject, Course, Section, Academic Period
    const [a1, a2, a3, a4, a5] = ['TEST', 'TEST', run3, '900', `${now.getUTCFullYear()}W1`];
    const pname = `${appCode}:PATTERN:${a1}:${a2}:${a3}:${a4}:${a5}`;
    const a = await launchAndVerify(token, 'IORC_0037_XFD_SEC_Create_Pattern_Shell_Org', {
      comsAppId: app.id, patternName: pname, workerId: me.id, attribute1: a1, attribute2: a2, attribute3: a3,
      attribute4: a4, attribute5: a5, effectiveDate: today, ...who(),
    });
    expectAudit(a, 'Shell Org Pattern', 'ADD');
    const pwid = await findOrg(pname);
    if (!pwid) throw new Error(`${pname} not found by WQL after the audit record was written`);
    pattern = { code: pname, wid: pwid, appCode };
    const b = await launchAndVerify(token, 'IORC_0037_XFD_SEC_Change_Shell_Org_Status', status(pwid, pname, appCode, true, later));
    expectAudit(b, 'Org Status', 'INACTIVATE');
    pass('Pattern.add', `${pname} created, audited and inactivated effective ${later}`);
  });

  await test('Guard.patternName', async () => {
    const app = ((await request('GET', `${BO}/comsApplications?limit=1`, token)).data || [])[0];
    if (!app) return skip('Guard.patternName', 'no COMS application');
    // A name that doesn't start with the application code must be rejected (nothing created, no audit).
    await expectRejected(token, 'IORC_0037_XFD_SEC_Create_Pattern_Shell_Org', {
      comsAppId: app.id, patternName: `TEST:PATTERN:TEST:TEST:${run3}:901:${now.getUTCFullYear()}W1`, workerId: me.id,
      attribute1: 'TEST', attribute2: `TEST:${run3}`, attribute3: '901', attribute5: `${now.getUTCFullYear()}W1`, effectiveDate: today, ...who(),
    });
    pass('Guard.patternName', 'a pattern name that does not start with the application code is rejected');
  });

  // ── Role assignment: add a position to the test role, then remove it (net no change) ──
  await test('RoleAssignment.addRemove', async () => { await roleAddRemove(token, me); });

  // ── Role request: create → start review BP → cancel the event → IORC_0037_XFD_SEC_Close_Denied_Role_Request marks it Denied ──
  // Leaves one Denied TESTROLECI request: requests linked to a BP event can't be deleted.
  await test('Request.reviewCancelDeny', async () => {
    const roleName = `X:ADM:ROLE:TESTROLECIRUN${runNo}`;
    const ref = `CI-RUN${runNo}-${Math.random().toString(36).slice(2, 8)}`;
    const req = await request('POST', `${BO}/comsAssignableRoles`, token, {
      referenceId: ref, roleName, application: 'X:ADM', status: 'Pending ISC Review', requestedDate: today,
      requestedBy: { id: me.id }, active: false, effectiveDate: today, workdayRoleId: roleName,
    });
    const reqId = req.id;
    if (!reqId) throw new Error('request POST returned no id');
    await launch(token, 'IORC_0037_XFD_SEC_Start_Role_Request_Review', { ref });
    let eventWid = null;
    for (let i = 0; i < 10 && !eventWid; i++) {
      await sleep(3000);
      eventWid = (await request('GET', `${BO}/comsAssignableRoles/${reqId}`, token)).reviewEventWid || null;
    }
    if (!eventWid) throw new Error(`IORC_0037_XFD_SEC_Start_Role_Request_Review did not link a review event to ${roleName} within 30 s`);
    const ev = await request('GET', `${BP}/events/${eventWid}`, token);
    const st = String(ev?.status?.descriptor || ev?.overallStatus?.descriptor || '');
    if (/complete|terminat|cancel|denied/i.test(st)) throw new Error(`new review event is already "${st}"`);
    pass('Request.startReview', `${roleName} has an open review event ("${st || 'in progress'}")`);

    await request('POST', `${BP}/events/${eventWid}/cancel`, token, { comment: 'Automated test run: cancel test request' });
    // Cancel is paired with IORC_0037_XFD_SEC_Close_Denied_Role_Request; BP-triggered orchestrations take ~2-3 min (up to 15).
    let r = null;
    for (let i = 0; i < 40; i++) {
      await sleep(15000);
      r = await request('GET', `${BO}/comsAssignableRoles/${reqId}`, token);
      if (r.status === 'Denied') break;
    }
    if (r?.status !== 'Denied') throw new Error(`${roleName} still "${r?.status}" 10 min after cancelling its review (IORC_0037_XFD_SEC_Close_Denied_Role_Request did not run)`);
    if (r.active !== false) throw new Error(`${roleName} is Denied but active=${r.active}`);
    const audits = (await readAll(token, 'comsAuditLogs')).filter((a) => a.roleName === roleName && a.action === 'DENY');
    if (!audits.length) throw new Error(`${roleName} is Denied but has no DENY audit record`);
    // The DENY record must name the person who denied or cancelled (here: the test user), not the BP.
    const by = audits[0];
    // changedByWid holds the Person WID from bp.initiatingPerson(), not the Worker WID, so compare names.
    if (by.triggeredBy !== me.descriptor || !by.changedByWid) {
      throw new Error(`DENY record shows Changed By "${by.triggeredBy}" (${by.changedByWid || 'no WID'}); expected ${me.descriptor}`);
    }
    // IORC_0037_XFD_SEC_Close_Denied_Role_Request copies the event's comment (here the cancel comment) into Denial Reason.
    if (!/Automated test run/.test(r.denialReason || '')) throw new Error(`${roleName} Denial Reason is "${r.denialReason || ''}", expected the cancel comment`);
    pass('Request.reviewCancelDeny', `${roleName}: cancelling the review marked it Denied, inactive, with the cancel comment as Denial Reason and a DENY audit naming ${me.descriptor}`);
  });

  // ── Two pending ISC requests, left open for review: one on the new shell org, one on the new pattern ──
  // Built the way the Assignable Role Manager page builds them (<org code>:ROLE:<name>, REQUEST audit,
  // then IORC_0037_XFD_SEC_Start_Role_Request_Review). Cleanup cancels their reviews, which marks them Denied.
  // One filled position, sent like the page's Positions field: WIDs in positions/positionWids, full names in positionNames.
  let testPos = null;
  const pickPosition = async () => {
    if (testPos) return testPos;
    const p = ((await wql(token, 'SELECT cf_PositionID, workdayID, position_PositionManagement, cf_PositionText, cf_PositionIsFilled FROM allPositions WHERE supervisoryOrganization is not empty', 50)).data || [])
      .find((x) => x.cf_PositionIsFilled !== false && (x.position_PositionManagement?.descriptor || x.cf_PositionText));
    if (!p) throw new Error('no filled position found for the test requests');
    testPos = { wid: p.workdayID?.id || p.workdayID, name: p.position_PositionManagement?.descriptor || p.cf_PositionText };
    return testPos;
  };
  // One active academic unit for Enabled For, saved the way the request page saves it.
  let testUnit = null;
  const pickUnit = async () => {
    if (testUnit) return testUnit;
    const u = ((await wql(token, 'SELECT workdayID, academicUnit, academicUnitName FROM academicUnits WHERE inactive = false', 20)).data || [])
      .find((x) => x.academicUnit?.descriptor);
    if (!u) throw new Error('no active academic unit found for Enabled For');
    testUnit = { wid: u.workdayID?.id || u.workdayID, name: u.academicUnit.descriptor };
    return testUnit;
  };
  const pendingRequest = async (name, orgCode, orgWid, appCode) => {
    const roleName = `${orgCode}:ROLE:TESTROLE`;
    const pos = await pickPosition();
    const unit = await pickUnit();
    const ref = `CI-RUN${runNo}-${name}-${Math.random().toString(36).slice(2, 8)}`;
    const req = await request('POST', `${BO}/comsAssignableRoles`, token, {
      referenceId: ref, roleName, workdayRoleId: roleName, application: appCode, shellOrgCode: orgCode, shellOrgWid: orgWid,
      status: 'Pending ISC Review', requestedDate: today, requestedBy: { id: me.id }, active: false, effectiveDate: today,
      positions: pos.wid, positionWids: pos.wid, positionNames: pos.name,
      enabledForOrganizationTypes: unit.name, enabledForWid: unit.wid, academicUnitWid: unit.wid, academicUnitDescription: unit.name,
    });
    if (!req.id) throw new Error('request POST returned no id');
    // IORC_0037_XFD_SEC_Start_Role_Request_Review writes the REQUEST audit record (with the event and run ID) since 2026-11-04.
    await launch(token, 'IORC_0037_XFD_SEC_Start_Role_Request_Review', { ref });
    let eventWid = null;
    for (let i = 0; i < 10 && !eventWid; i++) {
      await sleep(3000);
      eventWid = (await request('GET', `${BO}/comsAssignableRoles/${req.id}`, token)).reviewEventWid || null;
    }
    if (!eventWid) throw new Error(`IORC_0037_XFD_SEC_Start_Role_Request_Review did not link a review event to ${roleName} within 30 s`);
    const ev = await request('GET', `${BP}/events/${eventWid}`, token);
    const st = String(ev?.status?.descriptor || ev?.overallStatus?.descriptor || '');
    if (/complete|terminat|cancel|denied/i.test(st)) throw new Error(`review event for ${roleName} is already "${st}"`);
    const reqAudit = (await readAll(token, 'comsAuditLogs')).find((a) => a.action === 'REQUEST' && a.roleName === roleName);
    if (!reqAudit) throw new Error(`IORC_0037_XFD_SEC_Start_Role_Request_Review wrote no REQUEST audit record for ${roleName}`);
    if (reqAudit.eventWid !== eventWid || !reqAudit.runId) throw new Error(`REQUEST audit for ${roleName}: eventWid ${reqAudit.eventWid || '-'} (want ${eventWid}), runId ${reqAudit.runId || '-'}`);
    return { roleName, st, pos: pos.name, unit: unit.name };
  };

  await test('Request.pendingShellOrg', async () => {
    if (!orgWid) return skip('Request.pendingShellOrg', 'no org from ShellOrg.add');
    const r = await pendingRequest('ORG', orgName, orgWid, 'X:ADM');
    pass('Request.pendingShellOrg', `${r.roleName} (position ${r.pos}, enabled for ${r.unit}) is pending ISC review ("${r.st || 'in progress'}")`);
  });

  await test('Request.pendingPattern', async () => {
    if (!pattern) return skip('Request.pendingPattern', 'no pattern from Pattern.add');
    const r = await pendingRequest('PAT', pattern.code, pattern.wid, pattern.appCode);
    pass('Request.pendingPattern', `${r.roleName} (position ${r.pos}, enabled for ${r.unit}) is pending ISC review ("${r.st || 'in progress'}")`);
  });
}

// ─── Cleanup (dry run unless --apply) ─────────────────────────────────────────
// Test data is anything carrying TEST in its name/code (TEST:ORG, TESTROLE, TEST:CI) plus the
// pattern orgs created during testing, which have no TEST marker. Everything else is reported
// as "kept" so a human can check nothing real is caught, and nothing extra is missed.
const KNOWN_TEST_PATTERNS = [
  'X:CLW:PATTERN:MATH:MATH:300:951:2026W1',
  'X:CLW:PATTERN:MATH:MATH:301:951:2026W1',
  'X:CLW:PATTERN:MATH:MATH:302:951:2026W1',
  'X:CLW:PATTERN:MATH:MATH_V:303:951:2026W1',
];
const EXTRA_TEST_IDS = (arg('--also') || '').split(',').map((s) => s.trim()).filter(Boolean);
const isTestText = (...vals) => vals.some((v) => {
  const s = String(v ?? '');
  return /TEST/.test(s) || KNOWN_TEST_PATTERNS.some((p) => s.includes(p));
});
const wid = (v) => (v && typeof v === 'object' ? v.id : v);
const code = (o) => o.code?.descriptor || o.code || o.organizationByName?.descriptor || '';

async function cleanup(token, me) {
  const APPLY = argv.includes('--apply');
  console.log(`\n-- Cleanup (${APPLY ? 'APPLY' : 'DRY RUN: nothing will change'}) --`);
  const today = tenantDate();
  const ts = new Date().toISOString().replace(/\.\d+Z$/, 'Z');

  // 1. Active test orgs and patterns -> inactivate effective today (Workday orgs can't be deleted).
  const orgs = (await wql(token, 'SELECT workdayID, organizationByName, code, cf_active1 FROM topLevelOrganizations WHERE code contains \'X:\'', 10000)).data || [];
  const testOrgs = orgs.filter((o) => isTestText(code(o)));
  const activeTest = testOrgs.filter((o) => o.cf_active1 === true || o.cf_active1 === 'true' || o.cf_active1 === 1);
  console.log(`\nOrgs: ${orgs.length} X: orgs, ${testOrgs.length} test orgs, ${activeTest.length} still active (to inactivate):`);
  activeTest.forEach((o) => console.log(`   inactivate  ${code(o)}`));
  testOrgs.filter((o) => !activeTest.includes(o)).forEach((o) => console.log(`   already inactive  ${code(o)}`));

  // 2. Test role requests -> delete (pending ones included; their review events are reported).
  const roles = await readAll(token, 'comsAssignableRoles');
  const testRolesAll = roles.filter((r) => EXTRA_TEST_IDS.includes(r.id) || isTestText(r.roleName, r.referenceId, r.shellOrgCode));
  // A request linked to a Workday review event can't be deleted (HTTP 500 "Attempt to delete
  // instance ... with references"); the event is permanent history. Those are reported and kept.
  const testRoles = testRolesAll.filter((r) => !r.reviewEventWid);
  testRolesAll.filter((r) => r.reviewEventWid).forEach((r) =>
    console.log(`   keep (linked to review event, can't be deleted)  ${r.roleName}  [${r.status}]`));
  console.log(`\nRole requests: ${roles.length} total, ${testRoles.length} to delete:`);
  // Pending test requests can't be deleted either; cancelling their review closes them (IORC_0037_XFD_SEC_Close_Denied_Role_Request
  // then marks them Denied with a DENY audit, which step 3 removes).
  const pendingTest = testRolesAll.filter((r) => r.reviewEventWid && r.status === 'Pending ISC Review');
  pendingTest.forEach((r) => console.log(`   cancel review  ${r.roleName}  (event ${r.reviewEventWid})`));
  testRoles.forEach((r) => console.log(`   delete  ${r.id}  ${r.roleName}  [${r.status}]${r.reviewEventWid ? '  review event ' + r.reviewEventWid : ''}`));
  console.log('   kept (not identified as test):');
  roles.filter((r) => !testRoles.includes(r)).forEach((r) => console.log(`     ${r.id}  ${r.roleName}  [${r.status}]  requested ${r.requestedDate || '?'}`));

  // 3. Test audit entries -> delete. Done last so the inactivation records above are removed too.
  const audits = await readAll(token, 'comsAuditLogs');
  // Role assignment tests add a position to TEST_ROLE and remove it again: an ASSIGN and a
  // REMOVE for the same position ID on that role are test records (net no change).
  const pid = (a) => (String(a.positionName || '').match(/P-\d+/) || [])[0];
  const onTestRole = audits.filter((a) => a.objectType === 'Role Assignment' && a.roleName === TEST_ROLE && pid(a));
  const pairedIds = new Set(onTestRole.filter((a) => onTestRole.some((b) => pid(b) === pid(a) && b.action !== a.action)).map((a) => a.id));
  const testAudit = (a) => EXTRA_TEST_IDS.includes(a.id) || pairedIds.has(a.id) || isTestText(a.coName, a.coReferenceId, a.roleName, a.details);
  console.log(`\nAudit entries: ${audits.length} read, ${audits.filter(testAudit).length} to delete:`);
  audits.filter(testAudit).forEach((a) => console.log(`   delete  ${a.id}  ${a.timestamp}  ${a.objectType}/${a.action}  ${a.coName || ''} ${a.roleName || ''}`.trimEnd()));
  console.log('   kept (not identified as test):');
  audits.filter((a) => !testAudit(a)).forEach((a) => console.log(`     ${a.id}  ${a.timestamp}  ${a.objectType}/${a.action}  ${a.coName || ''} ${a.roleName || ''} ${a.positionName || ''}`.trimEnd()));

  // 4. Test bulk runs and their row records (batchRef TEST..., written by bulkvalidate / bulkapply) -> delete.
  // Runs and rows not marked TEST (e.g. a demo's bulk edit) are kept; `purge` is the suite that clears everything.
  const isTestRef = (r) => /^TEST/i.test(String(r.batchRef || '')) || EXTRA_TEST_IDS.includes(r.id);
  const bulkRuns = await readAll(token, 'comsBulkRuns');
  const bulkRows = await readAll(token, 'comsBulkRowResults');
  console.log(`\nBulk runs: ${bulkRuns.length} read, ${bulkRuns.filter(isTestRef).length} to delete; row records: ${bulkRows.length} read, ${bulkRows.filter(isTestRef).length} to delete:`);
  [...bulkRuns, ...bulkRows].filter(isTestRef).forEach((r) => console.log(`   delete  ${r.id}  ${r.batchRef}  ${r.runMode || ''} ${r.status || r.result || ''}`.trimEnd()));
  console.log('   kept (not identified as test):');
  [...bulkRuns, ...bulkRows].filter((r) => !isTestRef(r)).forEach((r) => console.log(`     ${r.id}  ${r.batchRef}  ${r.runMode || ''} ${r.status || r.result || ''}  ${r.roleName || r.summary || ''}`.trimEnd()));

  if (!APPLY) {
    pass('Cleanup.dryRun', `would inactivate ${activeTest.length} org(s), cancel ${pendingTest.length} pending review(s), delete ${testRoles.length} request(s), ${audits.filter(testAudit).length}+ audit entr(ies) and ${bulkRuns.filter(isTestRef).length + bulkRows.filter(isTestRef).length} bulk record(s)`);
    return;
  }
  for (const r of [...bulkRows, ...bulkRuns].filter(isTestRef)) {
    await test(`Cleanup.deleteBulk ${r.batchRef}`, async () => {
      const coll = bulkRuns.includes(r) ? 'comsBulkRuns' : 'comsBulkRowResults';
      await request('DELETE', `${BO}/${coll}/${r.id}`, token);
      pass(`Cleanup.deleteBulk ${r.batchRef}`, `${coll} record deleted`);
    });
  }

  const tomorrow = tenantDate(1);
  // --effective yyyy-MM-dd: use this date only (e.g. after future-dated events that block earlier dates).
  // --only CODE1,CODE2: limit inactivation to these org codes.
  const FIXED = arg('--effective');
  const ONLY = (arg('--only') || '').split(',').map((x) => x.trim()).filter(Boolean);
  for (const o of activeTest.filter((x) => !ONLY.length || ONLY.includes(code(x)))) {
    await test(`Cleanup.inactivate ${code(o)}`, async () => {
      const params = (eff) => ({
        orgId: wid(o.workdayID), action: 'INACTIVATE', orgCode: code(o), orgName: code(o), includeInactive: 'true',
        effectiveDate: eff, patternName: code(o), orgType: code(o).split(':').slice(0, 2).join(':'),
        comsAppId: code(o).split(':').slice(0, 2).join(':'), validateOnly: 'false',
        changedBy: me.descriptor, changedByWid: me.id, timestamp: ts,
      });
      // An org with another status change already dated today is rejected; try tomorrow instead.
      let eff = FIXED || today;
      try {
        if (FIXED) await launchAndVerify(token, 'IORC_0037_XFD_SEC_Change_Shell_Org_Status', params(FIXED));
        else try { await launchAndVerify(token, 'IORC_0037_XFD_SEC_Change_Shell_Org_Status', params(today)); } catch (e1) {
          eff = tomorrow;
          try { await launchAndVerify(token, 'IORC_0037_XFD_SEC_Change_Shell_Org_Status', params(tomorrow)); } catch (e2) { throw new Error(`${today}: ${e1.message.slice(0, 160)} | ${tomorrow}: ${e2.message.slice(0, 160)}`); }
        }
      } catch (e) {
        // Workday allows one pending status change: an org whose inactivation is already scheduled is rejected.
        // An HTML 403 is the API gateway refusing the launch before it runs (see CLAUDE.md).
        return skip(`Cleanup.inactivate ${code(o)}`, `not changed (${e.message.slice(0, 340)})`);
      }
      pass(`Cleanup.inactivate ${code(o)}`, `inactivated effective ${eff}`);
    });
  }
  for (const r of pendingTest) {
    await test(`Cleanup.cancelReview ${r.roleName}`, async () => {
      await request('POST', `${BP}/events/${r.reviewEventWid}/cancel`, token, { comment: 'Test cleanup: cancel test request' });
      pass(`Cleanup.cancelReview ${r.roleName}`, 'review cancelled');
    });
  }
  if (pendingTest.length) {
    // Wait for IORC_0037_XFD_SEC_Close_Denied_Role_Request (usually 2-3 min) so its DENY audit records are cleared below.
    await test('Cleanup.pendingClosed', async () => {
      const ids = pendingTest.map((r) => r.id);
      for (let i = 0; i < 24; i++) {
        await sleep(15000);
        const open = (await readAll(token, 'comsAssignableRoles'))
          .filter((r) => ids.includes(r.id) && r.status !== 'Denied');
        if (!open.length) return pass('Cleanup.pendingClosed', `${ids.length} pending test request(s) now Denied`);
      }
      throw new Error('some cancelled test requests are not Denied after 6 min (IORC_0037_XFD_SEC_Close_Denied_Role_Request may still be queued)');
    });
  }
  for (const r of testRoles) {
    await test(`Cleanup.deleteRequest ${r.roleName}`, async () => {
      await request('DELETE', `${BO}/comsAssignableRoles/${r.id}`, token);
      pass(`Cleanup.deleteRequest ${r.roleName}`, 'deleted');
    });
  }
  // Re-read so audit entries written by the inactivations above are cleared too.
  const auditsNow = await readAll(token, 'comsAuditLogs');
  let deleted = 0;
  for (const a of auditsNow.filter(testAudit)) {
    await test(`Cleanup.deleteAudit ${a.id}`, async () => {
      await request('DELETE', `${BO}/comsAuditLogs/${a.id}`, token);
      deleted++;
    });
  }
  pass('Cleanup.audit', `deleted ${deleted} test audit entr(ies)`);
}

// ═══ Repair suite: one-off data corrections (dry run unless --apply) ═══
//   --unassign <P-id>  remove that position from the test role (--role), through IORC_0037_XFD_SEC_Assign_Remove_Role_Positions,
//                      so the change gets the same REMOVE POSITION audit record as the page.
//   always:            pending requests whose Enabled For holds a bare WID get the unit's name, looked
//                      up in the same lists the request page's pickers search (FUH, academic units).
async function repair(token, me) {
  const apply = argv.includes('--apply');
  console.log(`\n-- Repair (${apply ? 'APPLY' : 'dry run: add --apply to change data'}) --`);
  const today = tenantDate();
  const who = () => ({ changedBy: me.descriptor, changedByWid: me.id, timestamp: new Date().toISOString().replace(/\.\d+Z$/, 'Z') });
  const idOf = (v) => String(v && typeof v === 'object' ? v.id : v || '');

  // --drop-audit <exact org name>: delete only the audit records for that organization (e.g. a demo
  // rehearsal record). The organization itself is untouched: orgs can only be inactivated.
  const dropAudit = arg('--drop-audit');
  if (dropAudit) await test('Repair.dropAudit', async () => {
    const hits = (await readAll(token, 'comsAuditLogs')).filter((a) => a.coName === dropAudit || a.coReferenceId === dropAudit);
    hits.forEach((a) => console.log(`   ${apply ? 'delete' : 'would delete'}  ${a.id}  ${a.timestamp}  ${a.objectType}/${a.action}  ${a.coName || ''}  by ${a.triggeredBy || a.worker?.descriptor || ''}`));
    if (!hits.length) return pass('Repair.dropAudit', `no audit record for ${dropAudit}`);
    if (!apply) return pass('Repair.dropAudit', `would delete ${hits.length} audit record(s) for ${dropAudit}`);
    for (const a of hits) await request('DELETE', `${BO}/comsAuditLogs/${a.id}`, token);
    const left = (await readAll(token, 'comsAuditLogs')).filter((a) => a.coName === dropAudit || a.coReferenceId === dropAudit);
    if (left.length) throw new Error(`${left.length} still there`);
    pass('Repair.dropAudit', `deleted ${hits.length} audit record(s) for ${dropAudit}`);
  });
  if (dropAudit) return;   // on its own: skip the other repairs below

  // --backfill-wids: give old audit records the org and role WIDs newer records store, so the Audit Log no longer needs
  // its three lookup lists (all shell orgs, shell roles, AAA roles) just to link these few (2026-11-04).
  if (argv.includes('--backfill-wids')) await test('Repair.backfillWids', async () => {
    const wqlFile = (id) => JSON.parse(fs.readFileSync(path.join(ROOT, 'presentation/wqlQueries', id + '.wqlquery'), 'utf8')).query;
    const orgs = (await wql(token, wqlFile('allShellOrgs'), 10000)).data || [];
    const roles = [...((await wql(token, wqlFile('allShellAssignableRolesinTenant'), 1000)).data || []), ...((await wql(token, wqlFile('allAAArolesinTenant'), 1000)).data || [])];
    const todo = (await readAll(token, 'comsAuditLogs')).filter((a) => (!a.orgWid && a.coName) || (!a.roleWid && a.roleName));
    let done = 0;
    for (const a of todo) {
      const body = {};
      if (!a.orgWid && a.coName) { const o = orgs.find((x) => x.code === a.coName && x.organizationByName?.id); if (o) body.orgWid = o.organizationByName.id; }
      if (!a.roleWid && a.roleName) { const r = roles.find((x) => x.role?.descriptor === a.roleName && x.role?.id); if (r) body.roleWid = r.role.id; }
      console.log(`   ${a.id} ${a.timestamp} ${a.objectType}/${a.action} ${a.coName || ''} ${a.roleName || ''} -> ${JSON.stringify(body) === '{}' ? 'no match (stays text)' : (apply ? 'set ' : 'would set ') + Object.keys(body).join(', ')}`);
      if (apply && Object.keys(body).length) { await request('PATCH', `${BO}/comsAuditLogs/${a.id}`, token, body); done++; }
    }
    pass('Repair.backfillWids', `${todo.length} record(s) without WIDs; ${apply ? 'updated ' + done : 'dry run'}`);
  });
  if (argv.includes('--backfill-wids')) return;

  const unassign = arg('--unassign');
  if (unassign) await test('Repair.unassign', async () => {
    const readRole = async () => {
      const r = await wql(token, `SELECT role, roleAssignments{organization, cf_ZCF_EE_RoleAssignedToAsPositionRestrictions} as roleAssignments FROM assignableRoles WHERE roleName = '${TEST_ROLE}'`, 5);
      const row = (r.data || [])[0];
      const ra = (row?.roleAssignments || []).find((x) => String(x.organization?.descriptor || '').startsWith('X:'));
      return row && ra ? { role: row.role, org: ra.organization, positions: ra.cf_ZCF_EE_RoleAssignedToAsPositionRestrictions || [] } : null;
    };
    const cur = await readRole();
    if (!cur) throw new Error(`${TEST_ROLE} has no X: organization assignment`);
    const hit = cur.positions.find((p) => String(p.descriptor || '').includes(unassign));
    if (!hit) return pass('Repair.unassign', `${unassign} is not assigned to ${TEST_ROLE}: nothing to do`);
    const params = {
      roleId: cur.role.id, roleName: TEST_ROLE, orgId: cur.org.id, orgName: cur.org.descriptor, effectiveDate: today,
      positionId: hit.id, positionIdType: 'WID', positionName: hit.descriptor, mode: 'REMOVE', positionWid: hit.id, ...who(),
    };
    if (!apply) return pass('Repair.unassign', `would remove "${hit.descriptor}" from ${TEST_ROLE} on ${cur.org.descriptor}`);
    const rem = await launchAndVerify(token, 'IORC_0037_XFD_SEC_Assign_Remove_Role_Positions', params);
    if (rem.objectType !== 'Role Assignment' || rem.action !== 'REMOVE POSITION') throw new Error(`audit is ${rem.objectType}/${rem.action}`);
    let gone = false;
    for (let i = 0; i < 18 && !gone; i++) {
      gone = !((await readRole())?.positions || []).some((p) => p.id === hit.id);
      if (!gone) await sleep(5000);
    }
    if (!gone) throw new Error(`REMOVE POSITION audited but "${hit.descriptor}" still shows on ${TEST_ROLE} after 90 s`);
    pass('Repair.unassign', `removed "${hit.descriptor}" from ${TEST_ROLE} (audit ${rem.id})`);
  });

  // Audit records with no action: written by test calls that reached IORC_0037_XFD_SEC_Assign_Remove_Role_Positions with a
  // mode other than ADD/REMOVE (before its mode guard existed). They describe no change.
  await test('Repair.auditNoAction', async () => {
    const all = await readAll(token, 'comsAuditLogs');
    const junk = all.filter((a) => a.objectType === 'Role Assignment' && !a.action);
    if (!junk.length) return pass('Repair.auditNoAction', 'no audit records without an action');
    if (!apply) return pass('Repair.auditNoAction', `would delete ${junk.length} Role Assignment audit record(s) with no action`);
    for (const a of junk) await request('DELETE', `${BO}/comsAuditLogs/${a.id}`, token);
    pass('Repair.auditNoAction', `deleted ${junk.length} Role Assignment audit record(s) with no action`);
  });

  // Bulk audit records written before the bulk run looked positions up (2026-10-31): the position
  // name came from the CSV and ADD rows had no position WID. Use Workday's name and WID, as single
  // changes do. Approved by the product owner 2026-10-31.
  await test('Repair.bulkAuditPosition', async () => {
    const all = await readAll(token, 'comsAuditLogs');
    const bulk = all.filter((a) => a.objectType === 'Role Assignment' && /^Bulk upload /.test(a.details || ''));
    const fixes = [];
    for (const a of bulk) {
      const pid = (String(a.positionName || '').match(/^P-\d+/) || [])[0];
      if (!pid) continue;
      const r = await wql(token, `SELECT workdayID, cf_PositionID, position_PositionManagement, cf_PositionText FROM allPositions WHERE cf_PositionID = '${pid}'`, 1);
      const pos = (r.data || [])[0];
      if (!pos) { warn('Repair.bulkAuditPosition', `${a.id}: ${pid} not found in allPositions; left as is`); continue; }
      const name = pos.position_PositionManagement?.descriptor || pos.cf_PositionText || a.positionName;
      const wid = a.positionWid || idOf(pos.workdayID);
      if (name === a.positionName && wid === a.positionWid) continue;
      fixes.push({ a, body: { positionName: name, positionWid: wid, details: String(a.details).split(a.positionName).join(name) } });
    }
    if (!fixes.length) return pass('Repair.bulkAuditPosition', `${bulk.length} bulk audit record(s) already use Workday's position name and WID`);
    const list = fixes.map((f) => `${f.a.action} ${f.a.timestamp}: name "${f.a.positionName}" → "${f.body.positionName}", WID "${f.a.positionWid || ''}" → "${f.body.positionWid}"`).join('; ');
    if (!apply) return pass('Repair.bulkAuditPosition', `would update ${fixes.length}: ${list}`);
    for (const f of fixes) await request('PATCH', `${BO}/comsAuditLogs/${f.a.id}`, token, f.body);
    pass('Repair.bulkAuditPosition', `updated ${fixes.length}: ${list}`);
  });

  await test('Repair.enabledFor', async () => {
    const roles = await readAll(token, 'comsAssignableRoles');
    const bad = roles.filter((r) => r.status === 'Pending ISC Review' && /^[0-9a-f]{32}$/.test(r.enabledForOrganizationTypes || ''));
    if (!bad.length) return pass('Repair.enabledFor', 'no pending request holds a bare WID in Enabled For');
    const fuh = (await wql(token, 'SELECT workdayID, organization1, code FROM customOrganizations WHERE type1 in (b40d8b016367100175b147f364840000)', 10000)).data || [];
    const au = (await wql(token, 'SELECT workdayID, academicUnit, academicUnitName FROM academicUnits WHERE inactive = false', 10000)).data || [];
    const left = [];
    for (const r of bad) {
      const w = r.enabledForOrganizationTypes;
      const f = fuh.find((o) => idOf(o.workdayID) === w);
      const a = f ? null : au.find((o) => idOf(o.workdayID) === w);
      const name = f ? f.organization1?.descriptor : a ? a.academicUnit?.descriptor : null;
      if (!name) { left.push(r.roleName); warn('Repair.enabledFor', `${r.roleName}: ${w} is in neither the FUH nor the academic unit list; left as is`); continue; }
      const body = {
        enabledForOrganizationTypes: name, enabledForWid: w,
        functionalUnitHierarchyWid: f ? w : '', functionalUnitDescription: f ? name : '',
        academicUnitWid: a ? w : '', academicUnitDescription: a ? name : '',
      };
      if (!apply) { console.log(`  would set ${r.roleName} Enabled For to "${name}" (${f ? 'FUH' : 'academic unit'})`); continue; }
      await request('PATCH', `${BO}/comsAssignableRoles/${r.id}`, token, body);
      const back = await request('GET', `${BO}/comsAssignableRoles/${r.id}`, token);
      if (back.enabledForOrganizationTypes !== name) throw new Error(`${r.roleName}: PATCH did not stick (reads "${back.enabledForOrganizationTypes}")`);
      console.log(`  set ${r.roleName} Enabled For to "${name}"`);
    }
    if (left.length) throw new Error(`${left.length} request(s) not fixed: ${left.join(', ')}`);
    pass('Repair.enabledFor', `${bad.length} request(s) ${apply ? 'corrected' : 'would be corrected'}`);
  });

  // Requests whose positions show as a bare WID: Position Names empty (saved before names were stored,
  // TESTROLE1031 on 2026-10-30) or holding a WID. Look each WID up in allPositions and store the same
  // full name the page sends.
  await test('Repair.positionNames', async () => {
    const roles = await readAll(token, 'comsAssignableRoles');
    const isWid = (s) => /^[0-9a-f]{32}$/.test(String(s).trim());
    const SPLIT = /,\s*(?=[0-9a-f]{32}(?:,|$)|P-\d)/;
    const source = (r) => String(r.positionNames || '').trim() || String(r.positionWids || r.positions || '').trim();
    const bad = roles.filter((r) => source(r) && source(r).split(SPLIT).some(isWid));
    if (!bad.length) return pass('Repair.positionNames', 'every request with positions has their names stored');
    const all = (await wql(token, 'SELECT cf_PositionID, workdayID, position_PositionManagement, cf_PositionText FROM allPositions WHERE supervisoryOrganization is not empty', 10000)).data || [];
    const left = [];
    for (const r of bad) {
      const parts = source(r).split(SPLIT);
      const fixed = parts.map((p) => {
        if (!isWid(p)) return p;
        const pos = all.find((x) => idOf(x.workdayID) === p.trim());
        return pos ? (pos.position_PositionManagement?.descriptor || pos.cf_PositionText || pos.cf_PositionID) : null;
      });
      if (fixed.includes(null)) { left.push(r.roleName); warn('Repair.positionNames', `${r.roleName}: a WID in "${source(r)}" is not in allPositions; left as is`); continue; }
      const name = fixed.join(', ');
      if (!apply) { console.log(`  would set ${r.roleName} (${r.status}) Position Names "${r.positionNames || ''}" → "${name}"`); continue; }
      await request('PATCH', `${BO}/comsAssignableRoles/${r.id}`, token, { positionNames: name });
      const back = await request('GET', `${BO}/comsAssignableRoles/${r.id}`, token);
      if (back.positionNames !== name) throw new Error(`${r.roleName}: PATCH did not stick (reads "${back.positionNames}")`);
      console.log(`  set ${r.roleName} Position Names to "${name}"`);
    }
    if (left.length) throw new Error(`${left.length} request(s) not fixed: ${left.join(', ')}`);
    pass('Repair.positionNames', `${bad.length} request(s) ${apply ? 'corrected' : 'would be corrected'}`);
  });
}

// ═══ Second-user suite (run only by name; needs WD_SECOND_TOKEN) ═══
// Checks what one account can't: a requester withdrawing their own request, someone else cancelling
// it, and a requester being refused on another person's review. WD_SECOND_TOKEN is a tenant token for a
// non-admin test requester (Manage: COMS Assignable Roles; Cancel as Initiator on the BP policy).
// Leaves 3 Denied TEST requests (BP-linked records can't be deleted).
async function secondUserSuite(token, me) {
  console.log('\n-- Second user (requester vs admin) --');
  const token2 = process.env.WD_SECOND_TOKEN || arg('--token2');
  if (!token2) return skip('SecondUser', 'WD_SECOND_TOKEN is not set (see test/README.md "Second-user tests")');
  let me2;
  try { me2 = await request('GET', `${API}/common/v1/workers/me`, token2); } catch (e) { return fail('SecondUser.auth', e.message); }
  if (me2.id === me.id) return fail('SecondUser.auth', `WD_SECOND_TOKEN signs in as ${me.descriptor}, the same person as the main token`);
  pass('SecondUser.auth', `second user is ${me2.descriptor}`);
  const runNo = process.env.GITHUB_RUN_NUMBER || String(100 + Math.floor(Math.random() * 900));
  const today = tenantDate();
  // Create a request and start its review as `tok` (that person becomes the initiator).
  const startRequest = async (tok, who, suffix) => {
    const roleName = `X:ADM:ROLE:TESTROLE${suffix}RUN${runNo}`;
    const ref = `CI-RUN${runNo}-${suffix}-${Math.random().toString(36).slice(2, 6)}`;
    const req = await request('POST', `${BO}/comsAssignableRoles`, tok, {
      referenceId: ref, roleName, application: 'X:ADM', status: 'Pending ISC Review', requestedDate: today,
      requestedBy: { id: who.id }, active: false, effectiveDate: today, workdayRoleId: roleName,
    });
    await launch(tok, 'IORC_0037_XFD_SEC_Start_Role_Request_Review', { ref });
    let ev = null;
    for (let i = 0; i < 10 && !ev; i++) { await sleep(3000); ev = (await request('GET', `${BO}/comsAssignableRoles/${req.id}`, tok)).reviewEventWid || null; }
    if (!ev) throw new Error(`no review event linked to ${roleName} within 30 s`);
    return { id: req.id, roleName, ev };
  };
  const waitDenied = async (r) => {
    for (let i = 0; i < 40; i++) {
      await sleep(15000);
      const x = await request('GET', `${BO}/comsAssignableRoles/${r.id}`, token);
      if (x.status === 'Denied') return x;
    }
    throw new Error(`${r.roleName} not Denied 10 min after its review was cancelled`);
  };
  const denyAudit = async (r) => (await readAll(token, 'comsAuditLogs')).find((a) => a.roleName === r.roleName && a.action === 'DENY');

  await test('SecondUser.withdrawOwn', async () => {
    const r = await startRequest(token2, me2, 'WD');
    await request('POST', `${BP}/events/${r.ev}/cancel`, token2, { comment: 'Automated test run: requester withdraws' });
    const x = await waitDenied(r);
    const a = await denyAudit(r);
    if (!a || a.triggeredBy !== me2.descriptor) throw new Error(`DENY audit for ${r.roleName} names "${a?.triggeredBy}", expected the requester ${me2.descriptor}`);
    if (!/requester withdraws/.test(x.denialReason || '')) throw new Error(`Denial Reason is "${x.denialReason || ''}"`);
    pass('SecondUser.withdrawOwn', `${me2.descriptor} withdrew ${r.roleName}; Denied, with their comment and a DENY audit naming them`);
  });
  await test('SecondUser.cancelledByOther', async () => {
    const r = await startRequest(token2, me2, 'OC');
    await request('POST', `${BP}/events/${r.ev}/cancel`, token, { comment: 'Automated test run: admin cancels' });
    await waitDenied(r);
    const a = await denyAudit(r);
    if (!a || a.triggeredBy !== me.descriptor) throw new Error(`DENY audit for ${r.roleName} names "${a?.triggeredBy}", expected the canceller ${me.descriptor} (requester was ${me2.descriptor})`);
    pass('SecondUser.cancelledByOther', `${me.descriptor} cancelled ${me2.descriptor}'s ${r.roleName}; the DENY audit names the canceller`);
  });
  await test('SecondUser.cannotCancelOthers', async () => {
    const r = await startRequest(token, me, 'XC');
    let refused = false;
    try { await request('POST', `${BP}/events/${r.ev}/cancel`, token2, { comment: 'Automated test run: should be refused' }); } catch (e) { refused = /HTTP 40[0-9]/.test(e.message); }
    // Close it either way so it doesn't stay pending.
    if (!refused) { await waitDenied(r); throw new Error(`${me2.descriptor} could cancel ${me.descriptor}'s review of ${r.roleName}`); }
    await request('POST', `${BP}/events/${r.ev}/cancel`, token, { comment: 'Automated test run: close test request' });
    pass('SecondUser.cannotCancelOthers', `${me2.descriptor} was refused cancelling someone else's review (closed it as admin)`);
  });
}

// ═══ ISU suite: lockdown checks (run only by name, once ISU writes are live) ═══
// After the ISU change, users are View/Get only on the audit log and request data, and only the app
// (pages with isuAuth, orchestrations with the ISU credential) can write. These checks try direct
// writes as the signed-in user and expect them to be refused. Anything that gets through is
// deleted again and fails the test. Delete itself isn't probed: a successful probe would destroy data.
async function isuSuite(token, me) {
  console.log('\n-- ISU (lockdown: direct user writes must be refused) --');
  await test('ISU.writesUseIsu', async () => isuStaticCheck());
  const refused = async (name, fn, undo) => {
    let created;
    try { created = await fn(); } catch (e) {
      if (/HTTP 40[13]/.test(e.message)) return pass(name, `refused (${e.message.slice(0, 8)})`);
      throw new Error(`expected 401/403, got: ${e.message.slice(0, 120)}`);
    }
    if (created?.id) { try { await undo(created.id); } catch (_) { /* reported below */ } }
    throw new Error(`the write went through as ${me.descriptor} (record ${created?.id || '?'} removed again)`);
  };
  const ts = new Date().toISOString().replace(/\.\d+Z$/, 'Z');
  await test('ISU.userCannotWriteAudit', () => refused('ISU.userCannotWriteAudit',
    () => request('POST', `${BO}/comsAuditLogs`, token, { timestamp: ts, objectType: 'Shell Org', action: 'ADD', coName: 'X:ADM:TEST:ISU:PROBE', details: 'ISU lockdown probe' }),
    (id) => request('DELETE', `${BO}/comsAuditLogs/${id}`, token)));
  await test('ISU.userCannotWriteRequest', () => refused('ISU.userCannotWriteRequest',
    () => request('POST', `${BO}/comsAssignableRoles`, token, { referenceId: `ISU-PROBE-${Date.now()}`, roleName: 'X:ADM:ROLE:TESTROLEISUPROBE', status: 'Pending ISC Review', active: false }),
    (id) => request('DELETE', `${BO}/comsAssignableRoles/${id}`, token)));
  await test('ISU.userCannotEditRequest', async () => {
    const r = (await readAll(token, 'comsAssignableRoles')).find((x) => /TEST/.test(x.roleName || ''));
    if (!r) return skip('ISU.userCannotEditRequest', 'no TEST request to probe');
    // PATCH a field to its current value: harmless if it goes through.
    await refused('ISU.userCannotEditRequest', async () => { await request('PATCH', `${BO}/comsAssignableRoles/${r.id}`, token, { notes: r.notes ?? '' }); return {}; }, async () => {});
  });
}

// ═══ Purge: empty the audit log and the bulk-run data before a demo (dry run unless --apply) ═══
// Deletes EVERY record in these collections, not only test ones. Role requests linked to a review
// event can't be deleted (Workday keeps the event), so they stay; test orgs are inactivated by cleanup.
const PURGE_COLLECTIONS = ['comsBulkRowResults', 'comsBulkRuns', 'comsBulkUploads', 'comsAuditLogs'];
async function purge(token) {
  const APPLY = argv.includes('--apply');
  console.log(`\n-- Purge (${APPLY ? 'APPLY' : 'DRY RUN: nothing will change'}) --`);
  for (const c of PURGE_COLLECTIONS) {
    let rows = [];
    try { rows = await readAll(token, c); } catch (e) { warn(`Purge.read ${c}`, e.message.slice(0, 200)); continue; }
    console.log(`${c}: ${rows.length} record(s)`);
    if (!APPLY) continue;
    let ok = 0, bad = 0;
    for (const r of rows) {
      try { await request('DELETE', `${BO}/${c}/${r.id}`, token); ok++; } catch (e) { bad++; if (bad <= 3) console.log(`   could not delete ${r.id}: ${e.message.slice(0, 160)}`); }
    }
    (bad ? fail : pass)(`Purge.${c}`, `deleted ${ok}, failed ${bad}`);
  }
  if (!APPLY) pass('Purge.dryRun', `would delete every record in ${PURGE_COLLECTIONS.join(', ')}`);
}

// ═══ Application pattern schemas (tools/pattern_schemas.json) → COMSApplication records ═══
const SCHEMA_FILE = path.join(__dirname, '..', 'tools', 'pattern_schemas.json');
function loadSchemas() {
  const f = JSON.parse(fs.readFileSync(SCHEMA_FILE, 'utf8'));
  return f.applications.map((a) => {
    const fields = a.fields || f.fieldSets[a.fieldsFrom];
    return { ...a, fields, schema: { prefixes: a.prefixes, fields } };
  });
}
async function seedApps(token) {
  const APPLY = argv.includes('--apply');
  console.log(`\n-- Seed application records (${APPLY ? 'APPLY' : 'DRY RUN'}) --`);
  const have = (await request('GET', `${BO}/comsApplications?limit=100`, token)).data || [];
  for (const a of loadSchemas()) {
    const body = { name: a.name, appId: a.appId, orgType: a.appId, orgSubtype: 'X:SHELL', namePrefix: a.prefixes.join(','),
      patternSchema: JSON.stringify(a.schema), active: true, description: `Pattern format from Application Patterns.xlsx: ${a.prefixes.join('/')} + ${a.fields.map((x) => x.fieldLabel).join(', ')}` };
    const cur = have.find((r) => r.appId === a.appId);
    // An existing record keeps its name, org type and subtype (X:CLW was set up by hand); only the pattern format changes.
    const same = cur && cur.namePrefix === body.namePrefix && cur.patternSchema === body.patternSchema;
    // Formats are edited on the Application Patterns page now (2026-11-04), so an existing record is only replaced
    // from tools/pattern_schemas.json with --overwrite; by default this only creates missing applications.
    const keep = cur && !same && !argv.includes('--overwrite');
    console.log(`   ${cur ? (same ? 'unchanged' : (keep ? 'kept (differs; edited in the app? --overwrite replaces it)' : 'update')) : 'create'}  ${a.appId}  ${body.namePrefix}  [${a.fields.map((x) => x.fieldLabel).join(', ')}]`);
    if (!APPLY || same || keep) continue;
    await test(`Seed.${a.appId}`, async () => {
      if (cur) await request('PATCH', `${BO}/comsApplications/${cur.id}`, token, { namePrefix: body.namePrefix, patternSchema: body.patternSchema });
      else await request('POST', `${BO}/comsApplications`, token, body);
      pass(`Seed.${a.appId}`, cur ? 'updated' : 'created');
    });
  }
  const after = (await request('GET', `${BO}/comsApplications?limit=100`, token)).data || [];
  for (const a of loadSchemas()) {
    const r = after.find((x) => x.appId === a.appId);
    const want = JSON.stringify(a.schema);
    if (r && r.patternSchema !== want) fail(`Seed.stored ${a.appId}`, `patternSchema stored ${String(r.patternSchema || '').length} of ${want.length} characters`);
  }
  pass('Seed.apps', `${after.length} application records (${after.filter((r) => r.patternSchema).length} with a pattern schema)`);
}

// Guard check without creating anything: every launch uses effective date 2026-02-30, which Workday rejects,
// so even a name the guard lets through creates nothing. Read the result per launch in the app Logs
// (CheckPatternName passes for "accept" names and stops "reject" names before CallAddUpdateOrganization).
async function patternGuard(token, me) {
  console.log('\n-- Pattern guard launches (effective date 2026-02-30: nothing can be created) --');
  const apps = (await request('GET', `${BO}/comsApplications?limit=100`, token)).data || [];
  const id = (code) => (apps.find((a) => a.appId === code) || {}).id;
  const cases = [
    ['accept', 'X:CLW', 'X:CLW:PATTERN:ZZZZ:ZZZZ_V:999:999:2027W2'],
    ['accept', 'X:BPMS(AOC)', 'X:BPMS(AOC):CP:ZZZZ_V:9*'],
    ['accept', 'X:ADM', 'X:ADM:KEYCLOAK:ZZGUARDCHECK'],
    ['reject', 'X:BPMS(AOC)', 'X:BPMS(AOC):XX:MECH_V:1*'],
    ['reject', 'X:BPMS(AOC)', 'X:BPMS(AOC):CP:MECH_V'],
    ['reject', 'X:BPMS(AOC)', 'X:BPMS(AOC):CP:mech_v:100'],
    ['reject', 'X:ADM', 'X:ADM:ORG:ANY'],
    ['reject', 'X:ADM', 'X:ADM:AAP:A:B'],
    ['reject', 'X:CLW', 'X:CLW:ORG:MATH'],
  ];
  for (const [want, app, name] of cases) {
    if (!id(app)) { warn(`Guard.${name}`, `no record for ${app}`); continue; }
    await launch(token, 'IORC_0037_XFD_SEC_Create_Pattern_Shell_Org', { comsAppId: id(app), patternName: name, workerId: me.id, attribute1: '', attribute2: '', attribute3: '', attribute5: '',
      effectiveDate: '2026-02-30', changedBy: me.descriptor, changedByWid: me.id, timestamp: new Date().toISOString().replace(/\.\d+Z$/, 'Z') });
    console.log(`   launched  expect ${want}  ${name}`);
    await sleep(1500);
  }
  await sleep(20000);
  const created = ((await wql(token, "SELECT code FROM topLevelOrganizations WHERE code contains 'X:'", 10000)).data || []).map((o) => o.code);
  const leaked = cases.map((c) => c[2]).filter((n) => created.includes(n));
  if (leaked.length) fail('Guard.nothingCreated', `created: ${leaked.join(', ')}`);
  else pass('Guard.nothingCreated', `${cases.length} launches, no new organization (check CheckPatternName per launch in the app Logs)`);
}

// ═══ Org guard: IORC_0037_XFD_SEC_Create_Application_Shell_Org's CheckOrgName (2026-11-05: X:META for a new application) ═══
// Every launch has an impossible effective date, so even a launch that passes the guard is rejected by Workday
// inside IORC_0037_XFD_SEC_Sub_Create_Shell_Organization and nothing is created. Bad input must stop at CheckOrgName, before any Workday call.
async function orgGuard(token, me) {
  console.log('\n-- Org guard launches (effective date NOTADATE: nothing can be created) --');
  const who = () => ({ changedBy: me.descriptor, changedByWid: me.id, timestamp: new Date().toISOString().replace(/\.\d+Z$/, 'Z') });
  const txt = (r) => (typeof r === 'string' ? r : JSON.stringify(r));
  const GUARD = /IORC_0037_XFD_SEC_Create_Application_Shell_Org\.CheckOrgName/;
  const WORKDAY = /IORC_0037_XFD_SEC_Sub_Create_Shell_Organization/;
  const cases = [
    ['workday', 'TSTGUARD',  'TSTGUARD',           'X:META',  'new application code without X: (allowed since 2026-11-06)'],
    ['guard',   'X:TST',     'X:ADM:TEST:GUARD',   'X:SHELL', 'name not under its type (type X:TST)'],
    ['guard',   'X:TST:ONE', 'X:TST:ONE:GUARD',    'X:SHELL', 'application type with two parts'],
    ['guard',   'X:ADM',     'X:CLW:TEST:GUARD',   'X:SHELL', 'name not under its type'],
    ['guard',   'X:TSTGUARD','X:TSTGUARD',         'X:SHELL', 'new application as X:SHELL'],
    ['guard',   'X:ADM',     'X:ADM:TEST GUARD',   'X:SHELL', 'space in name'],
    ['guard',   'X:ADM',     'X:ADM:X:CLW:GUARD',  'X:META',  'second X: after the application'],
    ['workday', 'X:TSTGUARD','X:TSTGUARD',         'X:META',  'new application, X:META'],
    ['workday', 'X:ADM',     'X:ADM:TEST:GUARD',   'X:SHELL', 'under an application'],
    ['workday', 'X:ADM',     'X:ADM:TEST:GUARDMETA','X:META', 'X:META under an application'],
  ];
  const auditTotal = async () => (await request('GET', `${BO}/comsAuditLogs?limit=1`, token)).total;
  const orgCodes = async () => ((await wql(token, "SELECT code FROM topLevelOrganizations WHERE code contains 'X:'", 10000)).data || []).map((o) => o.code);
  const existed = new Set(await orgCodes());
  const before = await auditTotal();
  for (const [want, type, name, subtype, label] of cases) {
    await test(`OrgGuard.${label}`, async () => {
      const r = txt(await launch(token, 'IORC_0037_XFD_SEC_Create_Application_Shell_Org', { comsAppId: type, orgType: type, organizationName: name, organizationCode: name,
        orgSubtype: subtype, workerId: me.id, effectiveDate: 'NOTADATE', ...who() }));
      if (!/Completed with error/.test(r)) throw new Error(`expected a rejected run, got: ${r.slice(0, 300)}`);
      if (want === 'guard' && !GUARD.test(r)) throw new Error(`expected CheckOrgName to stop it, got: ${r.slice(0, 300)}`);
      if (want === 'workday' && (GUARD.test(r) || !WORKDAY.test(r))) throw new Error(`expected it to pass CheckOrgName and reach Workday, got: ${r.slice(0, 300)}`);
      pass(`OrgGuard.${label}`, `${want === 'guard' ? 'stopped by CheckOrgName' : 'passed the guard, Workday rejected the date'}: ${r.slice(0, 160)}`);
    });
    await sleep(1500);
  }

  // What the Add Shell Org page sends (presentation/newShellOrg.pmd onSubmit, built by tools/new_shell_org_meta.py),
  // mirrored here: with an application, the name starts with its ID once (typed part or full name); without one (X:META)
  // the code is the whole name and the type. Each launch must pass CheckOrgName and reach Workday with exactly that name.
  await test('OrgGuard.pageMirror', async () => {
    const page = JSON.parse(fs.readFileSync(path.join(ROOT, 'presentation/newShellOrg.pmd'), 'utf8'));
    const src = page.onSubmit;
    for (const line of ["let lname = comsShellOrg.orgName(ac, oc, meta);", "let lot = comsShellOrg.orgType(ac, oc, meta);",
      "let lcode = comsShellOrg.orgCode(ac, oc, meta);", "'ot': lot.urlEncode()", "'on': lname.urlEncode()", "'oc': lcode.urlEncode()"]) {
      if (!src.includes(line)) throw new Error(`the page's launch changed, update this mirror: missing ${line}`);
    }
    const ep = page.endPoints.find((e) => e.name === 'launchAddShellOrg').url;
    if (ep.includes('comsAppId')) throw new Error('the launch sends comsAppId again; update the mirror');
    const script = fs.readFileSync(path.join(ROOT, 'presentation/scripts/comsShellOrg.script'), 'utf8');
    for (const line of ["baseOf(a) + '(' + subOf(a, c) + ')'", "(a == '' || meta) ? orgName(a, code, meta) : a",
      "(a == '' || meta) ? orgName(a, code, meta) : orgName(a, code, meta).substringAfter(a + ':')"]) {
      if (!script.includes(line)) throw new Error(`comsShellOrg.script changed, update this mirror: missing ${line}`);
    }
    pass('OrgGuard.pageMirror', 'the mirror matches the page and comsShellOrg.script');
  });
  // comsShellOrg.script, mirrored
  const baseOf = (a) => (a.includes('(') ? a.slice(0, a.indexOf('(')) : a);
  const subOf = (a, c) => { const b = baseOf(a); let x = c.startsWith(b + '(') ? c.slice(b.length + 1) : (c.startsWith('(') ? c.slice(1) : c); return x.endsWith(')') ? x.slice(0, -1) : x; };
  const orgName = (a, c, meta) => (!a ? c : meta ? `${baseOf(a)}(${subOf(a, c)})` : c.startsWith(a + ':') ? c : `${a}:${c}`);
  const pageParams = (subtype, ac, typed) => {
    const meta = subtype === 'X:META'; const oc = typed.trim(); const n = orgName(ac, oc, meta);
    const lot = (!ac || meta) ? n : ac; const lcode = (!ac || meta) ? n : n.slice(ac.length + 1);
    return { orgType: lot, organizationName: n, organizationCode: lcode, orgSubtype: subtype };
  };
  const pageCases = [
    ['X:SHELL', 'X:ADM', 'TEST:GUARDPAGE', 'X:ADM:TEST:GUARDPAGE', 'TEST:GUARDPAGE', 'shell, part after the application'],
    ['X:SHELL', 'X:ADM', 'X:ADM:TEST:GUARDPAGE', 'X:ADM:TEST:GUARDPAGE', 'TEST:GUARDPAGE', 'shell, full name typed'],
    ['X:META', 'X:LLIS', 'TSTGUARD', 'X:LLIS(TSTGUARD)', 'X:LLIS(TSTGUARD)', 'meta under an application, brackets'],
    ['X:META', 'X:LLIS', 'X:LLIS(TSTGUARD)', 'X:LLIS(TSTGUARD)', 'X:LLIS(TSTGUARD)', 'meta under an application, full name'],
    ['X:META', 'X:BPMS(AOC)', 'TSTGUARD', 'X:BPMS(TSTGUARD)', 'X:BPMS(TSTGUARD)', 'meta under a bracketed application'],
    ['X:META', '', 'X:TSTGUARDPAGE', 'X:TSTGUARDPAGE', 'X:TSTGUARDPAGE', 'meta, new application'],
    ['X:META', '', 'TSTGUARDPAGE', 'TSTGUARDPAGE', 'TSTGUARDPAGE', 'meta, new application code without X:'],
    ['X:SHELL', 'X:BPMS(AOC)', 'ORG:TST', 'X:BPMS(AOC):ORG:TST', 'ORG:TST', 'shell under a bracketed application'],
  ];
  for (const [subtype, ac, typed, wantName, wantCode, label] of pageCases) {
    await test(`OrgGuard.page ${label}`, async () => {
      const prm = pageParams(subtype, ac, typed);
      if (prm.organizationName !== wantName || prm.organizationCode !== wantCode) throw new Error(`page would send ${JSON.stringify(prm)}`);
      const r = txt(await launch(token, 'IORC_0037_XFD_SEC_Create_Application_Shell_Org', { ...prm, workerId: me.id, effectiveDate: 'NOTADATE', ...who() }));
      if (GUARD.test(r)) throw new Error(`CheckOrgName refused what the page sends: ${r.slice(0, 300)}`);
      if (!r.includes(`Workday rejected the request for ${wantName} @`)) throw new Error(`expected Workday to get ${wantName}, got: ${r.slice(0, 300)}`);
      pass(`OrgGuard.page ${label}`, `type ${prm.orgType}, name ${prm.organizationName}, code ${prm.organizationCode}: reached Workday intact`);
    });
    await sleep(1500);
  }
  await sleep(5000);
  const after = await auditTotal();
  if (after !== before) fail('OrgGuard.noAudit', `${after - before} audit record(s) written`);
  else pass('OrgGuard.noAudit', `${cases.length + pageCases.length} launches, no audit record`);
  const created = await orgCodes();
  const leaked = [...cases.map((c) => c[2]), ...pageCases.map((c) => c[3])].filter((n) => created.includes(n) && !existed.has(n));
  if (leaked.length) fail('OrgGuard.nothingCreated', `created: ${leaked.join(', ')}`);
  else pass('OrgGuard.nothingCreated', 'no new organization');

  // The application pick-lists (Add Shell Org, Maintain Application Pattern's Add Application, AAA and role pages) come
  // from the customOrganizations WQL component, which sets no limit. A new application's X:META org (X:NEWAPP) must
  // appear in it, so the default must not cut the list.
  await test('Apps.listComplete', async () => {
    const q = JSON.parse(fs.readFileSync(path.join(ROOT, 'presentation/wqlQueries/customOrganizations.wqlquery'), 'utf8')).query;
    const noLimit = await request('GET', `${WQL}?query=${encodeURIComponent(q)}`, token);
    const full = await wql(token, q, 10000);
    const n0 = (noLimit.data || []).length, n1 = (full.data || []).length;
    const appOf = (c) => (c.split(':').length > 2 ? c.split(':').slice(0, 2).join(':') : c);
    const apps = [...new Set((full.data || []).map((o) => appOf(o.code || '')).filter((c) => c.startsWith('X:')))].sort();
    console.log(`   X: orgs: ${n1} (total ${full.total}); without a limit: ${n0} (total ${noLimit.total}); ${apps.length} application codes: ${apps.join(', ')}`);
    if (n1 !== full.total) throw new Error(`limit 10000 returned ${n1} of ${full.total}`);
    if (n0 < n1) throw new Error(`without a limit the query returns ${n0} of ${n1}: new applications could be missing from the pick-lists`);
    pass('Apps.listComplete', `${n1} X: organizations, ${apps.length} application codes; the default returns them all`);
  });
}

// ═══ Gateway probe: which IORC_0037_XFD_SEC_Create_Application_Shell_Org launches the API gateway refuses (HTML 403) before the orchestration runs ═══
// Every launch has effective date NOTADATE, so nothing can be created. Reports only (no failures).
async function gatewayProbe(token, me) {
  console.log('\n-- Gateway probe (IORC_0037_XFD_SEC_Create_Application_Shell_Org, effective date NOTADATE) --');
  const ts = new Date().toISOString().replace(/\.\d+Z$/, 'Z');
  const base = (type, name, code, sub) => ({ orgType: type, orgSubtype: sub, organizationName: name, organizationCode: code, workerId: me.id,
    effectiveDate: 'NOTADATE', changedBy: me.descriptor, timestamp: ts, changedByWid: me.id });
  const variants = [
    ['shell AOC as page', base('X:BPMS(AOC)', 'X:BPMS(AOC):TEST:GUARDPAGE', 'TEST:GUARDPAGE', 'X:SHELL')],
    ['shell AOC ORG:TST', base('X:BPMS(AOC)', 'X:BPMS(AOC):ORG:TST', 'ORG:TST', 'X:SHELL')],
    ['shell CRSS', base('X:BPMS(CRSS)', 'X:BPMS(CRSS):ORG:TST', 'ORG:TST', 'X:SHELL')],
    ['shell LLIS(CPE)', base('X:LLIS(CPE)', 'X:LLIS(CPE):ORG:TST', 'ORG:TST', 'X:SHELL')],
    ['shell AOC no changedBy', { ...base('X:BPMS(AOC)', 'X:BPMS(AOC):ORG:TST', 'ORG:TST', 'X:SHELL'), changedBy: '' }],
    ['shell AOC no code', { ...base('X:BPMS(AOC)', 'X:BPMS(AOC):ORG:TST', '', 'X:SHELL') }],
    ['shell AOC no workerId', { ...base('X:BPMS(AOC)', 'X:BPMS(AOC):ORG:TST', 'ORG:TST', 'X:SHELL'), workerId: '' }],
    ['meta LLIS(TST)', base('X:LLIS(TST)', 'X:LLIS(TST)', 'X:LLIS(TST)', 'X:META')],
    ['shell ADM (no brackets)', base('X:ADM', 'X:ADM:ORG:TST', 'ORG:TST', 'X:SHELL')],
  ];
  for (const [label, prm] of variants) {
    let out;
    try { out = String(typeof (await launch(token, 'IORC_0037_XFD_SEC_Create_Application_Shell_Org', prm)) === 'string' ? 'reached the orchestration' : 'reached the orchestration'); }
    catch (e) { out = /HTTP 403/.test(e.message) ? 'GATEWAY 403' : e.message.slice(0, 120); }
    console.log(`   ${out.padEnd(26)} ${label}`);
    await sleep(1500);
  }
  pass('Gateway.probe', 'see the lines above');
}

// ═══ Prompt values probe (read-only): Workday's own prompt values (Graph "prompts" query) vs the app's WQL searches ═══
// developer.workday.com "Input Prompt Values for Mutations". Lists which mutations offer prompts for the app's subjects.
async function promptsProbe(token) {
  console.log('\n-- Prompt values probe (read-only) --');
  const T = async (name) => (await gql(token, `query { __type(name: "${name}") { name kind fields { name args { name } type { name kind ofType { name kind ofType { name kind } } } } } }`)).__type;
  const named = (t) => (t ? (t.name || named(t.ofType)) : null);
  const root = await T('Mutation_Prompts');
  if (!root) { console.log('   no Mutation_Prompts type'); return pass('Prompts.probe', 'no Mutation_Prompts type'); }
  console.log(`   Mutation_Prompts: ${root.fields.length} mutations with prompt values`);
  const want = /role|organi|position|academic|unit|supervisory|custom|hierarch/i;
  const hits = root.fields.filter((f) => want.test(f.name));
  console.log(`   mutations matching role/organization/position/academic: ${hits.map((f) => f.name).join(', ') || 'none'}`);
  const seen = new Set(); const leaves = [];
  const walk = async (typeName, pathTxt, depth) => {
    if (!typeName || seen.has(typeName + pathTxt) || depth > 4) return;
    seen.add(typeName + pathTxt);
    const t = await T(typeName); if (!t || !t.fields) return;
    for (const f of t.fields) {
      const tn = named(f.type);
      const args = (f.args || []).map((a) => a.name);
      if (args.includes('search') || args.includes('promptPath')) leaves.push(`${pathTxt}.${f.name}`);
      else if (tn && /Prompts$/.test(tn)) await walk(tn, `${pathTxt}.${f.name}`, depth + 1);
    }
  };
  for (const f of hits.slice(0, 25)) await walk(named(f.type), f.name, 1);
  const rel = leaves.filter((l) => /position|organi|academic|unit|role|supervisory/i.test(l.split('.').pop()));
  console.log(`   prompt ID fields under them: ${leaves.length}; about positions/organizations/academic units/roles: ${rel.length}`);
  rel.slice(0, 80).forEach((l) => console.log(`   FIELD ${l}`));
  console.log(`   all mutations with prompts: ${root.fields.map((f) => f.name).join(', ')}`);
  // Baseline: the app's current searches (the WQL the pages send), median of 3, with realistic search text
  const med = async (label, f) => {
    const ms = []; let info = '';
    for (let i = 0; i < 3; i++) { const t0 = Date.now(); try { info = await f(); } catch (e) { info = 'ERROR ' + e.message.slice(0, 120); } ms.push(Date.now() - t0); }
    console.log(`   TIME ${label}: median ${ms.slice().sort((a, b) => a - b)[1]} ms (${ms.join(', ')}) · ${info}`);
  };
  const n = (r) => `${(r.data || []).length} rows`;
  await med('FUH search "X:B"', async () => n(await wql(token, "SELECT workdayID, organization1, code FROM customOrganizations WHERE type1 in (b40d8b016367100175b147f364840000) AND code contains 'X:B'", 100)));
  await med('Academic Unit search "Math"', async () => n(await wql(token, "SELECT workdayID, academicUnit, academicUnitName FROM academicUnits WHERE inactive = false AND academicUnitName contains 'Math'", 100)));
  await med('Position search "Manager"', async () => n(await wql(token, "SELECT cf_PositionID, workdayID, position_PositionManagement, cf_PositionIsFilled, cf_PositionText FROM allPositions WHERE supervisoryOrganization is not empty AND cf_PositionText contains 'Manager'", 100)));
  await med('REST values supervisoryOrganization (no search; top level)', async () => { const r = await request('GET', `${API}/staffing/v6/values/jobChangesGroup/supervisoryOrganization/`, token); return `${(r.data || []).length} entries${(r.data || [])[0] ? ', first: ' + (r.data[0].descriptor || '') : ''}`; });
  pass('Prompts.probe', `${root.fields.length} mutations with prompts, ${hits.length} on the app's subjects, ${rel.length} matching ID fields`);
}

// ═══ Position search timing (read-only): the four pages' position search and candidate changes ═══
async function posSearchTiming(token) {
  console.log('\n-- Position search timing (read-only, median of 5) --');
  const run = async (q) => request('GET', `${WQL}?query=${encodeURIComponent(q)}${''}`, token);
  const runL = async (q, lim) => request('GET', `${WQL}?limit=${lim}&query=${encodeURIComponent(q)}`, token);
  const med = async (label, f) => {
    const ms = []; let info = '';
    for (let i = 0; i < 5; i++) { const t0 = Date.now(); try { info = await f(); } catch (e) { info = 'ERROR ' + e.message.slice(0, 100); } ms.push(Date.now() - t0); }
    const m = ms.slice().sort((a, b) => a - b)[2];
    console.log(`   TIME ${label}: median ${m} ms (${ms.join(', ')}) · ${info}`);
    return m;
  };
  const F5 = 'cf_PositionID, workdayID, position_PositionManagement, cf_PositionIsFilled, cf_PositionText';
  const F4 = 'cf_PositionID, workdayID, position_PositionManagement, cf_PositionText';
  const W = (t) => `supervisoryOrganization is not empty AND cf_PositionText contains '${t}'`;
  const rows = (r) => `${(r.data || []).length} rows (total ${r.total ?? '?'}), ${Math.round(JSON.stringify(r).length / 1024)} KB`;
  for (const t of ['a', 'Manager', 'Director', 'P-00', 'Advisor']) {
    console.log(`   -- "${t}"`);
    await med(`now: 5 fields, no limit`, async () => rows(await run(`SELECT ${F5} FROM allPositions WHERE ${W(t)}`)));
    await med(`5 fields, limit 50`, async () => rows(await runL(`SELECT ${F5} FROM allPositions WHERE ${W(t)}`, 50)));
    await med(`4 fields, limit 50`, async () => rows(await runL(`SELECT ${F4} FROM allPositions WHERE ${W(t)}`, 50)));
    await med(`4 fields, limit 25`, async () => rows(await runL(`SELECT ${F4} FROM allPositions WHERE ${W(t)}`, 25)));
    await med(`(info) 4 fields, limit 50, no supervisory filter`, async () => rows(await runL(`SELECT ${F4} FROM allPositions WHERE cf_PositionText contains '${t}'`, 50)));
  }
  pass('PosSearch.timing', 'see lines above');
}

// ═══ Position tree probe (read-only): can positions be browsed by supervisory organization? ═══
async function posTreeProbe(token) {
  console.log('\n-- Position tree probe (read-only) --');
  const t0 = Date.now();
  const all = (await wql(token, 'SELECT cf_PositionID, workdayID, supervisoryOrganization FROM allPositions WHERE supervisoryOrganization is not empty', 10000)).data || [];
  console.log(`   positions with a supervisory org: ${all.length} (${Date.now() - t0} ms)`);
  const by = {};
  all.forEach((p) => { const o = p.supervisoryOrganization; const k = (o && (o.descriptor || (o[0] && o[0].descriptor))) || '?'; const id = (o && (o.id || (o[0] && o[0].id))) || ''; (by[k] = by[k] || { id, n: 0 }).n++; });
  const sizes = Object.values(by).map((x) => x.n).sort((a, b) => a - b);
  const q = (f) => sizes[Math.floor((sizes.length - 1) * f)];
  console.log(`   supervisory orgs holding them: ${sizes.length}; positions per org: median ${q(0.5)}, 90th pct ${q(0.9)}, max ${sizes[sizes.length - 1]}`);
  Object.entries(by).sort((a, b) => b[1].n - a[1].n).slice(0, 5).forEach(([k, v]) => console.log(`   BIG ${v.n} · ${k}`));
  const big = Object.entries(by).sort((a, b) => b[1].n - a[1].n)[0];
  if (big && big[1].id) {
    const ms = [];
    for (let i = 0; i < 3; i++) { const s = Date.now(); await wql(token, `SELECT cf_PositionID, workdayID, position_PositionManagement, cf_PositionText FROM allPositions WHERE supervisoryOrganization in ('${big[1].id}')`, 200); ms.push(Date.now() - s); }
    console.log(`   TIME positions in one org (largest, ${big[1].n}): ${ms.join(', ')} ms`);
  }
  // Workday's own supervisory-org tree (the Staffing "values" list from developer.workday.com "Concept: Multilevel Lists")
  try {
    const s = Date.now(); const r = await request('GET', `${API}/staffing/v6/values/jobChangesGroup/supervisoryOrganization/`, token);
    console.log(`   REST tree root (${Date.now() - s} ms): ${(r.data || []).map((x) => x.descriptor).join(' | ')}`);
    for (const node of (r.data || []).slice(0, 3)) {
      if (!node.href) continue;
      const s2 = Date.now(); const c = await request('GET', node.href, token);
      const d = c.data || [];
      console.log(`   REST tree "${node.descriptor}" (${Date.now() - s2} ms): ${d.length} entries; first: ${d.slice(0, 3).map((x) => x.descriptor).join(' | ')}; deeper levels: ${d.some((x) => x.href) ? 'yes' : 'no'}`);
    }
  } catch (e) { console.log('   REST tree error ' + e.message.slice(0, 150)); }
  // details for a page build: ids, hrefs, depth of each root, manager -> orgs, tree org id -> positions
  try {
    const orgIds = new Set(all.map((p) => { const o = p.supervisoryOrganization; return (o && (o.id || (o[0] && o[0].id))) || ''; }));
    const r = await request('GET', `${API}/staffing/v6/values/jobChangesGroup/supervisoryOrganization/`, token);
    console.log('   ROOT ids: ' + (r.data || []).map((x) => `${x.descriptor}=${x.id} href=${(x.href || '').replace(API, '')}`).join(' ; '));
    for (const node of (r.data || [])) {
      if (!node.href) continue;
      const s = Date.now(); const c = await request('GET', node.href + (node.href.includes('?') ? '&' : '?') + 'limit=100', token); const d = c.data || [];
      const f = d[0] || {};
      console.log(`   NODE "${node.descriptor}" ${Date.now() - s} ms total=${c.total} got=${d.length} first=${f.descriptor}|id=${f.id}|href=${(f.href || '').replace(API, '')} orgWithPositions=${d.filter((x) => orgIds.has(x.id)).length}`);
      if (f.href) {
        const g = await request('GET', f.href, token); const gd = g.data || [];
        console.log(`     L2 of "${f.descriptor}": total=${g.total} first=${(gd[0] || {}).descriptor}|id=${(gd[0] || {}).id}|href=${((gd[0] || {}).href || '').replace(API, '')} orgWithPositions=${gd.filter((x) => orgIds.has(x.id)).length}`);
      }
    }
    const az = (r.data || []).find((x) => x.descriptor === 'Supervisory Organization');
    if (az) { const p1 = await request('GET', az.href + '?limit=100&offset=0', token); const p2 = await request('GET', az.href + '?limit=100&offset=100', token);
      const names = [...(p1.data || []), ...(p2.data || [])].map((x) => x.descriptor);
      console.log(`   PAGE2 A-Z total=${p1.total} page1=${(p1.data || []).length} page2=${(p2.data || []).length} distinct=${new Set(names).size} last=${names[names.length - 1]}`); }
    const mg = await request('GET', `${API}/staffing/v6/values/jobChangesGroup/supervisoryOrganization/`, token);
    const byMgr = (mg.data || []).find((x) => /by Manager$/.test(x.descriptor));
    if (byMgr) {
      const mlist = (await request('GET', byMgr.href + '?limit=5', token)).data || [];
      for (const m of mlist.slice(0, 3)) {
        try { const s = Date.now(); const so = await request('GET', `${API}/common/v1/workers/${m.id}/supervisoryOrganizationsManaged`, token);
          const sd = so.data || []; console.log(`   MGR ${m.descriptor} (${m.id}) ${Date.now() - s} ms orgsManaged=${sd.length} first=${(sd[0] || {}).descriptor}|${(sd[0] || {}).id} withPositions=${sd.filter((x) => orgIds.has(x.id)).length}`);
          if (sd[0]) { const s2 = Date.now(); const pq = await wql(token, `SELECT cf_PositionID, position_PositionManagement, cf_PositionText FROM allPositions WHERE supervisoryOrganization in ('${sd[0].id}')`, 200); console.log(`     positions in ${sd[0].descriptor}: ${(pq.data || []).length} (${Date.now() - s2} ms) e.g. ${((pq.data || [])[0] || {}).cf_PositionID}`); }
        } catch (e) { console.log(`   MGR ${m.descriptor} error ${e.message.slice(0, 120)}`); }
      }
    }
  } catch (e) { console.log('   detail error ' + e.message.slice(0, 200)); }
  pass('PosTree.probe', 'see lines above');
}

// ═══ Academic Unit / FUH tree probe (read-only): what parent links do the two lists have? ═══
async function orgTreeProbe(token) {
  console.log('\n-- Academic Unit / FUH tree probe (read-only) --');
  for (const alias of ['academicUnits', 'customOrganizations', 'academicUnitHierarchies', 'organizations']) {
    try {
      const ds = await request('GET', `${API}/wql/v1/dataSources?alias=${alias}`, token);
      const id = (ds.data || [])[0]?.id; if (!id) { console.log(`   DS ${alias}: none`); continue; }
      let all = [];
      for (let off = 0; off < 3000; off += 100) { const page = (await request('GET', `${API}/wql/v1/dataSources/${id}/fields?limit=100&offset=${off}`, token)).data || []; all = all.concat(page); if (page.length < 100) break; }
      console.log(`   DS ${alias}: ${all.length} fields`);
      all.filter((x) => /superior|parent|subordinate|hierarch|included|level|top|child|inactive|type/i.test(`${x.alias} ${x.descriptor}`)).slice(0, 40).forEach((x) => console.log(`     FIELD ${alias}.${x.alias} | ${x.descriptor} | ${x.type || ''}`));
    } catch (e) { console.log(`   DS ${alias} error ${e.message.slice(0, 150)}`); }
  }
  for (const q of ['Academic Unit Hierarch', 'Functional Unit', 'Organization Hierarch', 'Superior']) {
    try { const r = await request('GET', `${API}/wql/v1/dataSources?search=${encodeURIComponent(q)}&limit=15`, token);
      (r.data || []).forEach((d) => console.log(`   DSS[${q}] ${d.alias || ''} | ${d.descriptor || ''}`)); } catch (e) { console.log(`   DSS[${q}] error ${e.message.slice(0, 100)}`); }
  }
  try { const r = await wql(token, 'SELECT workdayID, academicUnit, academicUnitName FROM academicUnits WHERE inactive = false', 10000); console.log(`   AU active count ${(r.data || []).length}`); } catch (e) { console.log('   AU count error ' + e.message.slice(0, 150)); }
  try { const r = await wql(token, 'SELECT workdayID, organization1, code FROM customOrganizations WHERE type1 in (b40d8b016367100175b147f364840000)', 10000); const d = r.data || []; console.log(`   FUH count ${d.length}; sample codes: ${d.slice(0, 8).map((x) => x.code).join(' | ')}`); } catch (e) { console.log('   FUH count error ' + e.message.slice(0, 150)); }
  // second pass: custom organization parent fields (not cf_), and the shape of both trees
  try {
    const ds = await request('GET', `${API}/wql/v1/dataSources?alias=customOrganizations`, token); const id = (ds.data || [])[0]?.id;
    let all = []; for (let off = 0; off < 3000; off += 100) { const page = (await request('GET', `${API}/wql/v1/dataSources/${id}/fields?limit=100&offset=${off}`, token)).data || []; all = all.concat(page); if (page.length < 100) break; }
    all.filter((x) => !/^cf_/.test(x.alias) && /superior|parent|subordinate|hierarch|top|level|included|inactive/i.test(`${x.alias} ${x.descriptor}`)).forEach((x) => console.log(`     CFIELD ${x.alias} | ${x.descriptor} | ${x.type || ''}`));
  } catch (e) { console.log('   CFIELD error ' + e.message.slice(0, 150)); }
  for (const f of ['superiorOrganization', 'superiorCustomOrganization', 'hierarchicParents', 'directSuperiors', 'organizationHierarchy']) {
    try {
      const r = await wql(token, `SELECT workdayID, organization1, code, ${f} FROM customOrganizations WHERE type1 in (b40d8b016367100175b147f364840000)`, 10000); const d = r.data || [];
      const parentOf = (o) => { const v = o[f]; return Array.isArray(v) ? (v[0] && v[0].id) : (v && v.id); };
      const ids = new Set(d.map((o) => o.workdayID)); const kids = {};
      d.forEach((o) => { const p = parentOf(o) || 'ROOT'; (kids[ids.has(p) ? p : (p === 'ROOT' ? 'ROOT' : 'OUTSIDE:' + p)] = kids[ids.has(p) ? p : (p === 'ROOT' ? 'ROOT' : 'OUTSIDE:' + p)] || []).push(o); });
      const depth = (wid) => { let n = 0; let cur = d.find((o) => o.workdayID === wid); while (cur && parentOf(cur) && ids.has(parentOf(cur)) && n < 30) { n++; cur = d.find((o) => o.workdayID === parentOf(cur)); } return n; };
      const roots = Object.keys(kids).filter((k) => k === 'ROOT' || k.startsWith('OUTSIDE:'));
      const sizes = Object.entries(kids).filter(([k]) => ids.has(k)).map(([, v]) => v.length).sort((a, b) => a - b);
      console.log(`   FUH via ${f}: rows ${d.length}; root groups ${roots.map((k) => k.slice(0, 40) + '=' + kids[k].length).join(', ')}; parents with children ${sizes.length}, max children ${sizes[sizes.length - 1]}, max depth ${Math.max(...d.map((o) => depth(o.workdayID)))}`);
      console.log(`     sample: ${d.slice(0, 4).map((o) => `${o.code}<-${JSON.stringify(o[f]).slice(0, 70)}`).join(' ; ')}`);
      roots.forEach((k) => console.log(`     ROOT ${k.slice(0, 50)}: ${kids[k].slice(0, 6).map((o) => o.code + ' ' + (o.organization1?.descriptor || '')).join(' | ')}`));
      break;
    } catch (e) { console.log(`   FUH via ${f}: ${e.message.slice(0, 160)}`); }
  }
  try {
    const h = await wql(token, 'SELECT workdayID, academicUnitHierarchy, directSuperiors, directSubordinates FROM academicUnitHierarchies', 10000);
    const d = h.data || []; const top = d.filter((x) => !(x.directSuperiors || []).length);
    console.log(`   AUH rows ${d.length}; top ${top.length}: ${top.slice(0, 6).map((x) => x.academicUnitHierarchy?.descriptor + '(' + (x.directSubordinates || []).length + ')').join(' | ')}; sample ${JSON.stringify(d[0]).slice(0, 220)}`);
  } catch (e) { console.log('   AUH error ' + e.message.slice(0, 200)); }
  try {
    const u = await wql(token, 'SELECT workdayID, academicUnit, hierarchicParents, academicUnitIsTopNode FROM academicUnits WHERE inactive = false', 10000);
    const d = u.data || []; const noParent = d.filter((x) => !(x.hierarchicParents || []).length);
    const per = {}; d.forEach((x) => (x.hierarchicParents || []).forEach((p) => { per[p.descriptor] = (per[p.descriptor] || 0) + 1; }));
    console.log(`   AU rows ${d.length}; without hierarchy ${noParent.length}; topNode ${d.filter((x) => x.academicUnitIsTopNode).length}; per hierarchy (top 8): ${Object.entries(per).sort((a, b) => b[1] - a[1]).slice(0, 8).map(([k, v]) => k + '=' + v).join(' | ')}; sample ${JSON.stringify(d[0]).slice(0, 200)}`);
  } catch (e) { console.log('   AU parents error ' + e.message.slice(0, 200)); }
  // third pass: other link fields
  const show = (v) => Array.isArray(v) ? v.map((x) => x.descriptor || x.id).slice(0, 3).join('+') + (v.length > 3 ? `+${v.length - 3}` : '') : (v && typeof v === 'object' ? (v.descriptor || v.id) : String(v ?? ''));
  for (const f of ['includedByOrganizations', 'includedOrganizations', 'subordinateOrganizations', 'level01FromTheTop', 'organizationLevelFromTop', 'superiorOrganizationCode', 'subtype']) {
    try {
      const r = await wql(token, `SELECT code, ${f} FROM customOrganizations WHERE type1 in (b40d8b016367100175b147f364840000)`, 10000); const d = r.data || [];
      const filled = d.filter((o) => { const v = o[f]; return Array.isArray(v) ? v.length : (v !== undefined && v !== null && v !== ''); });
      const dist = {}; filled.forEach((o) => { const k = show(o[f]).slice(0, 40); dist[k] = (dist[k] || 0) + 1; });
      console.log(`   FUH2 ${f}: filled ${filled.length}/${d.length}; values ${Object.entries(dist).sort((a, b) => b[1] - a[1]).slice(0, 6).map(([k, v]) => k + '=' + v).join(' | ')}`);
    } catch (e) { console.log(`   FUH2 ${f}: ${e.message.slice(0, 140)}`); }
  }
  for (const f of ['academicUnitSubtype', 'subordinateAcademicUnits', 'superiorAcademicUnit', 'academicUnitAndSuperiorAcademicUnits', 'includedInAcademicUnitHierarchies_TopNode', 'academicLevel']) {
    try {
      const r = await wql(token, `SELECT academicUnit, ${f} FROM academicUnits WHERE inactive = false`, 10000); const d = r.data || [];
      const filled = d.filter((o) => { const v = o[f]; return Array.isArray(v) ? v.length : (v !== undefined && v !== null && v !== ''); });
      const dist = {}; filled.forEach((o) => { const k = show(o[f]).slice(0, 50); dist[k] = (dist[k] || 0) + 1; });
      console.log(`   AU2 ${f}: filled ${filled.length}/${d.length}; values ${Object.entries(dist).sort((a, b) => b[1] - a[1]).slice(0, 6).map(([k, v]) => k + '=' + v).join(' | ')}`);
    } catch (e) { console.log(`   AU2 ${f}: ${e.message.slice(0, 140)}`); }
  }
  try { const h = await wql(token, 'SELECT workdayID, academicUnitHierarchy FROM academicUnitHierarchies', 10000); console.log(`   AUH2 rows ${(h.data || []).length}: ${(h.data || []).slice(0, 5).map((x) => show(x.academicUnitHierarchy)).join(' | ')}`); } catch (e) { console.log('   AUH2 ' + e.message.slice(0, 160)); }
  try {
    const r = await wql(token, 'SELECT workdayID, organization1, subtype FROM customOrganizations WHERE type1 in (b40d8b016367100175b147f364840000)', 10000); const d = r.data || [];
    const dep = d.filter((o) => (o.subtype?.descriptor || '') === '07 Department');
    const first = {}; dep.forEach((o) => { const n = o.organization1?.descriptor; const k = n === undefined ? 'UNDEF' : (n === '' ? 'EMPTY' : JSON.stringify(n[0])); first[k] = (first[k] || 0) + 1; });
    console.log(`   DEPT rows ${dep.length}; first chars ${JSON.stringify(first)}; samples ${dep.slice(0, 5).map((o) => JSON.stringify(o.organization1)).join(' ; ')}`);
    const ids = new Set(); let dup = 0; d.forEach((o) => { if (ids.has(o.workdayID)) dup++; ids.add(o.workdayID); }); console.log(`   FUH distinct WIDs ${ids.size} of ${d.length} rows (dup ${dup})`);
  } catch (e) { console.log('   DEPT error ' + e.message.slice(0, 150)); }
  for (const [n, q] of [['fuhTreeAll', 'SELECT workdayID, organization1, subtype FROM customOrganizations WHERE type1 in (b40d8b016367100175b147f364840000)'], ['auTreeAll', 'SELECT workdayID, academicUnit, academicUnitSubtype FROM academicUnits WHERE inactive = false']]) {
    const ms = []; let bytes = 0;
    for (let i = 0; i < 5; i++) { const t = Date.now(); const r = await wql(token, q, 10000); ms.push(Date.now() - t); bytes = JSON.stringify(r).length; }
    ms.sort((a, b) => a - b); console.log(`   TIME ${n}: median ${ms[2]} ms (${ms.join(', ')}), ${Math.round(bytes / 1024)} KB`);
  }
  try { const q = JSON.parse(fs.readFileSync(path.join(ROOT, 'presentation/wqlQueries/allAAArolesinTenant.wqlquery'), 'utf8')).query; const r = await wql(token, q, 1000); console.log(`   AAA roles: ${(r.data || []).map((x) => x.role?.descriptor).join(' | ')}`); } catch (e) { console.log('   AAA roles error ' + e.message.slice(0, 120)); }
  pass('OrgTree.probe', 'see lines above');
}

// ═══ AAA role names use the full application ID (read-only; tools/aaa_full_app_id.py, 2026-11-05) ═══
// Read-only: every application (same rule as Add Shell Org / AAA), with counts, for the Shell Org Manager
// application-filter design (2026-11-05). Prints one APPSUMMARY JSON line.
async function appSummary(token) {
  console.log('\n-- Application summary (read-only) --');
  const wqlFile = (id) => JSON.parse(fs.readFileSync(path.join(ROOT, 'presentation/wqlQueries', id + '.wqlquery'), 'utf8')).query;
  const appOf = (code) => code.includes('(') ? code.split(')')[0] + ')' : (code.split(':').slice(1).join(':').includes(':') ? code.split(':')[0] + ':' + code.split(':')[1] : code);
  const familyOf = (a) => a.includes('(') ? a.split('(')[0] : 'Standalone';
  const orgs = (await wql(token, wqlFile('allShellOrgs'), 10000)).data || [];
  const roles = (await wql(token, wqlFile('allShellAssignableRolesinTenant'), 10000)).data || [];
  const recs = await readAll(token, 'comsApplications');
  const reqs = await readAll(token, 'comsAssignableRoles');
  const audits = await readAll(token, 'comsAuditLogs');
  const apps = {};
  const get = (a) => (apps[a] = apps[a] || { id: a, family: familyOf(a), name: '', orgs: 0, active: 0, patterns: 0, roles: 0, assignments: 0, positions: 0, pending: 0, lastChange: '', hasRecord: false, recordActive: null });
  for (const o of orgs) { const a = get(appOf(o.code || '')); a.orgs++; if (o.cf_active1 !== false && o.cf_active1 !== 'false') a.active++; if ((o.code || '').includes('PATTERN')) a.patterns++; if ((o.code || '') === a.id) a.name = (o.organizationByName?.descriptor || o.organizationByName || '').toString(); }
  for (const r of roles) { const rn = (r.role?.descriptor || '').toString(); const m = rn.match(/^(X:[^:]+(?:\([^)]*\))?(?::[^:(]+)?)/); const app = m ? appOf(rn.split(':ROLE')[0]) : null; if (!app) continue; const a = get(app); a.roles++; const ras = r.roleAssignments || []; a.assignments += ras.length; a.positions += ras.reduce((n, x) => n + ((x.cf_ZCF_EE_RoleAssignedToAsPositionRestrictions || []).length || 0), 0); }
  for (const r of recs) { const a = get(r.appId || ''); a.hasRecord = true; a.recordActive = r.active; if (!a.name) a.name = r.name || ''; }
  for (const r of reqs) if (/Pending/i.test(r.status || '')) { const a = apps[r.application] || apps[appOf(r.shellOrgCode || '')]; if (a) a.pending++; }
  for (const x of audits) { const a = apps[x.application] || apps[appOf(x.coName || '')]; if (a && (x.timestamp || '') > a.lastChange) a.lastChange = x.timestamp || ''; }
  const list = Object.values(apps).filter((a) => a.id.startsWith('X:')).sort((a, b) => a.id.localeCompare(b.id));
  const fams = {}; list.forEach((a) => { fams[a.family] = (fams[a.family] || 0) + 1; });
  console.log(`   ${orgs.length} orgs, ${roles.length} shell roles, ${recs.length} pattern records -> ${list.length} applications; families ${JSON.stringify(fams)}`);
  console.log('APPSUMMARY ' + JSON.stringify(list));
  pass('Apps.summary', `${list.length} applications`);
}

async function aaaNameCheck(token) {
  console.log('\n-- AAA role name: full application ID (read-only) --');
  const check = (n, fn) => test(n, async () => pass(n, await fn()));
  const page = JSON.parse(fs.readFileSync(path.join(ROOT, 'presentation/adminProvisioning.pmd'), 'utf8'));
  const find = (n, id) => { if (!n || typeof n !== 'object') return null; if (n.id === id) return n; for (const v of Object.values(n)) { const r = find(v, id); if (r) return r; } return null; };
  const script = find(page.presentation, 'applicationDropdown').values;
  await check('AAA.listUsesFullId', async () => { if (!script.includes("code.substringBefore(')') + ')'") || script.includes("code.substringAfter('(').substringBefore(')')")) throw new Error('application list still reduces bracketed IDs'); return 'page script keeps X:APP(CODE)'; });
  const wqlFile = (id) => JSON.parse(fs.readFileSync(path.join(ROOT, 'presentation/wqlQueries', id + '.wqlquery'), 'utf8')).query;
  const orgs = (await wql(token, wqlFile('customOrganizations'), 10000)).data || [];
  // the page's own rule, in JS
  const appOf = (code) => code.includes('(') ? code.split(')')[0] + ')' : (code.split(':').slice(1).join(':').includes(':') ? code.split(':')[0] + ':' + code.split(':')[1] : code);
  const apps = []; const seen = new Set(); orgs.forEach((o) => { const a = appOf(o.code || ''); if (!seen.has(a)) { seen.add(a); apps.push(a); } });
  console.log(`   ${orgs.length} orgs -> ${apps.length} applications; bracketed: ${apps.filter((a) => a.includes('(')).join(' | ')}`);
  const roles = ((await wql(token, wqlFile('allAAArolesinTenant'), 1000)).data || []).map((r) => r.role?.descriptor || '');
  await check('AAA.duplicateCheckSeesExistingRoles', async () => {
    const miss = roles.filter((r) => { const m = r.match(/^Organizations and Roles Assignment Administrator \((.*)\)$/); return !m || !apps.some((a) => `Organizations and Roles Assignment Administrator (${a})` === r || r.startsWith(`Organizations and Roles Assignment Administrator (${a},`)); });
    if (miss.length) throw new Error('no application in the list builds: ' + miss.join(' | '));
    return `${roles.length} existing AAA role(s) match a listed application exactly: ${roles.join(' | ')}`;
  });
  await check('AAA.noEmptyOrBrokenIds', async () => {
    const bad = apps.filter((a) => !a || (a.includes('(') && !/^[^()]+\([^()]+\)$/.test(a)));
    if (bad.length) throw new Error('odd application IDs: ' + bad.join(' | '));
    return 'every bracketed ID is APP(CODE)';
  });
}

// ═══ Probe: read-only facts for building application pattern schemas ═══
// ═══ Bulk validate: one TEST batch through IORC_0037_XFD_SEC_Bulk_Role_Changes_From_Grid in VALIDATE mode (no role changes) ═══
// Proves the per-row sub-orchestration (IORC_0037_XFD_SEC_Sub_Process_Bulk_Role_Row, tools/extract_subflows.py) runs: the run must finish as
// Validated, its row must get a VALID or INVALID result, and no Role Assignment audit record may appear for it.
// Leaves a run record and two row records marked TEST<n> (bulk run data is cleared by the purge suite).
async function bulkValidate(token, me) {
  console.log('\n-- Bulk validate (writes a TEST run; changes no roles) --');
  await test('Bulk.validateRun', async () => {
    const audits = await readAll(token, 'comsAuditLogs');
    const src = audits.filter((a) => a.objectType === 'Role Assignment' && a.roleWid && a.orgWid && a.coReferenceId).pop();
    if (!src) return skip('Bulk.validateRun', 'no Role Assignment audit record to take a role, organization and position from');
    const ref = 'TEST' + new Date().toISOString().replace(/\D/g, '').slice(0, 14);
    const stamp = new Date().toISOString().replace(/\.\d+Z$/, 'Z');
    const today = new Date(Date.now() - 8 * 3600e3).toISOString().slice(0, 10);   // tenant (Pacific) date
    await request('POST', `${BO}/comsBulkRuns`, token, { batchRef: ref, source: 'Grid', runMode: 'VALIDATE', status: 'Uploaded',
      effectiveDate: today, uploadedByName: me.descriptor, uploadedByWid: me.id, uploadedAt: stamp, changeCount: '1', summary: 'TEST validate run' });
    await request('POST', `${BO}/comsBulkRowResults`, token, { batchRef: ref + '-DRAFT', runMode: 'VALIDATE', rowAction: 'ADD', result: 'DRAFT',
      roleName: src.roleName || '', roleWid: src.roleWid, orgName: src.coName || '', orgWid: src.orgWid,
      positionId: src.coReferenceId, positionName: src.positionName || '', assigneeWid: '', timestamp: stamp });
    const auditsBefore = new Set(audits.map((a) => a.id));
    const r = await launch(token, 'IORC_0037_XFD_SEC_Bulk_Role_Changes_From_Grid', { ref, mode: 'VALIDATE', effectiveDate: today, changedBy: me.descriptor, changedByWid: me.id });
    console.log('   launch: ' + String(typeof r === 'string' ? r : JSON.stringify(r)).slice(0, 200));
    let run, rows = [];
    for (let i = 0; i < 30; i++) {
      await sleep(4000);
      run = ((await request('GET', `${BO}/comsBulkRuns?limit=100&batchRef=${encodeURIComponent(ref)}`, token)).data || [])[0];
      rows = (await request('GET', `${BO}/comsBulkRowResults?limit=100&batchRef=${encodeURIComponent(ref)}`, token)).data || [];
      if (run && /Validated|Completed|Rejected|Failed/.test(run.status || '') && rows.length) break;
    }
    if (!run || run.status !== 'Validated') throw new Error(`${ref}: run status ${run?.status} (${run?.statusMessage || ''}) after 2 minutes`);
    if (!rows.length) throw new Error(`${ref}: no row result (the per-row sub-orchestration didn't write one)`);
    const bad = rows.filter((x) => !/^(VALID|INVALID)$/.test(x.result || ''));
    if (bad.length) throw new Error(`${ref}: unexpected row result ${bad.map((x) => x.result).join(', ')}`);
    const newAudits = (await readAll(token, 'comsAuditLogs')).filter((a) => !auditsBefore.has(a.id) && (a.details || '').includes(ref));
    if (newAudits.length) throw new Error(`${ref}: VALIDATE wrote ${newAudits.length} audit record(s)`);
    pass('Bulk.validateRun', `${ref}: Validated; row ${rows[0].result}: ${rows[0].message || ''} (role ${src.roleName}, ${src.coReferenceId})`);
  });
}

// ═══ Bulk apply: one position added to the test role and removed again through the bulk-edit orchestration ═══
// IORC_0037_XFD_SEC_Bulk_Role_Changes_From_Grid → IORC_0037_XFD_SEC_Sub_Process_Bulk_Role_Row (sub-orchestration) → IORC_0037_XFD_SEC_Sub_Write_Audit_Record (sub-orchestration called by a
// sub-orchestration, 2026-11-05). Checks both audit records and that the role ends as it started. Net change: none;
// leaves two TEST bulk runs and their row records (cleared by the purge suite), like bulkvalidate.
async function bulkApply(token, me) {
  console.log('\n-- Bulk apply (adds one position to the test role, then removes it) --');
  await test('Bulk.applyAddRemove', async () => {
    const today = tenantDate();
    const readRole = async () => {
      const r = await wql(token, `SELECT role, roleAssignments{organization, cf_ZCF_EE_RoleAssignedToAsPositionRestrictions} as roleAssignments FROM assignableRoles WHERE roleName = '${TEST_ROLE}'`, 5);
      const row = (r.data || [])[0];
      const ra = (row?.roleAssignments || []).find((x) => String(x.organization?.descriptor || '').startsWith('X:'));
      return row && ra ? { role: row.role, org: ra.organization, positions: ra.cf_ZCF_EE_RoleAssignedToAsPositionRestrictions || [] } : null;
    };
    const cur = await readRole();
    if (!cur) return skip('Bulk.applyAddRemove', `test role ${TEST_ROLE} has no X: organization assignment`);
    const assigned = cur.positions.map((p) => String(p.descriptor || ''));
    const pos = ((await wql(token, 'SELECT cf_PositionID, workdayID, position_PositionManagement, cf_PositionText, cf_PositionIsFilled FROM allPositions WHERE supervisoryOrganization is not empty', 300)).data || [])
      .filter((p) => p.cf_PositionID && p.cf_PositionIsFilled !== false && !assigned.some((d) => d.includes(p.cf_PositionID)))[0];
    if (!pos) return skip('Bulk.applyAddRemove', `no unassigned position found for ${TEST_ROLE}`);
    const posName = pos.position_PositionManagement?.descriptor || pos.cf_PositionText || pos.cf_PositionID;
    const runOne = async (tag, row) => {
      const ref = 'TEST' + tag + new Date().toISOString().replace(/\D/g, '').slice(0, 14);
      const stamp = new Date().toISOString().replace(/\.\d+Z$/, 'Z');
      await request('POST', `${BO}/comsBulkRuns`, token, { batchRef: ref, source: 'Grid', runMode: 'APPLY', status: 'Uploaded',
        effectiveDate: today, uploadedByName: me.descriptor, uploadedByWid: me.id, uploadedAt: stamp, changeCount: '1', summary: 'TEST apply run' });
      await request('POST', `${BO}/comsBulkRowResults`, token, { batchRef: ref + '-DRAFT', runMode: 'APPLY', result: 'DRAFT',
        roleName: TEST_ROLE, roleWid: cur.role.id, orgName: cur.org.descriptor || '', orgWid: cur.org.id, timestamp: stamp, ...row });
      const r = await launch(token, 'IORC_0037_XFD_SEC_Bulk_Role_Changes_From_Grid', { ref, mode: 'APPLY', effectiveDate: today, changedBy: me.descriptor, changedByWid: me.id });
      console.log(`   ${tag} launch: ` + String(typeof r === 'string' ? r : JSON.stringify(r)).slice(0, 200));
      let run, audit;
      for (let i = 0; i < 30 && !(run && audit); i++) {
        await sleep(4000);
        run = ((await request('GET', `${BO}/comsBulkRuns?limit=100&batchRef=${encodeURIComponent(ref)}`, token)).data || [])[0];
        if (run && /Rejected|Failed/.test(run.status || '')) throw new Error(`${ref}: run ${run.status}: ${run.statusMessage || ''}`);
        if (run?.status === 'Completed') audit = (await readAll(token, 'comsAuditLogs')).filter((a) => (a.details || '').includes(ref)).pop();
      }
      if (!run || run.status !== 'Completed') throw new Error(`${ref}: run status ${run?.status} after 2 minutes`);
      if (!audit) throw new Error(`${ref}: Completed but no audit record mentions it (IORC_0037_XFD_SEC_Sub_Write_Audit_Record inside IORC_0037_XFD_SEC_Sub_Process_Bulk_Role_Row didn't write)`);
      return { ref, audit };
    };
    const check = (a, action) => {
      const miss = ['timestamp', 'runId', 'roleName', 'positionName', 'changedByWid', 'orgWid', 'roleWid', 'positionWid', 'triggeredBy']
        .filter((k) => !String(a[k] || '').trim());
      if (a.objectType !== 'Role Assignment' || a.action !== action) throw new Error(`audit record is ${a.objectType}/${a.action}, expected Role Assignment/${action}`);
      if (miss.length) throw new Error(`${action} audit record lacks ${miss.join(', ')}`);
      if (!/^Bulk edit /.test(a.details || '')) throw new Error(`${action} details don't start with "Bulk edit": ${a.details}`);
    };
    const add = await runOne('BA', { rowAction: 'ADD', positionId: pos.cf_PositionID, positionName: posName, assigneeWid: '' });
    check(add.audit, 'ASSIGN POSITION');
    let added = null;
    for (let i = 0; i < 18 && !added; i++) {
      added = ((await readRole())?.positions || []).find((p) => !cur.positions.some((q) => q.id === p.id));
      if (!added) await sleep(5000);
    }
    if (!added) throw new Error(`${pos.cf_PositionID} was audited as added by ${add.ref} but did not appear on ${TEST_ROLE} within 90 s; it is probably still assigned: remove it in Manage Role Assignments`);
    const rem = await runOne('BR', { rowAction: 'REMOVE', positionId: pos.cf_PositionID, positionName: added.descriptor || posName, assigneeWid: added.id });
    check(rem.audit, 'REMOVE POSITION');
    let gone = false;
    for (let i = 0; i < 18 && !gone; i++) {
      gone = !((await readRole())?.positions || []).some((p) => p.id === added.id);
      if (!gone) await sleep(5000);
    }
    if (!gone) throw new Error(`${pos.cf_PositionID} is still on ${TEST_ROLE} after ${rem.ref}: remove it in Manage Role Assignments`);
    pass('Bulk.applyAddRemove', `${pos.cf_PositionID} added (${add.ref}) and removed (${rem.ref}) on ${TEST_ROLE}; both audit records written by IORC_0037_XFD_SEC_Sub_Write_Audit_Record inside IORC_0037_XFD_SEC_Sub_Process_Bulk_Role_Row ("${add.audit.details}")`);
  });
}

// ═══ Sub-orchestrations (tools/extract_subflows.py): each parent → its sub-orchestration → Workday, leaving nothing ═══
// Each call gets input only Workday rejects (an impossible effective date, an unknown request), so the error comes from
// inside the sub-orchestration's own steps and nothing is created. IORC_0037_XFD_SEC_Sub_Process_Bulk_Role_Row's success path: suite bulkvalidate.
async function subflowsSuite(token, me) {
  console.log('\n-- Sub-orchestrations (rejected calls only; nothing is created) --');
  const who = () => ({ changedBy: me.descriptor, changedByWid: me.id, timestamp: new Date().toISOString().replace(/\.\d+Z$/, 'Z') });
  const txt = (r) => (typeof r === 'string' ? r : JSON.stringify(r));
  const auditTotal = async () => (await request('GET', `${BO}/comsAuditLogs?limit=1`, token)).total;
  const expectRejected = async (name, step, params, want) => {
    const before = await auditTotal();
    const r = txt(await launch(token, name, params));
    await sleep(3000);
    const after = await auditTotal();
    if (!/Completed with error/.test(r)) throw new Error(`${name}: expected a rejected run, got: ${r.slice(0, 300)}`);
    if (want && !want.test(r)) throw new Error(`${name}: the error didn't come from the sub-orchestration's own step: ${r.slice(0, 300)}`);
    if (after !== before) throw new Error(`${name}: ${after - before} audit record(s) written by a rejected run`);
    pass(step, r.slice(0, 220));
  };
  await test('Subflow.createShellOrg', () => expectRejected('IORC_0037_XFD_SEC_Create_Application_Shell_Org', 'Subflow.createShellOrg', {
    comsAppId: '', orgType: 'X:ADM', organizationName: 'X:ADM:TEST:SUBFLOW', organizationCode: 'X:ADM:TEST:SUBFLOW',
    orgSubtype: 'X:SHELL', workerId: me.id, effectiveDate: 'NOTADATE', ...who() }, /rejected the request for X:ADM:TEST:SUBFLOW[\s\S]*IORC_0037_XFD_SEC_Sub_Create_Shell_Organization/));
  await test('Subflow.createShellOrgPattern', async () => {
    const app = ((await request('GET', `${BO}/comsApplications?limit=100`, token)).data || []).find((a) => a.appId === 'X:CLW');
    if (!app) return skip('Subflow.createShellOrgPattern', 'no X:CLW record');
    const pname = 'X:CLW:PATTERN:TEST:TEST:999:900:2026W1';
    await expectRejected('IORC_0037_XFD_SEC_Create_Pattern_Shell_Org', 'Subflow.createShellOrgPattern', { comsAppId: app.id, patternName: pname, workerId: me.id,
      attribute1: 'TEST', attribute2: 'TEST', attribute3: '999', attribute4: '900', attribute5: '2026W1', effectiveDate: 'NOTADATE', ...who() },
      new RegExp('rejected the request for ' + pname.replace(/[()]/g, '\\$&') + '[\\s\\S]*IORC_0037_XFD_SEC_Sub_Create_Shell_Organization'));
  });
  await test('Subflow.startReview', () => expectRejected('IORC_0037_XFD_SEC_Start_Role_Request_Review', 'Subflow.startReview', { ref: 'TEST-NO-SUCH-REQUEST' }, /IORC_0037_XFD_SEC_Sub_Start_Request_Review/));
}

async function probe(token) {
  console.log('\n-- Probe (read-only) --');
  // 2026-11-06: organization subtypes (X:META / X:SHELL) as the filter instead of the X: code prefix
  {
    const xs = (await wql(token, "SELECT workdayID, code, subtype, type1, superiorOrganization FROM topLevelOrganizations WHERE code contains 'X:'", 10000)).data || [];
    const st = {};
    for (const o of xs) { const k = JSON.stringify(o.subtype || null); st[k] = (st[k] || 0) + 1; }
    Object.entries(st).forEach(([k, v]) => console.log(`   SUBTYPE ${k} count=${v}`));
    console.log('   SAMPLE ' + JSON.stringify(xs.slice(0, 2)));
    const ids = [...new Set(xs.map((o) => o.subtype && o.subtype.id).filter(Boolean))];
    if (ids.length) {
      const bySub = (await wql(token, `SELECT workdayID, code, subtype FROM topLevelOrganizations WHERE subtype in (${ids.join(',')})`, 10000)).data || [];
      console.log(`   BYSUBTYPE total=${bySub.length} withoutX=${bySub.filter((o) => !String(o.code || '').includes('X:')).length}`);
      bySub.filter((o) => !String(o.code || '').includes('X:')).slice(0, 20).forEach((o) => console.log('   NOX ' + JSON.stringify(o)));
    }
    const roles = (await wql(token, "SELECT role, roleName, enabledForOrganizationTypes FROM assignableRoles WHERE roleName contains 'X:'", 10000)).data || [];
    console.log(`   ROLES total=${roles.length} sample=${JSON.stringify(roles.slice(0, 3))}`);
    return;
  }
  // Sub-orchestration probe (tools/probe_subflow.py): ProbeSubflowCall calls ProbeEcho and returns {"echo": "echo:hello"}.
  // Application Pattern audit rows vs application records (Audit Log link, 2026-11-05)
  const ap = (await readAll(token, 'comsAuditLogs')).filter((a) => a.objectType === 'Application Pattern');
  ap.forEach((a) => console.log(`   APPAUDIT coReferenceId=${JSON.stringify(a.coReferenceId)} coName=${JSON.stringify(a.coName)} keys=${Object.keys(a).join(',')}`));
  const apps = (await request('GET', `${BO}/comsApplications?limit=100`, token)).data || [];
  console.log(`comsApplications: ${apps.length}`);
  apps.slice(0, 3).forEach((a) => console.log(`   APPREC id=${a.id} appId=${JSON.stringify(a.appId)} keys=${Object.keys(a).join(',')}`));
  apps.forEach((a) => console.log('   APP ' + JSON.stringify(a)));
  const orgs = (await wql(token, "SELECT code, cf_active1 FROM topLevelOrganizations WHERE code contains 'X:'", 10000)).data || [];
  const byApp = {};
  for (const o of orgs) {
    const c = String(o.code || ''); const parts = c.split(':');
    if (parts.length < 2) continue;
    const app = parts[0] + ':' + parts[1]; const pre = parts[2] || '(none)';
    byApp[app] = byApp[app] || {}; byApp[app][pre] = (byApp[app][pre] || 0) + 1;
  }
  Object.keys(byApp).sort().forEach((a) => console.log(`   CODE ${a}  prefixes: ${Object.entries(byApp[a]).map(([k, v]) => k + '=' + v).join(', ')}`));
  for (const q of ['Subject', 'Course Subject', 'Course']) {
    try {
      const r = await request('GET', `${API}/wql/v1/dataSources?search=${encodeURIComponent(q)}&limit=20`, token);
      (r.data || []).forEach((d) => console.log(`   DS[${q}] ${d.alias || ''} | ${d.descriptor || d.name || ''}`));
    } catch (e) { console.log(`   DS[${q}] error ${e.message.slice(0, 120)}`); }
  }
  try {
    const ds = await request('GET', `${API}/wql/v1/dataSources?alias=topLevelOrganizations`, token);
    const id = (ds.data || [])[0]?.id;
    console.log(`   DS topLevelOrganizations id=${id}`);
    let all = [];
    for (let off = 0; off < 5000; off += 100) {
      const page = (await request('GET', `${API}/wql/v1/dataSources/${id}/fields?limit=100&offset=${off}`, token)).data || [];
      all = all.concat(page); if (page.length < 100) break;
    }
    console.log(`   FIELDS total ${all.length}`);
    all.filter((x) => /subtype|organization type|^type/i.test(`${x.alias} ${x.descriptor}`)).forEach((x) => console.log(`   FIELD ${x.alias} | ${x.descriptor} | ${x.type || ''}`));
  } catch (e) { console.log('   FIELDS error ' + e.message.slice(0, 200)); }
  for (const f of ['subtype']) {
    try {
      const r = await wql(token, `SELECT code, ${f} FROM topLevelOrganizations WHERE code contains 'X:'`, 10000);
      const cnt = {};
      (r.data || []).forEach((o) => { const v = o[f]?.descriptor || JSON.stringify(o[f]); const k = `${String(o.code).split(':').length <= 2 ? 'APP-ROOT' : String(o.code).split(':')[2]}|${v}`; cnt[k] = (cnt[k] || 0) + 1; });
      console.log(`   SUBTYPE via ${f}:`); Object.entries(cnt).sort().forEach(([k, v]) => console.log(`      ${k} = ${v}`));
      break;
    } catch (e) { console.log(`   SUBTYPE field ${f}: ${e.message.slice(0, 200)}`); }
  }
  // Application-level organizations (X:APP, X:APP(SUB)): their organization type and subtype (2026-11-05, X:META design)
  for (const f of ['organizationType', 'type', 'type1', 'customOrganizationType']) {
    try {
      const r = await wql(token, `SELECT code, subtype, ${f} FROM topLevelOrganizations WHERE code contains 'X:'`, 10000);
      const roots = (r.data || []).filter((o) => String(o.code).split(':').length <= 2 || /\)$/.test(String(o.code).split(':').slice(0, 2).join(':')));
      const seen = {};
      roots.filter((o) => String(o.code).split(':').length <= 2).forEach((o) => console.log(`   ROOT ${o.code} | type ${o[f]?.descriptor || JSON.stringify(o[f])} | subtype ${o.subtype?.descriptor || JSON.stringify(o.subtype)}`));
      (r.data || []).filter((o) => String(o.code).includes('(') && String(o.code).split(':').length > 2).forEach((o) => {
        const app = String(o.code).split(':').slice(0, 2).join(':'); const t = o[f]?.descriptor || JSON.stringify(o[f]);
        if (!seen[app + t]) { seen[app + t] = 1; console.log(`   UNDER ${app} | example ${o.code} | type ${t}`); }
      });
      break;
    } catch (e) { console.log(`   TYPE field ${f}: ${e.message.slice(0, 160)}`); }
  }
  pass('Probe', `${apps.length} application record(s), ${Object.keys(byApp).length} application codes in Workday`);
}

// ── Role assignment: add a position to the test role, then remove it (net no change) ──
// Shared by the full suite and the eventlinks suite. Returns both audit records.
async function roleAddRemove(token, me) {
  const today = tenantDate();
  const who = () => ({ changedBy: me.descriptor, changedByWid: me.id, timestamp: new Date().toISOString().replace(/\.\d+Z$/, 'Z') });
  // The API gateway scores the whole launch query string and refused this one (HTML 403) with the
  // org's full name "X:...(...) ... (varies)"; dropping any one of several values let it through
  // (gatewayprobe, 2026-11-04). orgName only labels the audit record, so retry once with the org code.
  const launchRole = async (params) => {
    try { return await launchAndVerify(token, 'IORC_0037_XFD_SEC_Assign_Remove_Role_Positions', params); }
    catch (e) {
      if (!/HTTP 403 .*<!DOCTYPE|HTTP 403 .*<style/i.test(e.message)) throw e;
      console.log(`   gateway refused the launch (HTML 403); retrying with orgName "${String(params.orgName).split(' ')[0]}"`);
      return launchAndVerify(token, 'IORC_0037_XFD_SEC_Assign_Remove_Role_Positions', { ...params, orgName: String(params.orgName).split(' ')[0] });
    }
  };
  const expectAudit = (a, type, action) => {
    if (a.objectType !== type || a.action !== action) throw new Error(`audit record is ${a.objectType}/${a.action}, expected ${type}/${action}`);
  };
    const roleName = TEST_ROLE;
  const readRole = async () => {
    const r = await wql(token, `SELECT role, roleAssignments{organization, cf_ZCF_EE_RoleAssignedToAsPositionRestrictions} as roleAssignments FROM assignableRoles WHERE roleName = '${roleName}'`, 5);
    const row = (r.data || [])[0];
    const ra = (row?.roleAssignments || []).find((x) => String(x.organization?.descriptor || '').startsWith('X:'));
    return row && ra ? { role: row.role, org: ra.organization, positions: ra.cf_ZCF_EE_RoleAssignedToAsPositionRestrictions || [] } : null;
  };
  const cur = await readRole();
  if (!cur) return skip('RoleAssignment.addRemove', `test role ${roleName} has no X: organization assignment`);
  const assigned = cur.positions.map((p) => String(p.descriptor || ''));
  const pos = ((await wql(token, 'SELECT cf_PositionID, workdayID, position_PositionManagement, cf_PositionText, cf_PositionIsFilled FROM allPositions WHERE supervisoryOrganization is not empty', 300)).data || [])
    .filter((p) => p.cf_PositionID && p.cf_PositionIsFilled !== false && !assigned.some((d) => d.includes(p.cf_PositionID)))[0];
  if (!pos) return skip('RoleAssignment.addRemove', `no unassigned position found for ${roleName}`);
  const posWid = pos.workdayID?.id || pos.workdayID;
  // Same full name the Manage Role Assignment page sends (its search results' descriptor).
  const posName = pos.position_PositionManagement?.descriptor || pos.cf_PositionText || pos.cf_PositionID;
  const base = { roleId: cur.role.id, roleName, orgId: cur.org.id, orgName: cur.org.descriptor, effectiveDate: today };
  const add = await launchRole({
    ...base, positionId: pos.cf_PositionID, positionIdType: 'Position_ID', positionName: posName,
    mode: 'ADD', positionWid: posWid, ...who(),
  });
  expectAudit(add, 'Role Assignment', 'ASSIGN POSITION');
  let added = null;
  // WQL can lag the change by well over 20 s: poll up to 90 s. If it never shows, say so loudly,
  // because the position is then left on the test role and must be removed by hand.
  for (let i = 0; i < 18 && !added; i++) {
    const after = await readRole();
    added = (after?.positions || []).find((p) => !cur.positions.some((q) => q.id === p.id));
    if (!added) await sleep(5000);
  }
  if (!added) throw new Error(`${pos.cf_PositionID} was audited as added to ${roleName} but did not appear on the role assignment within 90 s; it is probably still assigned: remove it in Manage Role Assignments`);
  const rem = await launchRole({
    ...base, positionId: added.id, positionIdType: 'WID', positionName: added.descriptor || pos.cf_PositionID,
    mode: 'REMOVE', positionWid: added.id, ...who(),
  });
  expectAudit(rem, 'Role Assignment', 'REMOVE POSITION');
  // The audit log must show the same full position name for both changes, never a bare ID.
  for (const a of [add, rem]) {
    if (/^P-\d+$/.test(String(a.positionName || '').trim())) throw new Error(`${a.action} audit shows only the position ID "${a.positionName}"`);
  }
  if (add.positionName !== rem.positionName) throw new Error(`position name differs: assign "${add.positionName}" vs remove "${rem.positionName}"`);
  pass('RoleAssignment.addRemove', `${pos.cf_PositionID} added to and removed from ${roleName} on ${cur.org.descriptor}`);
  return { add, rem, pos, roleName };
}

// ═══ Event links (writes): one role assignment add + remove, then check both audit records ═══
// carry the run ID Workday returned for their launch and an event that opens in Workday.
async function eventLinks(token, me) {
  console.log('\n-- Event links (writes: adds then removes one position on the test role) --');
  let r = null;
  await test('EventLinks.roleChange', async () => { r = await roleAddRemove(token, me); });
  if (!r || !r.add) return skip('EventLinks', 'the role change did not run');
  for (const a of [r.add, r.rem]) {
    const n = `EventLinks.${a.action === 'ASSIGN POSITION' ? 'add' : 'remove'}`;
    await test(`${n}.runId`, async () => {
      if (!a.runId) throw new Error('audit record has no runId');
      if (a._launchId && a._launchId !== a.runId) throw new Error(`runId ${a.runId} differs from the launch's X-Orchestrate-Id ${a._launchId}`);
      pass(`${n}.runId`, `runId ${a.runId}` + (a._launchId ? ' = the launch\'s X-Orchestrate-Id' : ' (launch returned no X-Orchestrate-Id header to compare)'));
    });
    await test(`${n}.event`, async () => {
      if (!a.eventWid) throw new Error('audit record has no eventWid (Assign_Roles_Event_Reference not found in the Staffing response)');
      const ev = await request('GET', `${BP}/events/${a.eventWid}`, token);
      pass(`${n}.event`, `eventWid ${a.eventWid} opens: ${ev.descriptor || ev.businessProcess?.descriptor || JSON.stringify(ev).slice(0, 120)}`);
    });
  }
}


// ═══ Timing (read-only): the audit reads the pages make, REST (this morning) vs Graph (now) ═══
async function timingSuite(token) {
  console.log('\n-- Timing (read-only): every data call the slow pages make, one at a time --');
  const med = async (label, f, n = 3) => {
    const ms = []; let info = '';
    for (let i = 0; i < n; i++) { const s = Date.now(); info = await f(); ms.push(Date.now() - s); }
    console.log(`   ${label}: median ${ms.slice().sort((x, y) => x - y)[Math.floor(n / 2)]} ms (${ms.join(', ')})${info ? ' · ' + info : ''}`);
  };
  const wqlFile = (id) => JSON.parse(fs.readFileSync(path.join(ROOT, 'presentation/wqlQueries', id + '.wqlquery'), 'utf8')).query;
  const kb = (r) => Math.round(JSON.stringify(r).length / 1024) + ' KB';
  for (const id of ['allShellOrgs', 'allShellAssignableRolesinTenant', 'allAAArolesinTenant', 'allPositions', 'customOrganizations']) {
    await med(`WQL ${id}`, async () => { const r = await wql(token, wqlFile(id), 10000); return `${(r.data || []).length} rows, ${kb(r)}`; });
  }
  await med('WQL positionFill (Access Review)', async () => { const r = await wql(token, 'SELECT cf_PositionID, cf_PositionIsFilled FROM allPositions WHERE supervisoryOrganization is not empty', 10000); return `${(r.data || []).length} rows, ${kb(r)}`; });
  await med('REST requests: count + 3 pages (today)', async () => { await request('GET', `${BO}/comsAssignableRoles?limit=1`, token); const r = await Promise.all([0, 100, 200].map((o) => request('GET', `${BO}/comsAssignableRoles?limit=100&offset=${o}`, token))); return `${r.reduce((n, x) => n + (x.data || []).length, 0)} rows, ${kb(r)}`; });
  const RQ = 'workdayID { id } referenceId roleName application status requestedBy { workdayID { id } descriptor } requestedDate approvedDate effectiveDate shellOrgCode positionNames reviewEventWid';
  const req = (where) => `query { r: ${APP_ID}_COMSAssignableRole(dataSource: {${APP_ID}_comsAssignableRoles: {}}${where ? ', where: ' + where : ''}, orderBy: {requestedDate: DESC}, limit: 100) { total data { ${RQ} } } }`;
  await med('Graph requests: all, newest first', async () => { const r = await gql(token, req('')); return `${r.r.data.length} rows (total ${r.r.total}), ${kb(r)}`; });
  await med('Graph requests: pending only', async () => { const r = await gql(token, req('{status: {eq: "Pending ISC Review"}}')); return `${r.r.data.length} rows, ${kb(r)}`; });
  const AQ = 'workdayID { id } timestamp action objectType coName coReferenceId triggeredBy details effectiveDate roleName positionName changedByWid orgWid roleWid positionWid runId eventWid';
  const aud = (where, limit = 100) => `query { r: ${APP_ID}_COMSAuditLog(dataSource: {${APP_ID}_comsAuditLogs: {}}${where ? ', where: ' + where : ''}, orderBy: {timestamp: DESC}, limit: ${limit}) { total data { ${AQ} } } }`;
  const since = new Date(Date.now() - 7 * 864e5).toISOString().slice(0, 10) + 'T00:00:00Z';
  await med('Graph audit: page 0 (today)', async () => { const r = await gql(token, aud('')); return `total ${r.r.total}, ${kb(r)}`; });
  // timestamp is a TEXT field: String_Filter has no gt/gte (2026-11-04), so a period can't be filtered on the server
  await med('Graph audit: total only (limit 1)', async () => { const r = await gql(token, `query { r: ${APP_ID}_COMSAuditLog(dataSource: {${APP_ID}_comsAuditLogs: {}}, limit: 1) { total } }`); return `total ${r.r.total}`; });
  const audits = await readAll(token, 'comsAuditLogs');
  const noOrg = audits.filter((a) => !a.orgWid && a.coName).length, noRole = audits.filter((a) => !a.roleWid && a.roleName).length;
  pass('Timing', `see lines above; ${audits.length} audit records, ${noOrg} without orgWid, ${noRole} without roleWid (the Audit Log's lookup lists only serve these)`);
}

// ═══ GraphQL probe (read-only): what the Graph API schema offers for this app's objects ═══
// Names per developer.workday.com "Model Components in the Graph API Schema":
// query <appRef>_<BusinessObject>(dataSource: {<appRef>_<collection>: {}}, where, limit, offset).
const GQL = `${API}/graphql/v1`;
async function gql(token, query, variables) {
  const r = await request('POST', GQL, token, { query, variables: variables || {} });
  if (r && r.errors && r.errors.length) throw new Error('GraphQL: ' + JSON.stringify(r.errors).slice(0, 400));
  return r.data;
}
async function graphqlSuite(token) {
  console.log('\n-- GraphQL (read-only) --');
  const objs = [['COMSAuditLog', 'comsAuditLogs'], ['COMSAssignableRole', 'comsAssignableRoles'],
    ['COMSApplication', 'comsApplications'], ['COMSBulkRun', 'comsBulkRuns']];
  const typeInfo = async (name) => {
    const d = await gql(token, `query($n: String!) { __type(name: $n) { name kind fields { name type { name kind ofType { name kind } } } inputFields { name type { name kind ofType { name kind } } } } }`, { n: name });
    return d.__type;
  };
  // 1. The root query fields for this app.
  await test('GraphQL.schema', async () => {
    const d = await gql(token, `{ __schema { queryType { fields(includeDeprecated: false) { name args { name type { name kind ofType { name kind } } } type { name kind ofType { name } } } } } }`);
    const mine = d.__schema.queryType.fields.filter((f) => f.name.startsWith(APP_ID));
    mine.forEach((f) => console.log(`   QUERY ${f.name} -> ${f.type.name || f.type.ofType?.name} args: ${f.args.map((a) => a.name + ':' + (a.type.name || a.type.ofType?.name)).join(', ')}`));
    if (!mine.length) throw new Error('no query fields start with ' + APP_ID);
    pass('GraphQL.schema', `${mine.length} query field(s) for this app`);
    for (const f of mine) {
      for (const a of f.args.filter((x) => ['where', 'dataSource'].includes(x.name))) {
        const tn = a.type.name || a.type.ofType?.name; const t = await typeInfo(tn);
        console.log(`   ${f.name}.${a.name} (${tn}): ${(t?.inputFields || []).map((x) => x.name + ':' + (x.type.name || x.type.ofType?.name)).join(', ')}`);
      }
      const rt = f.type.name || f.type.ofType?.name; const t = await typeInfo(rt);
      const dataF = (t?.fields || []).find((x) => x.name === 'data');
      const itemT = dataF && (dataF.type.name || dataF.type.ofType?.name);
      const it = itemT && await typeInfo(itemT);
      console.log(`   ${f.name} result ${rt}: ${(t?.fields || []).map((x) => x.name).join(', ')}; item ${itemT}: ${(it?.fields || []).map((x) => x.name + ':' + (x.type.name || x.type.ofType?.name)).join(', ')}`);
    }
  });
  // 2. Totals agree with REST.
  for (const [obj, coll] of objs) {
    await test(`GraphQL.total.${obj}`, async () => {
      const q = `query { r: ${APP_ID}_${obj}(dataSource: {${APP_ID}_${coll}: {}}, limit: 1) { total data { descriptor workdayID { id } } } }`;
      const t0 = Date.now(); const d = await gql(token, q); const ms = Date.now() - t0;
      const rest = (await request('GET', `${BO}/${coll}?limit=1`, token)).total;
      const g = d.r.total;
      (String(g) === String(rest) ? pass : fail)(`GraphQL.total.${obj}`, `GraphQL total ${g}, REST total ${rest} (${ms} ms); first: ${d.r.data?.[0]?.descriptor ?? '-'}`);
    });
  }

  // 3. What the Audit Log page would use: newest first, the same fields the page reads, shapes vs REST.
  await test('GraphQL.auditNewestFirst', async () => {
    for (const n of [`Ecocomsphase_xclw_cm_sync2_vmzvxm_COMSAuditLog_OrderInput`, 'String_Filter', 'Instant_Filter']) {
      const t = await typeInfo(n);
      console.log(`   TYPE ${n}: ${(t?.inputFields || []).map((x) => x.name + ':' + (x.type.name || x.type.ofType?.name)).join(', ')}`);
      for (const f of (t?.inputFields || [])) {
        const tn = f.type.name || f.type.ofType?.name;
        if (tn && /Order|Direction|Sort/i.test(tn)) {
          const e = (await gql(token, `query($n: String!) { __type(name: $n) { kind enumValues { name } inputFields { name type { name } } } }`, { n: tn })).__type;
          console.log(`      ${tn}: ${JSON.stringify(e)}`);
        }
      }
    }
    const fields = 'workdayID { id } timestamp action objectType coName coReferenceId triggeredBy details effectiveDate roleName positionName changedByWid orgWid roleWid positionWid';
    let d, used;
    for (const ob of ['{timestamp: DESC}', '[{timestamp: DESC}]', '{field: timestamp, direction: DESC}']) {
      try { d = await gql(token, `query { r: ${APP_ID}_COMSAuditLog(dataSource: {${APP_ID}_comsAuditLogs: {}}, orderBy: ${ob}, limit: 100) { total data { ${fields} } } }`); used = ob; break; }
      catch (e) { console.log(`   orderBy ${ob}: ${e.message.slice(0, 300)}`); }
    }
    if (!d) throw new Error('no orderBy form accepted');
    const g = d.r.data; const rest = (await request('GET', `${BO}/comsAuditLogs?limit=100`, token)).data || [];
    console.log(`   orderBy ${used}: ${g.map((x) => x.timestamp).join(' > ')}`);
    console.log(`   GQL item: ${JSON.stringify(g[0])}`);
    console.log(`   REST item: ${JSON.stringify(rest.find((x) => x.id === g[0]?.workdayID?.id) || rest[0])}`);
    const sorted = g.every((x, i) => i === 0 || String(g[i - 1].timestamp) >= String(x.timestamp));
    (sorted ? pass : fail)('GraphQL.auditNewestFirst', `${g.length} of ${d.r.total} rows, newest first: ${sorted}`);
    const w = await gql(token, `query { r: ${APP_ID}_COMSAuditLog(dataSource: {${APP_ID}_comsAuditLogs: {}}, where: {objectType: {eq: "Role Assignment"}}, limit: 100) { total } }`);
    pass('GraphQL.auditWhere', `where objectType = Role Assignment: ${w.r.total} (REST filtering would need an index)`);
  });

  // 4. Offset paging order (the Audit Log relies on it): offset 0 first, then offset 100 works.
  await test('GraphQL.offsetAfterFirst', async () => {
    const q = 'query($o: BigInt) { r: worker(dataSource: {indexedAllWorkers: {filter: {indexedAllWorkersFilter: {isActive: true}}}}, limit: 100, offset: $o) { total data { workdayID { id } } } }';
    const a = await gql(token, q, { o: 0 });
    if ((a.r.total || 0) <= 100) return skip('GraphQL.offsetAfterFirst', `only ${a.r.total} active workers`);
    const b = await gql(token, q, { o: 100 });
    const overlap = b.r.data.filter((x) => a.r.data.some((y) => y.workdayID.id === x.workdayID.id)).length;
    (b.r.data.length && !overlap ? pass : fail)('GraphQL.offsetAfterFirst', `total ${a.r.total}: page 1 ${a.r.data.length} rows, page 2 ${b.r.data.length} rows, ${overlap} repeated`);
  });

  // 4b. The Audit Log's own Graph Query returns the run ID and event on the newest records.
  await test('GraphQL.auditLinks', async () => {
    const q = JSON.parse(fs.readFileSync(path.join(ROOT, 'presentation/graphQueries/auditLogsNewest.graphquery'), 'utf8'));
    const d = await gql(token, q.query, { offset: 0 });
    const rows = d.r.data || [];
    rows.slice(0, 5).forEach((x) => console.log(`   ${x.timestamp} ${x.objectType} ${x.action} runId=${x.runId || '-'} eventWid=${x.eventWid || '-'}`));
    const linked = rows.filter((x) => x.runId && x.eventWid);
    (linked.length ? pass : fail)('GraphQL.auditLinks', `${linked.length} of ${rows.length} records carry both a run ID and an event (the page's own query)`);
  });
  // 5. A second (non-admin) user: Graph API calls need the "Workday Graph API Applications" domain
  // (developer.workday.com "Run Graph API Queries on a Page"). Without it the Graph pages fail for them.
  await test('GraphQL.secondUser', async () => {
    const token2 = process.env.WD_SECOND_TOKEN || arg('--token2');
    if (!token2) return skip('GraphQL.secondUser', 'WD_SECOND_TOKEN is not set');
    let me2; try { me2 = await request('GET', `${API}/common/v1/workers/me`, token2); } catch (e) { return skip('GraphQL.secondUser', 'second token not usable: ' + e.message.slice(0, 120)); }
    const q = `query { r: ${APP_ID}_COMSAuditLog(dataSource: {${APP_ID}_comsAuditLogs: {}}, orderBy: {timestamp: DESC}, limit: 1) { total } }`;
    let rest = null; try { rest = (await request('GET', `${BO}/comsAuditLogs?limit=1`, token2)).total; } catch (e) { rest = 'REST ' + e.message.slice(0, 80); }
    try { const d = await gql(token2, q); pass('GraphQL.secondUser', `${me2.descriptor}: Graph total ${d.r?.total}, REST total ${rest}`); }
    catch (e) { fail('GraphQL.secondUser', `${me2.descriptor} can't run the audit Graph query (REST total ${rest}): ${e.message.slice(0, 300)}`); }
  });
}

// ═══ Data check: every record has the fields its pages display (read-only) ═══
async function dataCheck(token) {
  console.log('\n-- Data check (read-only) --');
  // Fields no page, orchestration, report or test uses (2026-11-04): how many records hold a value in each.
  const UNUSED = { comsApplications: ['idPrefix', 'createdBy', 'workdayOrgId'],
    comsAssignableRoles: ['enabledForCompany', 'enabledForCompanyHierarchy', 'positionRestrictions', 'workdayPositionId', 'positionIsFilled', 'organizationRoleAssignments'] };
  for (const [col, fields] of Object.entries(UNUSED)) {
    const recs = await readAll(token, col);
    const counts = fields.map((f) => {
      const n = recs.filter((r) => { const v = r[f]; return !(v === undefined || v === null || v === '' || v === false || (Array.isArray(v) && !v.length)); }).length;
      const t = recs.filter((r) => r[f] === true).length;
      return `${f}=${n}${t ? ' (true ' + t + ')' : ''}`;
    });
    pass('DataCheck.unusedFields', `${col} (${recs.length} records): ${counts.join(', ')}`);
  }
  const gaps = [];
  const need = (label, rec, fields) => {
    const miss = fields.filter((f) => { const v = rec[f]; return v === undefined || v === null || v === '' || (typeof v === 'object' && !v.id && !v.descriptor && !Array.isArray(v)); });
    if (miss.length) gaps.push(`${label}: missing ${miss.join(', ')}`);
  };
  const reqs = await readAll(token, 'comsAssignableRoles');
  // Closed test requests from before these fields existed (October 2026: 36 records, 58 gaps, all TESTROLE /
  // TEST: names, Approved or Denied). They can't be deleted (linked to BP events), so they're counted, not listed.
  const oldTest = (r) => /^(Approved|Denied)$/.test(r.status || '') && /TESTROLE|(^|:)TEST:/.test(r.roleName || '');
  const skipped = reqs.filter(oldTest).length;
  if (skipped) pass('DataCheck.closedTestRequests', `${skipped} closed test request(s) not checked for gaps (made before the fields existed)`);
  for (const r of reqs) {
    if (oldTest(r)) continue;
    const label = `request ${r.roleName} [${r.status}]`;
    need(label, r, ['referenceId', 'roleName', 'status', 'requestedBy', 'requestedDate', 'effectiveDate', 'enabledForOrganizationTypes', 'positionNames']);
    if (r.status === 'Pending ISC Review') need(label, r, ['reviewEventWid']);
    if (r.status === 'Approved') need(label, r, ['securityGroupName', 'approvedDate']);
    if (r.status === 'Denied') need(label, r, ['denialReason']);
    if (r.positionNames && /(^|,\s*)[0-9a-f]{32}(\s*,|$)/.test(r.positionNames)) gaps.push(`${label}: positionNames holds a bare WID`);
  }
  const audits = await readAll(token, 'comsAuditLogs');
  for (const a of audits) {
    const label = `audit ${a.objectType}/${a.action} ${a.coName || a.roleName || ''}`;
    need(label, a, ['timestamp', 'objectType', 'action', 'triggeredBy', 'changedByWid', 'details']);
    if (/Shell Org/.test(a.objectType || '') || a.objectType === 'Org Status') need(label, a, ['coName', 'orgWid', 'effectiveDate']);
    if (a.objectType === 'Role Assignment') need(label, a, ['roleName', 'positionName', 'roleWid', 'positionWid', 'coName', 'effectiveDate']);
    if (a.objectType === 'Assignable Role') need(label, a, ['roleName', 'coName']);
  }
  const runs = [...await readAll(token, 'comsBulkRuns'), ...await readAll(token, 'comsBulkUploads')];
  for (const b of runs) need(`bulk ${b.batchRef} [${b.status}]`, b, ['batchRef', 'status', 'runMode', 'effectiveDate', 'uploadedByName', 'uploadedAt']);
  gaps.forEach((g) => console.log(`   ${g}`));
  if (gaps.length) warn('Data.gaps', `${gaps.length} record(s) missing a field a page displays (listed above)`);
  else pass('Data.gaps', `${reqs.length} requests, ${audits.length} audit records, ${runs.length} bulk runs: every displayed field is filled`);
}

// ═══ Demo seed: the three demo test cases, run through the same orchestrations as the pages ═══
//   1. Clockwork creates a course-section shell org (pattern)        → Shell Org Pattern / ADD
//   2. A position is given a shell role on its application's org     → Role Assignment / ASSIGN POSITION
//   3. A new shell role is requested for the new org and sent to ISC → Assignable Role / REQUEST (stays pending)
// Values avoid the live finale (P-00009 → STAFF) so that still validates during the demo.
async function demoSeed(token, me) {
  console.log('\n-- Demo seed (writes real data: 1 org, 1 role assignment, 1 pending request) --');
  const EFF = arg('--effective') || '2026-11-02';
  const who = () => ({ changedBy: me.descriptor, changedByWid: me.id, timestamp: new Date().toISOString().replace(/\.\d+Z$/, 'Z') });
  const findOrg = async (c) => {
    const r = await wql(token, `SELECT workdayID, code FROM topLevelOrganizations WHERE code = '${c}'`, 1);
    return r.data?.[0]?.workdayID?.id || r.data?.[0]?.workdayID || null;
  };
  const PATTERN = 'X:CLW:PATTERN:CPSC:CPSC_V:110:101:2026W2';
  let patternWid = null;

  await test('Demo.1 pattern', async () => {
    const apps = (await request('GET', `${BO}/comsApplications?limit=100`, token)).data || [];
    const app = apps.find((a) => a.appId === 'X:CLW');
    if (!app) throw new Error('no COMS application with appId X:CLW');
    if (await findOrg(PATTERN)) return pass('Demo.1 pattern', `${PATTERN} already exists`);
    const a = await launchAndVerify(token, 'IORC_0037_XFD_SEC_Create_Pattern_Shell_Org', {
      comsAppId: app.id, patternName: PATTERN, workerId: me.id, attribute1: 'CPSC', attribute2: 'CPSC_V',
      attribute3: '110', attribute4: '101', attribute5: '2026W2', effectiveDate: EFF, ...who(),
    });
    if (a.objectType !== 'Shell Org Pattern' || a.action !== 'ADD') throw new Error(`audit is ${a.objectType}/${a.action}`);
    for (let i = 0; i < 12 && !patternWid; i++) { patternWid = await findOrg(PATTERN); if (!patternWid) await sleep(5000); }
    pass('Demo.1 pattern', `${PATTERN} created effective ${EFF}${patternWid ? '' : ' (not yet visible in WQL)'}`);
  });

  await test('Demo.2 assign', async () => {
    const roleName = 'X:BPMS(ODMT):ROLE:DEPTSTAFF';
    const done = (await readAll(token, 'comsAuditLogs')).find((x) => x.action === 'ASSIGN POSITION' && x.roleName === roleName);
    if (done) return pass('Demo.2 assign', `already done: ${done.positionName} on ${roleName}`);
    const r = await wql(token, `SELECT role, roleAssignments{organization, cf_ZCF_EE_RoleAssignedToAsPositionRestrictions} as roleAssignments FROM assignableRoles WHERE roleName = '${roleName}'`, 5);
    const row = (r.data || [])[0];
    const ra = (row?.roleAssignments || []).find((x) => String(x.organization?.descriptor || '').startsWith('X:'));
    if (!row || !ra) throw new Error(`${roleName} has no X: organization assignment`);
    const assigned = (ra.cf_ZCF_EE_RoleAssignedToAsPositionRestrictions || []).map((p) => String(p.descriptor || ''));
    const pos = ((await wql(token, 'SELECT cf_PositionID, workdayID, position_PositionManagement, cf_PositionText, cf_PositionIsFilled FROM allPositions WHERE supervisoryOrganization is not empty', 300)).data || [])
      .filter((p) => p.cf_PositionID && p.cf_PositionID !== 'P-00009' && p.cf_PositionIsFilled !== false && !assigned.some((d) => d.includes(p.cf_PositionID)))[0];
    if (!pos) throw new Error(`no unassigned filled position for ${roleName}`);
    const a = await launchAndVerify(token, 'IORC_0037_XFD_SEC_Assign_Remove_Role_Positions', {
      roleId: row.role.id, roleName, orgId: ra.organization.id, orgName: ra.organization.descriptor, effectiveDate: EFF,
      positionId: pos.cf_PositionID, positionIdType: 'Position_ID', mode: 'ADD', positionWid: pos.workdayID?.id || pos.workdayID,
      positionName: pos.position_PositionManagement?.descriptor || pos.cf_PositionText || pos.cf_PositionID, ...who(),
    });
    if (a.action !== 'ASSIGN POSITION') throw new Error(`audit is ${a.objectType}/${a.action}`);
    pass('Demo.2 assign', `${pos.cf_PositionID} (${a.positionName}) added to ${roleName} on ${ra.organization.descriptor}, effective ${EFF}`);
  });

  await test('Demo.3 request', async () => {
    const roleName = `${PATTERN}:ROLE:TEACHINGASSISTANT`;
    if (!patternWid) patternWid = await findOrg(PATTERN);
    // Enabled For: an academic unit, as the form's Academic Unit picker stores it.
    const aus = (await wql(token, "SELECT workdayID, academicUnit, academicUnitName FROM academicUnits WHERE inactive = false AND academicUnitName contains 'Computer Science'", 20)).data || [];
    const au = aus[0] || ((await wql(token, 'SELECT workdayID, academicUnit, academicUnitName FROM academicUnits WHERE inactive = false', 1)).data || [])[0];
    if (!au) throw new Error('no academic unit found for Enabled For');
    const auWid = au.workdayID?.id || au.workdayID;
    const auName = au.academicUnit?.descriptor || au.academicUnitName;
    // Positions: two filled positions, as the form's Positions picker stores them (WIDs + full names).
    const allPos = ((await wql(token, 'SELECT cf_PositionID, workdayID, position_PositionManagement, cf_PositionText, cf_PositionIsFilled FROM allPositions WHERE supervisoryOrganization is not empty', 1000)).data || [])
      .filter((p) => p.cf_PositionID && p.cf_PositionID !== 'P-00009' && p.cf_PositionIsFilled !== false);
    const pref = allPos.filter((p) => /instructor|lecturer|teaching|professor|academic/i.test(`${p.position_PositionManagement?.descriptor || ''} ${p.cf_PositionText || ''}`));
    const picks = [...pref, ...allPos.filter((p) => !pref.includes(p))].slice(0, 2);
    if (!picks.length) throw new Error('no filled positions found');
    const wids = picks.map((p) => p.workdayID?.id || p.workdayID);
    const names = picks.map((p) => p.position_PositionManagement?.descriptor || p.cf_PositionText || p.cf_PositionID);
    const fields = {
      shellOrgCode: PATTERN, shellOrgWid: patternWid || '',
      positions: wids.join(','), positionWids: wids.join(','), positionNames: names.join(', '),
      enabledForOrganizationTypes: auName, enabledForWid: auWid, academicUnitWid: auWid, academicUnitDescription: auName,
      functionalUnitHierarchyWid: '', functionalUnitDescription: '',
    };
    const existing = (await readAll(token, 'comsAssignableRoles')).find((x) => x.roleName === roleName && x.status === 'Pending ISC Review');
    if (existing) {
      // Fill in what the first seed left empty; the review event and its REQUEST audit stay as they are.
      await request('PATCH', `${BO}/comsAssignableRoles/${existing.id}`, token, fields);
      const reqAudit = (await readAll(token, 'comsAuditLogs')).find((x) => x.action === 'REQUEST' && x.roleName === roleName);
      if (reqAudit) await request('PATCH', `${BO}/comsAuditLogs/${reqAudit.id}`, token, { positionName: names.join(', '), positionWid: wids.join(',') });
      const after = await request('GET', `${BO}/comsAssignableRoles/${existing.id}`, token);
      if (after.positionNames !== fields.positionNames || after.enabledForOrganizationTypes !== auName) throw new Error('PATCH did not stick');
      return pass('Demo.3 request', `${roleName} updated: Enabled For "${auName}", positions ${names.join(' | ')}`);
    }
    const ref = `REQ-${Date.now().toString(36).toUpperCase()}`;
    const req = await request('POST', `${BO}/comsAssignableRoles`, token, {
      referenceId: ref, roleName, workdayRoleId: roleName, application: 'X:CLW', status: 'Pending ISC Review',
      requestedDate: tenantDate(), requestedBy: { id: me.id }, active: false, effectiveDate: EFF, ...fields,
    });
    if (!req.id) throw new Error('request POST returned no id');
    // IORC_0037_XFD_SEC_Start_Role_Request_Review writes the REQUEST audit record (with the event and run ID) since 2026-11-04.
    await launch(token, 'IORC_0037_XFD_SEC_Start_Role_Request_Review', { ref });
    let ev = null;
    for (let i = 0; i < 10 && !ev; i++) { await sleep(3000); ev = (await request('GET', `${BO}/comsAssignableRoles/${req.id}`, token)).reviewEventWid || null; }
    if (!ev) throw new Error(`request ${ref} saved but no review event within 30 s`);
    pass('Demo.3 request', `${roleName} requested (${ref}), Enabled For "${auName}", positions ${names.join(' | ')}, ISC review started`);
  });

  // Every pending request must show Enabled For and positions on the review pages.
  await test('Demo.pendingComplete', async () => {
    const pend = (await readAll(token, 'comsAssignableRoles')).filter((r) => r.status === 'Pending ISC Review');
    pend.forEach((r) => console.log(`   pending  ${r.roleName}  | Enabled For: ${r.enabledForOrganizationTypes || '(empty)'}  | Positions: ${r.positionNames || '(empty)'}`));
    const bad = pend.filter((r) => !r.enabledForOrganizationTypes || !r.positionNames);
    if (bad.length) throw new Error(`${bad.length} pending request(s) still missing Enabled For or position names: ${bad.map((r) => r.roleName).join(', ')}`);
    pass('Demo.pendingComplete', `${pend.length} pending request(s) all have Enabled For and position names`);
  });

  const audits = await readAll(token, 'comsAuditLogs');
  console.log(`\nAudit log now has ${audits.length} record(s):`);
  audits.forEach((a) => console.log(`   ${a.timestamp}  ${a.objectType}/${a.action}  ${a.coName || ''} ${a.roleName || ''} ${a.positionName || ''}`.trimEnd()));
}

// ─── Main ─────────────────────────────────────────────────────────────────────
(async () => {
  console.log(`ECO-COMS tests: suite=${SUITES.join(',')} tenant=${TENANT}`);
  if (SUITES.includes('static')) staticSuite();

  const live = SUITES.filter((s) => s !== 'static');
  if (live.length) {
    const token = resolveToken();
    if (!token) {
      fail('Auth', 'no Workday token: pass --token, set WD_DEV_TOKEN, or log in with wdcli');
    } else {
      let me;
      try {
        me = await request('GET', `${API}/common/v1/workers/me`, token);
        pass('Auth', `signed in as ${me.descriptor}`);
      } catch (e) { fail('Auth', e.message); }
      if (me) {
        if (live.includes('smoke') || live.includes('full')) await smoke(token, me);
        if (live.includes('full')) await full(token, me);
        if (live.includes('isu')) await isuSuite(token, me);
        if (live.includes('cleanup')) await cleanup(token, me);
        if (live.includes('repair')) await repair(token, me);
        if (live.includes('seconduser')) await secondUserSuite(token, me);
        if (live.includes('purge')) await purge(token);
        if (live.includes('demoseed')) await demoSeed(token, me);
        if (live.includes('datacheck')) await dataCheck(token);
        if (live.includes('probe')) await probe(token);
        if (live.includes('bulkvalidate')) await bulkValidate(token, me);
        if (live.includes('bulkapply')) await bulkApply(token, me);
        if (live.includes('subflows')) await subflowsSuite(token, me);
        if (live.includes('graphql')) await graphqlSuite(token);
        if (live.includes('eventlinks')) await eventLinks(token, me);
        if (live.includes('timing')) await timingSuite(token);
        if (live.includes('seedapps')) await seedApps(token);
        if (live.includes('patternguard')) await patternGuard(token, me);
        if (live.includes('orgguard')) await orgGuard(token, me);
        if (live.includes('gateway')) await gatewayProbe(token, me);
        if (live.includes('prompts')) await promptsProbe(token);
        if (live.includes('possearch')) await posSearchTiming(token);
        if (live.includes('postree')) await posTreeProbe(token);
        if (live.includes('orgtree')) await orgTreeProbe(token);
        if (live.includes('aaaname')) await aaaNameCheck(token);
        if (live.includes('appsummary')) await appSummary(token);
      }
    }
  }

  const count = (s) => results.filter((r) => r.status === s).length;
  const summary = { passed: count('PASS'), failed: count('FAIL'), skipped: count('SKIP'), warnings: count('WARN') };
  const line = `${summary.passed} passed, ${summary.failed} failed, ${summary.skipped} skipped, ${summary.warnings} warnings`;
  console.log(`\n${line}`);
  fs.writeFileSync(path.join(__dirname, 'results.json'),
    JSON.stringify({ runAt: new Date().toISOString(), suites: SUITES, tenant: TENANT, summary, results }, null, 2));
  if (process.env.GITHUB_STEP_SUMMARY) {
    const lines = [`## ECO-COMS tests (${SUITES.join(', ')})`, '', line, '',
      '| Result | Test | Detail |', '|---|---|---|',
      ...results.map((r) => `| ${r.status} | ${r.name} | ${String(r.msg).replace(/\|/g, '/').slice(0, 160)} |`),
      '', '<details><summary>Full output</summary>', '', '```', ...transcript, '```', '</details>'];
    fs.appendFileSync(process.env.GITHUB_STEP_SUMMARY, lines.join('\n') + '\n');
  }
  process.exit(summary.failed ? 1 : 0);
})();
