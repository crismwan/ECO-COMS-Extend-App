#!/usr/bin/env node
/**
 * ECO-COMS tests: one runner for every suite.
 *
 *   node test/run-tests.js static            repo checks, no tenant access (blocks upload; every push)
 *   node test/run-tests.js smoke             read-only live checks (after every deploy)
 *   node test/run-tests.js full              smoke + write tests for every flow (manual; leaves TEST data)
 *   node test/run-tests.js cleanup [--apply] list (default) or remove TEST data
 *   node test/run-tests.js isu               ISU lockdown checks: only once ISU writes are live (see README)
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
const SUITES_ALL = ['static', 'smoke', 'full', 'cleanup', 'isu'];
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
  'submitButton|deleteAssignableRole.pmd': 'no way to submit; decide delete vs cancelling the ISC review BP before re-enabling',
  'submitButton|newShellOrgConfirm.pmd': 'page no longer used by createShellOrgWizard; candidate for removal',
  'submitButton|newShellOrgPatternConfirm.pmd': 'page no longer used by createShellOrgPatternWizard; candidate for removal',
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
  const ids = async () => ((await request('GET', `${BO}/comsAuditLogs?limit=100`, token)).data || []);
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
  const before = new Set((((await request('GET', `${BO}/comsAuditLogs?limit=100`, token)).data) || []).map((a) => a.id));
  await launch(token, name, params);
  await sleep(20000);
  const fresh = (((await request('GET', `${BO}/comsAuditLogs?limit=100`, token)).data) || []).filter((a) => !before.has(a.id));
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
    audits = (await request('GET', `${BO}/comsAuditLogs?limit=100`, token)).data || [];
    pass('Audit.read', `${audits.length} recent records`);
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
    roles = (await request('GET', `${BO}/comsAssignableRoles?limit=100`, token)).data || [];
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
}

// ─── Full suite (writes to the tenant) ────────────────────────────────────────
async function full(token, me) {
  console.log('\n-- Full (writes TEST data, then reverts or inactivates it) --');
  // Short, readable run id: the GitHub run number (RUN15), or a random number for local runs.
  const runNo = process.env.GITHUB_RUN_NUMBER || String(100 + Math.floor(Math.random() * 900));
  const run3 = String(runNo).slice(-3).padStart(3, '0');
  const orgName = `X:ADM:TEST:CI:RUN${runNo}`;
  const now = new Date();
  const today = now.toISOString().slice(0, 10);
  const later = new Date(now.getTime() + 45 * 86400000).toISOString().slice(0, 10);
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
    const audits = ((await request('GET', `${BO}/comsAuditLogs?limit=100`, token)).data || []).filter((a) => a.roleName === roleName && a.action === 'DENY');
    if (!audits.length) throw new Error(`${roleName} is Denied but has no DENY audit record`);
    pass('Request.reviewCancelDeny', `${roleName}: cancelling the review marked it Denied, inactive, with a DENY audit`);
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
  const today = new Date().toISOString().slice(0, 10);
  const ts = new Date().toISOString().replace(/\.\d+Z$/, 'Z');

  // 1. Active test orgs and patterns -> inactivate effective today (Workday orgs can't be deleted).
  const orgs = (await wql(token, 'SELECT workdayID, organizationByName, code, cf_active1 FROM topLevelOrganizations WHERE code contains \'X:\'', 10000)).data || [];
  const testOrgs = orgs.filter((o) => isTestText(code(o)));
  const activeTest = testOrgs.filter((o) => o.cf_active1 === true || o.cf_active1 === 'true' || o.cf_active1 === 1);
  console.log(`\nOrgs: ${orgs.length} X: orgs, ${testOrgs.length} test orgs, ${activeTest.length} still active (to inactivate):`);
  activeTest.forEach((o) => console.log(`   inactivate  ${code(o)}`));
  testOrgs.filter((o) => !activeTest.includes(o)).forEach((o) => console.log(`   already inactive  ${code(o)}`));

  // 2. Test role requests -> delete (pending ones included; their review events are reported).
  const roles = (await request('GET', `${BO}/comsAssignableRoles?limit=100`, token)).data || [];
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
  const audits = (await request('GET', `${BO}/comsAuditLogs?limit=100`, token)).data || [];
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

  const tomorrow = new Date(Date.now() + 86400000).toISOString().slice(0, 10);
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
        const open = ((await request('GET', `${BO}/comsAssignableRoles?limit=100`, token)).data || [])
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
  const auditsNow = (await request('GET', `${BO}/comsAuditLogs?limit=100`, token)).data || [];
  let deleted = 0;
  for (const a of auditsNow.filter(testAudit)) {
    await test(`Cleanup.deleteAudit ${a.id}`, async () => {
      await request('DELETE', `${BO}/comsAuditLogs/${a.id}`, token);
      deleted++;
    });
  }
  pass('Cleanup.audit', `deleted ${deleted} test audit entr(ies)`);
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
    const r = ((await request('GET', `${BO}/comsAssignableRoles?limit=100`, token)).data || []).find((x) => /TEST/.test(x.roleName || ''));
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
