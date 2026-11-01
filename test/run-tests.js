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
const SUITES_ALL = ['static', 'smoke', 'full', 'cleanup', 'isu', 'repair', 'seconduser'];
const suiteArg = arg('--suite') || argv.find((a) => !a.startsWith('--') && SUITES_ALL.some((s) => a.split(',').includes(s))) || 'smoke';
const SUITES = suiteArg.split(',').map((s) => s.trim()).filter(Boolean);
for (const s of SUITES) if (!SUITES_ALL.includes(s)) { console.error(`Unknown suite "${s}". Use: ${SUITES_ALL.join(', ')}`); process.exit(2); }

// Fixed vocabulary (CLAUDE.md "Audit log design"). A new value here means a page or
// orchestration started writing something the viewer and reports don't expect.
const OBJECT_TYPES = ['Shell Org', 'Shell Org Pattern', 'Org Status', 'Role Assignment', 'Assignable Role'];
const ACTIONS = ['ADD', 'INACTIVATE', 'REACTIVATE', 'ASSIGN POSITION', 'REMOVE POSITION', 'REQUEST', 'APPROVE', 'DENY', 'DELETE'];
const TEST_ROLE = arg('--role') || process.env.E2E_ROLE || 'X:BPMS(ODMT):ROLE:ADVISORS';
const BO_COLLECTIONS = ['comsApplications', 'comsAssignableRoles', 'comsAuditLogs', 'comsRoleAssignments', 'comsShellOrgRequests'];

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
    ...listFiles('orchestration').filter((f) => f.endsWith('.orchestration')),
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
    if (String(v.type?._value || '').includes('BusinessProcessTriggered')) continue;
    const secured = ((v.securityDomains || {})._value || {})._value || [];
    const names = secured.map((x) => x._value);
    if (!names.length) { err('orchSecurity', `${path.basename(f)}: no securityDomains; anyone who can reach its launch URL can run it`); continue; }
    if (names.length > 1) err('orchSecurity', `${path.basename(f)}: ${names.length} security domains; App Hub allows only one per orchestration (use one orchestration per launching page)`);
    for (const n of names) {
      if (!domains[n]) err('orchSecurity', `${path.basename(f)}: security domain '${n}' is not defined in model/`);
      else if (domains[n].enabledForOrchestrationSecurity !== true) err('orchSecurity', `${path.basename(f)}: domain '${n}' needs "enabledForOrchestrationSecurity": true`);
    }
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
  for (const c of cardIds) if (!usedCards.has(c)) warn('Static.orphan', `card ${c} is not used by any page`);
  // 7f. AMD tasks nothing points at (pages count toward the 75-page limit). BP step pages are
  // reached by route, error pages through the SMD.
  const smd = (() => { try { return JSON.parse(fs.readFileSync(path.join(ROOT, AMD_PATH.replace('.amd', '.smd')), 'utf8')); } catch (_) { return {}; } })();
  const reached = new Set(refs.map(([, t]) => t));
  for (const c of smd.errorPageConfigurations || []) reached.add(c.page?.id);
  const bpRoutes = new Set();
  for (const f of listFiles('model').filter((x) => x.endsWith('.businessprocess'))) walk(docs[f] || {}, (n) => { if (typeof n.pageRoute === 'string') bpRoutes.add(n.pageRoute); });
  for (const [tid, t] of Object.entries(tasks)) {
    if (tid === 'home' || reached.has(tid) || reached.has(t.page?.id) || bpRoutes.has(t.routingPattern)) continue;
    warn('Static.orphan', `AMD task '${tid}' is not referenced by any page, card, flow or business process`);
  }

  // 8. No forbidden test text in anything shipped to the tenant (CLAUDE.md "Test data in the tenant")
  const forbidden = new RegExp(['cl', 'aude'].join(''), 'i');
  for (const f of [...listFiles('presentation', true), ...listFiles('model'), ...listFiles('orchestration')]) {
    if (forbidden.test(fs.readFileSync(path.join(ROOT, f), 'utf8'))) err('testText', `${f}: contains forbidden test text`);
  }

  // 9. Inbound endpoints should fail loudly (warning only)
  let quiet = 0;
  for (const d of Object.values(pmds)) {
    walk(d, (node, pk) => { if (pk === 'endPoints' && 'baseUrlType' in node && !('failOnStatusCodes' in node) && !node.deferred) quiet++; });
  }
  if (quiet) warn('Static.failOnStatusCodes', `${quiet} inbound endpoint(s) have no failOnStatusCodes (errors are swallowed)`);

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
// ManageShellOrgStatus picks inactivate vs reactivate from includeInactive ("true" = inactivate),
// not from action; action is only written to the audit record. Send both, as the page does.
const launch = (token, name, params) => {
  const qs = Object.entries(params).map(([k, v]) => `${k}=${encodeURIComponent(v ?? '')}`).join('&');
  return request('POST', `${ORCH}/${name}/launch?${qs}`, token, {});
};
// Same check the pages use (run-and-verify): the orchestration writes an audit record only
// after Workday accepts the change, so a +1 audit total means the call really worked.
async function launchAndVerify(token, name, params) {
  const ids = async () => (await readAll(token, 'comsAuditLogs'));
  const before = new Set((await ids()).map((a) => a.id));
  await launch(token, name, params);
  for (let i = 0; i < 10; i++) {
    await sleep(2000);
    // Match the new record by id: timestamps can tie, so "newest" is not reliable.
    const fresh = (await ids()).filter((a) => !before.has(a.id));
    if (fresh.length) return fresh[0];
  }
  throw new Error(`${name}: no new audit record after 20 s (Workday rejected the call or the orchestration failed; check app Logs)`);
}

// The guard in ManageShellOrgStatus must reject the call: no audit record may appear.
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

  let roles = [];
  await test('Requests.read', async () => {
    roles = await readAll(token, 'comsAssignableRoles');
    pass('Requests.read', `${roles.length} role requests`);
  });
  await test('Requests.deniedInactive', async () => {
    const bad = roles.filter((r) => r.status === 'Denied' && r.active !== false);
    if (bad.length) throw new Error(`${bad.length} Denied request(s) still active, e.g. ${bad[0].roleName}`);
    pass('Requests.deniedInactive', 'every Denied request is inactive (DenyRoleRequest orchestration)');
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
    const a = await launchAndVerify(token, 'AddShellOrg', {
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
    await expectRejected(token, 'ManageShellOrgStatus', { ...status(orgWid, orgName, 'X:ADM', false, later), action: 'INACTIVATE' });
    pass('Guard.actionMismatch', 'action that disagrees with includeInactive is rejected');
  });

  await test('Guard.notShellOrg', async () => {
    // orgId is a worker, not an X: shell org; validateOnly=true so nothing changes even if the guard failed.
    await expectRejected(token, 'ManageShellOrgStatus', status(me.id, orgName, 'X:ADM', true, later, 'true'));
    pass('Guard.notShellOrg', 'an orgId outside the X: shell orgs is rejected even with an X: orgCode');
  });

  let inactiveToday = false;
  await test('ShellOrg.inactivateToday', async () => {
    if (!orgWid) return skip('ShellOrg.inactivateToday', 'no org from ShellOrg.add');
    const a = await launchAndVerify(token, 'ManageShellOrgStatus', status(orgWid, orgName, 'X:ADM', true, today));
    expectAudit(a, 'Org Status', 'INACTIVATE');
    inactiveToday = true;
    pass('ShellOrg.inactivateToday', `${orgName} inactivated effective ${today}`);
  });

  await test('ShellOrg.reactivate', async () => {
    if (!inactiveToday) return skip('ShellOrg.reactivate', 'org was not inactivated today');
    const a = await launchAndVerify(token, 'ManageShellOrgStatus', status(orgWid, orgName, 'X:ADM', false, today));
    expectAudit(a, 'Org Status', 'REACTIVATE');
    pass('ShellOrg.reactivate', `${orgName} reactivated`);
  });

  await test('ShellOrg.inactivate', async () => {
    if (!orgWid) return skip('ShellOrg.inactivate', 'no org from ShellOrg.add');
    const a = await launchAndVerify(token, 'ManageShellOrgStatus', status(orgWid, orgName, 'X:ADM', true, later));
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
    const [a1, a2, a3, a5] = ['TEST', `TEST:${run3}`, '900', `${now.getUTCFullYear()}W1`];
    const pname = `${appCode}:PATTERN:${a1}:${a2}:${a3}:${a5}`;
    const a = await launchAndVerify(token, 'AddShellOrgPattern', {
      comsAppId: app.id, patternName: pname, workerId: me.id, attribute1: a1, attribute2: a2, attribute3: a3,
      attribute5: a5, effectiveDate: today, ...who(),
    });
    expectAudit(a, 'Shell Org Pattern', 'ADD');
    const pwid = await findOrg(pname);
    if (!pwid) throw new Error(`${pname} not found by WQL after the audit record was written`);
    pattern = { code: pname, wid: pwid, appCode };
    const b = await launchAndVerify(token, 'ManageShellOrgStatus', status(pwid, pname, appCode, true, later));
    expectAudit(b, 'Org Status', 'INACTIVATE');
    pass('Pattern.add', `${pname} created, audited and inactivated effective ${later}`);
  });

  await test('Guard.patternName', async () => {
    const app = ((await request('GET', `${BO}/comsApplications?limit=1`, token)).data || [])[0];
    if (!app) return skip('Guard.patternName', 'no COMS application');
    // A name that doesn't start with the application code must be rejected (nothing created, no audit).
    await expectRejected(token, 'AddShellOrgPattern', {
      comsAppId: app.id, patternName: `TEST:PATTERN:TEST:TEST:${run3}:901:${now.getUTCFullYear()}W1`, workerId: me.id,
      attribute1: 'TEST', attribute2: `TEST:${run3}`, attribute3: '901', attribute5: `${now.getUTCFullYear()}W1`, effectiveDate: today, ...who(),
    });
    pass('Guard.patternName', 'a pattern name that does not start with the application code is rejected');
  });

  // ── Role assignment: add a position to the test role, then remove it (net no change) ──
  await test('RoleAssignment.addRemove', async () => {
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
    const add = await launchAndVerify(token, 'AssignRolePositions', {
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
    const rem = await launchAndVerify(token, 'AssignRolePositions', {
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
  });

  // ── Role request: create → start review BP → cancel the event → DenyRoleRequest marks it Denied ──
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
    await launch(token, 'StartRoleRequestReview', { ref });
    let eventWid = null;
    for (let i = 0; i < 10 && !eventWid; i++) {
      await sleep(3000);
      eventWid = (await request('GET', `${BO}/comsAssignableRoles/${reqId}`, token)).reviewEventWid || null;
    }
    if (!eventWid) throw new Error(`StartRoleRequestReview did not link a review event to ${roleName} within 30 s`);
    const ev = await request('GET', `${BP}/events/${eventWid}`, token);
    const st = String(ev?.status?.descriptor || ev?.overallStatus?.descriptor || '');
    if (/complete|terminat|cancel|denied/i.test(st)) throw new Error(`new review event is already "${st}"`);
    pass('Request.startReview', `${roleName} has an open review event ("${st || 'in progress'}")`);

    await request('POST', `${BP}/events/${eventWid}/cancel`, token, { comment: 'Automated test run: cancel test request' });
    // Cancel is paired with DenyRoleRequest; BP-triggered orchestrations take ~2-3 min (up to 15).
    let r = null;
    for (let i = 0; i < 40; i++) {
      await sleep(15000);
      r = await request('GET', `${BO}/comsAssignableRoles/${reqId}`, token);
      if (r.status === 'Denied') break;
    }
    if (r?.status !== 'Denied') throw new Error(`${roleName} still "${r?.status}" 10 min after cancelling its review (DenyRoleRequest did not run)`);
    if (r.active !== false) throw new Error(`${roleName} is Denied but active=${r.active}`);
    const audits = (await readAll(token, 'comsAuditLogs')).filter((a) => a.roleName === roleName && a.action === 'DENY');
    if (!audits.length) throw new Error(`${roleName} is Denied but has no DENY audit record`);
    // The DENY record must name the person who denied or cancelled (here: the test user), not the BP.
    const by = audits[0];
    // changedByWid holds the Person WID from bp.initiatingPerson(), not the Worker WID, so compare names.
    if (by.triggeredBy !== me.descriptor || !by.changedByWid) {
      throw new Error(`DENY record shows Changed By "${by.triggeredBy}" (${by.changedByWid || 'no WID'}); expected ${me.descriptor}`);
    }
    // DenyRoleRequest copies the event's comment (here the cancel comment) into Denial Reason.
    if (!/Automated test run/.test(r.denialReason || '')) throw new Error(`${roleName} Denial Reason is "${r.denialReason || ''}", expected the cancel comment`);
    pass('Request.reviewCancelDeny', `${roleName}: cancelling the review marked it Denied, inactive, with the cancel comment as Denial Reason and a DENY audit naming ${me.descriptor}`);
  });

  // ── Two pending ISC requests, left open for review: one on the new shell org, one on the new pattern ──
  // Built the way the Assignable Role Manager page builds them (<org code>:ROLE:<name>, REQUEST audit,
  // then StartRoleRequestReview). Cleanup cancels their reviews, which marks them Denied.
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
    await request('POST', `${BO}/comsAuditLogs`, token, {
      timestamp: who().timestamp, objectType: 'Assignable Role', action: 'REQUEST', coReferenceId: roleName, coName: orgCode,
      details: `Assignable role request submitted: ${roleName} for org ${orgCode}`, triggeredBy: me.descriptor,
      roleName, effectiveDate: today, changedByWid: me.id, positionName: pos.name, positionWid: pos.wid,
    });
    await launch(token, 'StartRoleRequestReview', { ref });
    let eventWid = null;
    for (let i = 0; i < 10 && !eventWid; i++) {
      await sleep(3000);
      eventWid = (await request('GET', `${BO}/comsAssignableRoles/${req.id}`, token)).reviewEventWid || null;
    }
    if (!eventWid) throw new Error(`StartRoleRequestReview did not link a review event to ${roleName} within 30 s`);
    const ev = await request('GET', `${BP}/events/${eventWid}`, token);
    const st = String(ev?.status?.descriptor || ev?.overallStatus?.descriptor || '');
    if (/complete|terminat|cancel|denied/i.test(st)) throw new Error(`review event for ${roleName} is already "${st}"`);
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
  // Pending test requests can't be deleted either; cancelling their review closes them (DenyRoleRequest
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

  if (!APPLY) {
    pass('Cleanup.dryRun', `would inactivate ${activeTest.length} org(s), cancel ${pendingTest.length} pending review(s), delete ${testRoles.length} request(s) and ${audits.filter(testAudit).length}+ audit entr(ies)`);
    return;
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
        if (FIXED) await launchAndVerify(token, 'ManageShellOrgStatus', params(FIXED));
        else try { await launchAndVerify(token, 'ManageShellOrgStatus', params(today)); } catch (_) {
          eff = tomorrow;
          await launchAndVerify(token, 'ManageShellOrgStatus', params(tomorrow));
        }
      } catch (_) {
        // Workday allows one pending status change: an org whose inactivation is already scheduled is rejected.
        return skip(`Cleanup.inactivate ${code(o)}`, 'not changed: it most likely already has an inactivation scheduled');
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
    // Wait for DenyRoleRequest (usually 2-3 min) so its DENY audit records are cleared below.
    await test('Cleanup.pendingClosed', async () => {
      const ids = pendingTest.map((r) => r.id);
      for (let i = 0; i < 24; i++) {
        await sleep(15000);
        const open = (await readAll(token, 'comsAssignableRoles'))
          .filter((r) => ids.includes(r.id) && r.status !== 'Denied');
        if (!open.length) return pass('Cleanup.pendingClosed', `${ids.length} pending test request(s) now Denied`);
      }
      throw new Error('some cancelled test requests are not Denied after 6 min (DenyRoleRequest may still be queued)');
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
//   --unassign <P-id>  remove that position from the test role (--role), through AssignRolePositions,
//                      so the change gets the same REMOVE POSITION audit record as the page.
//   always:            pending requests whose Enabled For holds a bare WID get the unit's name, looked
//                      up in the same lists the request page's pickers search (FUH, academic units).
async function repair(token, me) {
  const apply = argv.includes('--apply');
  console.log(`\n-- Repair (${apply ? 'APPLY' : 'dry run: add --apply to change data'}) --`);
  const today = tenantDate();
  const who = () => ({ changedBy: me.descriptor, changedByWid: me.id, timestamp: new Date().toISOString().replace(/\.\d+Z$/, 'Z') });
  const idOf = (v) => String(v && typeof v === 'object' ? v.id : v || '');

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
    const rem = await launchAndVerify(token, 'AssignRolePositions', params);
    if (rem.objectType !== 'Role Assignment' || rem.action !== 'REMOVE POSITION') throw new Error(`audit is ${rem.objectType}/${rem.action}`);
    let gone = false;
    for (let i = 0; i < 18 && !gone; i++) {
      gone = !((await readRole())?.positions || []).some((p) => p.id === hit.id);
      if (!gone) await sleep(5000);
    }
    if (!gone) throw new Error(`REMOVE POSITION audited but "${hit.descriptor}" still shows on ${TEST_ROLE} after 90 s`);
    pass('Repair.unassign', `removed "${hit.descriptor}" from ${TEST_ROLE} (audit ${rem.id})`);
  });

  // Audit records with no action: written by test calls that reached AssignRolePositions with a
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

  // Requests whose Position Names hold a bare position WID instead of the name (seen on TESTROLE1031,
  // 2026-11-01). Look the WID up in allPositions and store the same full name the page sends.
  await test('Repair.positionNames', async () => {
    const roles = await readAll(token, 'comsAssignableRoles');
    const isWid = (s) => /^[0-9a-f]{32}$/.test(String(s).trim());
    const bad = roles.filter((r) => String(r.positionNames || '').split(/,\s*(?=[0-9a-f]{32}$|[0-9a-f]{32},|P-\d)/).some(isWid));
    if (!bad.length) return pass('Repair.positionNames', 'no request holds a bare WID in Position Names');
    const all = (await wql(token, 'SELECT cf_PositionID, workdayID, position_PositionManagement, cf_PositionText FROM allPositions WHERE supervisoryOrganization is not empty', 10000)).data || [];
    const left = [];
    for (const r of bad) {
      const parts = String(r.positionNames).split(/,\s*(?=[0-9a-f]{32}$|[0-9a-f]{32},|P-\d)/);
      const fixed = parts.map((p) => {
        if (!isWid(p)) return p;
        const pos = all.find((x) => idOf(x.workdayID) === p.trim());
        return pos ? (pos.position_PositionManagement?.descriptor || pos.cf_PositionText || pos.cf_PositionID) : null;
      });
      if (fixed.includes(null)) { left.push(r.roleName); warn('Repair.positionNames', `${r.roleName}: a WID in "${r.positionNames}" is not in allPositions; left as is`); continue; }
      const name = fixed.join(', ');
      if (!apply) { console.log(`  would set ${r.roleName} Position Names "${r.positionNames}" → "${name}"`); continue; }
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
    await launch(tok, 'StartRoleRequestReview', { ref });
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
