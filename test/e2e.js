#!/usr/bin/env node
/**
 * ECO-COMS live end-to-end tests against the ubc_wcpdev2 tenant.
 *
 *   node test/e2e.js                 # smoke suite: read-only, safe on every deploy
 *   node test/e2e.js --suite full    # smoke + write tests (creates and inactivates a TEST shell org)
 *   node test/e2e.js --verbose
 *
 * Token (never printed): --token <t>, else WD_DEV_TOKEN, else ~/.config/@workday/wdcli/config.json
 * (wcpTenantAccessToken.ubc_wcpdev2). Same PKCE user token the deploy workflow uses.
 *
 * Results: console + test/e2e-results.json. Exit code 1 if any test fails.
 * Coverage map and manual checks: test/README.md.
 */

'use strict';
const https = require('https');
const fs = require('fs');
const path = require('path');
const os = require('os');

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
const SUITE = arg('--suite') || 'smoke';

// Fixed vocabulary (CLAUDE.md "Audit log design"). A new value here means a page or
// orchestration started writing something the viewer and reports don't expect.
const OBJECT_TYPES = ['Shell Org', 'Shell Org Pattern', 'Org Status', 'Role Assignment', 'Assignable Role'];
const ACTIONS = ['ADD', 'INACTIVATE', 'REACTIVATE', 'ASSIGN POSITION', 'REMOVE POSITION', 'REQUEST', 'APPROVE', 'DENY', 'DELETE'];
const BO_COLLECTIONS = ['comsApplications', 'comsAssignableRoles', 'comsAuditLogs', 'comsRoleAssignments', 'comsShellOrgRequests'];

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
  const icon = { PASS: 'PASS', FAIL: 'FAIL', SKIP: 'SKIP' }[status];
  (status === 'FAIL' ? console.error : console.log)(`  ${icon}  ${name}: ${msg}`);
};
const pass = (n, m) => record('PASS', n, m);
const fail = (n, m) => record('FAIL', n, m);
const skip = (n, m) => record('SKIP', n, m);
async function test(name, fn) {
  try { await fn(); } catch (e) { fail(name, e.message); }
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

// ─── Smoke suite (read-only) ──────────────────────────────────────────────────
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
  await test('BP.pendingEventsOpen', async () => {
    const pending = roles.filter((r) => r.status === 'Pending ISC Review' && r.reviewEventWid).slice(0, 5);
    if (!pending.length) return skip('BP.pendingEventsOpen', 'no pending requests with a review event');
    for (const r of pending) {
      const ev = await request('GET', `${BP}/events/${r.reviewEventWid}`, token);
      const status = ev?.status?.descriptor || ev?.overallStatus?.descriptor || '';
      if (/denied|cancel|rescind/i.test(status)) throw new Error(`${r.roleName} is Pending in ECO-COMS but its review event is ${status}`);
    }
    pass('BP.pendingEventsOpen', `${pending.length} pending request(s) have an open review event`);
  });
}

// ─── Full suite (writes to the tenant) ────────────────────────────────────────
async function full(token, me) {
  console.log('\n-- Full (writes TEST data, then inactivates it) --');
  const stamp = new Date().toISOString().replace(/\D/g, '').slice(2, 12); // yyMMddHHmm
  const orgName = `X:ADM:TEST:CI:${stamp}`;
  const now = new Date();
  const ts = now.toISOString().replace(/\.\d+Z$/, 'Z');
  const today = ts.slice(0, 10);
  const later = new Date(now.getTime() + 45 * 86400000).toISOString().slice(0, 10);
  const who = { changedBy: me.descriptor, changedByWid: me.id, timestamp: ts };

  let orgWid = null;
  await test('ShellOrg.add', async () => {
    const a = await launchAndVerify(token, 'AddShellOrg', {
      comsAppId: '', orgType: 'X:ADM', organizationName: orgName, organizationCode: orgName,
      workerId: me.id, effectiveDate: today, ...who,
    });
    if (a.objectType !== 'Shell Org' || a.action !== 'ADD') throw new Error(`audit record is ${a.objectType}/${a.action}, expected Shell Org/ADD`);
    const r = await wql(token, `SELECT workdayID, code FROM topLevelOrganizations WHERE code = '${orgName}'`, 1);
    orgWid = r.data?.[0]?.workdayID?.id || r.data?.[0]?.workdayID;
    if (!orgWid) throw new Error(`${orgName} not found by WQL after the audit record was written`);
    pass('ShellOrg.add', `${orgName} created and audited`);
  });

  await test('ShellOrg.inactivate', async () => {
    if (!orgWid) return skip('ShellOrg.inactivate', 'no org from ShellOrg.add');
    const a = await launchAndVerify(token, 'ManageShellOrgStatus', {
      orgId: orgWid, action: 'INACTIVATE', orgCode: orgName, orgName, includeInactive: 'true',
      effectiveDate: later, patternName: orgName, orgType: 'X:ADM', comsAppId: 'X:ADM', validateOnly: 'false', ...who,
    });
    if (a.objectType !== 'Org Status' || a.action !== 'INACTIVATE') throw new Error(`audit record is ${a.objectType}/${a.action}, expected Org Status/INACTIVATE`);
    pass('ShellOrg.inactivate', `${orgName} inactivated effective ${later}`);
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
  testRoles.forEach((r) => console.log(`   delete  ${r.id}  ${r.roleName}  [${r.status}]${r.reviewEventWid ? '  review event ' + r.reviewEventWid : ''}`));
  console.log('   kept (not identified as test):');
  roles.filter((r) => !testRoles.includes(r)).forEach((r) => console.log(`     ${r.id}  ${r.roleName}  [${r.status}]  requested ${r.requestedDate || '?'}`));

  // 3. Test audit entries -> delete. Done last so the inactivation records above are removed too.
  const audits = (await request('GET', `${BO}/comsAuditLogs?limit=100`, token)).data || [];
  const testAudit = (a) => EXTRA_TEST_IDS.includes(a.id) || isTestText(a.coName, a.coReferenceId, a.roleName, a.details);
  console.log(`\nAudit entries: ${audits.length} read, ${audits.filter(testAudit).length} to delete:`);
  audits.filter(testAudit).forEach((a) => console.log(`   delete  ${a.id}  ${a.timestamp}  ${a.objectType}/${a.action}  ${a.coName || ''} ${a.roleName || ''}`.trimEnd()));
  console.log('   kept (not identified as test):');
  audits.filter((a) => !testAudit(a)).forEach((a) => console.log(`     ${a.id}  ${a.timestamp}  ${a.objectType}/${a.action}  ${a.coName || ''} ${a.roleName || ''} ${a.positionName || ''}`.trimEnd()));

  if (!APPLY) {
    pass('Cleanup.dryRun', `would inactivate ${activeTest.length} org(s), delete ${testRoles.length} request(s) and ${audits.filter(testAudit).length}+ audit entr(ies)`);
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
      if (FIXED) await launchAndVerify(token, 'ManageShellOrgStatus', params(FIXED));
      else try { await launchAndVerify(token, 'ManageShellOrgStatus', params(today)); } catch (_) {
        eff = tomorrow;
        await launchAndVerify(token, 'ManageShellOrgStatus', params(tomorrow));
      }
      pass(`Cleanup.inactivate ${code(o)}`, `inactivated effective ${eff}`);
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

// ─── Main ─────────────────────────────────────────────────────────────────────
(async () => {
  const token = resolveToken();
  if (!token) {
    console.error('No Workday token: pass --token, set WD_DEV_TOKEN, or log in with wdcli.');
    process.exit(2);
  }
  console.log(`ECO-COMS e2e: suite=${SUITE} tenant=${TENANT}`);
  let me;
  try {
    me = await request('GET', `${API}/common/v1/workers/me`, token);
    pass('Auth', `signed in as ${me.descriptor}`);
  } catch (e) {
    fail('Auth', e.message);
  }
  if (me) {
    if (SUITE === 'cleanup') {
      await cleanup(token, me);
    } else {
      await smoke(token, me);
      if (SUITE === 'full') await full(token, me);
    }
  }

  const count = (s) => results.filter((r) => r.status === s).length;
  const summary = { passed: count('PASS'), failed: count('FAIL'), skipped: count('SKIP') };
  console.log(`\n${summary.passed} passed, ${summary.failed} failed, ${summary.skipped} skipped`);
  fs.writeFileSync(path.join(__dirname, 'e2e-results.json'),
    JSON.stringify({ runAt: new Date().toISOString(), suite: SUITE, tenant: TENANT, summary, results }, null, 2));

  if (process.env.GITHUB_STEP_SUMMARY) {
    const lines = [`## ECO-COMS e2e (${SUITE})`, '', `${summary.passed} passed, ${summary.failed} failed, ${summary.skipped} skipped`, '',
      '| Result | Test | Detail |', '|---|---|---|',
      ...results.map((r) => `| ${r.status} | ${r.name} | ${String(r.msg).replace(/\|/g, '/').slice(0, 160)} |`),
      '', '<details><summary>Full output</summary>', '', '```', ...transcript, '```', '</details>'];
    fs.appendFileSync(process.env.GITHUB_STEP_SUMMARY, lines.join('\n') + '\n');
  }
  process.exit(summary.failed ? 1 : 0);
})();
