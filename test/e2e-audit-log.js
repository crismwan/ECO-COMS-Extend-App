#!/usr/bin/env node
/**
 * ECO-COMS Audit Log E2E Test Runner
 *
 * Tests that all app actions correctly write audit log entries to the
 * COMSAuditLog business object. Calls Workday REST APIs directly.
 *
 * Usage:
 *   node test/e2e-audit-log.js [--token <bearer_token>] [--verbose]
 *
 * Token sources (in priority order):
 *   1. --token CLI flag
 *   2. WD_DEV_TOKEN environment variable
 *   3. ~/.config/@workday/wdcli/config.json (wcpTenantAccessToken.ubc_wcpdev2)
 *
 * The script reads current audit log state, runs actions via REST API,
 * then validates new entries appeared with correct field values.
 */

const https = require('https');
const fs = require('fs');
const path = require('path');
const os = require('os');

// ─── Config ──────────────────────────────────────────────────────────────────

const APP_ID      = 'ecocomsphase_xclw_cm_sync2_vmzvxm';
const TENANT      = 'ubc_wcpdev2';
const BASE_BO     = `https://api.workday.com/apps/${APP_ID}/v1`;
const BASE_WQL    = 'https://api.workday.com/wql/v1';
const BASE_COMMON = 'https://api.workday.com/common/v1';

const VERBOSE     = process.argv.includes('--verbose');
const tokenFlagIdx = process.argv.indexOf('--token');
const TOKEN_FLAG  = tokenFlagIdx !== -1 ? process.argv[tokenFlagIdx + 1] : null;

// ─── Token resolution ─────────────────────────────────────────────────────────

function resolveToken() {
  if (TOKEN_FLAG)            return TOKEN_FLAG;
  if (process.env.WD_DEV_TOKEN) return process.env.WD_DEV_TOKEN;

  const cfgPath = path.join(os.homedir(), '.config', '@workday', 'wdcli', 'config.json');
  try {
    const cfg = JSON.parse(fs.readFileSync(cfgPath, 'utf8'));
    const t   = cfg?.wcpTenantAccessToken?.[TENANT];
    if (t) return t;
  } catch (_) { /* no config file */ }

  return null;
}

// ─── HTTP helper ──────────────────────────────────────────────────────────────

function req(method, url, token, body) {
  return new Promise((resolve, reject) => {
    const u     = new URL(url);
    const data  = body ? JSON.stringify(body) : null;
    const opts  = {
      hostname: u.hostname,
      path:     u.pathname + u.search,
      method,
      headers: {
        Authorization:  `Bearer ${token}`,
        Accept:         'application/json',
        ...(data ? { 'Content-Type': 'application/json', 'Content-Length': Buffer.byteLength(data) } : {})
      }
    };

    const r = https.request(opts, (res) => {
      let raw = '';
      res.on('data', d => raw += d);
      res.on('end', () => {
        if (VERBOSE) console.log(`  ${method} ${url} → ${res.statusCode}`);
        if (res.statusCode >= 400) {
          reject(new Error(`HTTP ${res.statusCode}: ${raw.slice(0, 300)}`));
        } else {
          try { resolve(JSON.parse(raw)); }
          catch (_) { resolve(raw); }
        }
      });
    });
    r.on('error', reject);
    if (data) r.write(data);
    r.end();
  });
}

const GET  = (url, tok)       => req('GET',  url, tok);
const POST = (url, tok, body) => req('POST', url, tok, body);

// ─── Audit log helpers ────────────────────────────────────────────────────────

async function fetchAuditLogs(token, limit = 100) {
  const res = await GET(`${BASE_BO}/comsAuditLogs?limit=${limit}`, token);
  return res.data || [];
}

async function getLatestAuditEntry(token, afterTimestamp) {
  const logs = await fetchAuditLogs(token, 100);
  if (!afterTimestamp) return logs[0] || null;
  // Return entries newer than the marker (by id order — latest first in BO API)
  return logs.filter(l => l.id !== afterTimestamp)[0] || null;
}

async function findNewEntries(token, knownIds, maxWait = 8000) {
  const start = Date.now();
  while (Date.now() - start < maxWait) {
    const logs = await fetchAuditLogs(token);
    const newOnes = logs.filter(l => !knownIds.has(l.id));
    if (newOnes.length > 0) return newOnes;
    await new Promise(r => setTimeout(r, 1500));
  }
  return [];
}

// ─── Test result tracking ─────────────────────────────────────────────────────

const results = [];

function pass(name, msg) {
  results.push({ status: 'PASS', name, msg });
  console.log(`  ✅  ${name}: ${msg}`);
}

function fail(name, msg, expected, actual) {
  results.push({ status: 'FAIL', name, msg, expected, actual });
  console.error(`  ❌  ${name}: ${msg}`);
  if (expected !== undefined) console.error(`       Expected: ${JSON.stringify(expected)}`);
  if (actual   !== undefined) console.error(`       Actual:   ${JSON.stringify(actual)}`);
}

function skip(name, msg) {
  results.push({ status: 'SKIP', name, msg });
  console.log(`  ⏭️   ${name}: ${msg}`);
}

function assertField(testName, entry, field, expected) {
  const actual = entry ? entry[field] : undefined;
  if (actual === expected) {
    pass(`${testName}.${field}`, `= "${expected}"`);
  } else {
    fail(`${testName}.${field}`, `field mismatch`, expected, actual);
  }
}

function assertContains(testName, entry, field, substring) {
  const actual = entry ? (entry[field] || '') : '';
  if (actual.includes(substring)) {
    pass(`${testName}.${field}`, `contains "${substring}"`);
  } else {
    fail(`${testName}.${field}`, `should contain "${substring}"`, `contains:${substring}`, actual);
  }
}

// ─── Worker helper ────────────────────────────────────────────────────────────

async function getMe(token) {
  const res = await GET(`${BASE_COMMON}/workers/me`, token);
  return res;
}

// ─── BO lookup helpers ────────────────────────────────────────────────────────

async function getComsApplications(token) {
  const res = await GET(`${BASE_BO}/comsApplications?limit=50`, token);
  return res.data || [];
}

async function getComsShellOrgs(token) {
  const res = await GET(`${BASE_BO}/comsShellOrgs?limit=100`, token);
  return res.data || [];
}

async function getComsAssignableRoles(token) {
  const res = await GET(`${BASE_BO}/comsAssignableRoles?limit=100`, token);
  return res.data || [];
}

// ─── TEST SUITE ───────────────────────────────────────────────────────────────

async function runTests(token) {
  console.log('\n═══════════════════════════════════════════════════════');
  console.log(' ECO-COMS Audit Log E2E Test Suite');
  console.log('═══════════════════════════════════════════════════════\n');

  // Get current worker
  let me;
  try {
    me = await getMe(token);
    console.log(`✔ Authenticated as: ${me.descriptor} (${me.id})\n`);
  } catch (e) {
    console.error('❌ Authentication failed:', e.message);
    process.exit(1);
  }

  // Snapshot existing audit log IDs
  const initialLogs = await fetchAuditLogs(token, 200);
  const initialIds  = new Set(initialLogs.map(l => l.id));
  console.log(`ℹ Found ${initialIds.size} existing audit log entries\n`);

  // ── Helper: snapshot + action + find new entry ─────────────────────────────
  async function runAction(label, actionFn) {
    const beforeLogs = await fetchAuditLogs(token, 200);
    const beforeIds  = new Set(beforeLogs.map(l => l.id));
    console.log(`\n─── ${label} ─────────────────────`);
    let result;
    try {
      result = await actionFn();
    } catch (e) {
      fail(label, `Action threw: ${e.message}`);
      return null;
    }
    const newEntries = await findNewEntries(token, beforeIds);
    if (newEntries.length === 0) {
      fail(label, 'No new audit log entry created within 8 seconds');
      return null;
    }
    const entry = newEntries[0];
    console.log(`  ℹ New audit entry: id=${entry.id}`);
    if (VERBOSE) console.log('  Entry:', JSON.stringify(entry, null, 2));
    return { entry, actionResult: result };
  }

  // ── TEST 1: Read audit log endpoint is accessible ──────────────────────────
  console.log('─── TEST 1: Audit log endpoint ──────────────────────');
  try {
    const logs = await fetchAuditLogs(token, 1);
    pass('AuditLogEndpoint', `Accessible, limit=1 returned ${logs.length} items`);
  } catch (e) {
    fail('AuditLogEndpoint', `Not accessible: ${e.message}`);
  }

  // ── TEST 2: Add Shell Org → audit log ─────────────────────────────────────
  const testOrgCode = `AUTOTEST${Date.now().toString().slice(-4)}`;
  let newOrgId = null;

  {
    // Find an application to use
    const apps = await getComsApplications(token);
    if (apps.length === 0) {
      skip('AddShellOrg', 'No COMS applications found — cannot create org');
    } else {
      const app    = apps[0];
      const appCode = app.id || app.code || app.descriptor;
      const orgName = `${appCode}:${testOrgCode}`;

      const result = await runAction('AddShellOrg', async () => {
        return await POST(`${BASE_BO}/comsShellOrgs`, token, {
          organizationName: orgName,
          organizationCode: orgName,
          comsApplication:  { id: app.id },
          effectiveDate:    '2026-10-29',
          isActive:         true,
          worker:           { id: me.id }
        });
      });

      if (result) {
        newOrgId = result.actionResult?.id;
        const { entry } = result;
        assertField('AddShellOrg', entry, 'objectType', 'Add New Shell Organization');
        assertField('AddShellOrg', entry, 'action',     'CREATE');
        assertContains('AddShellOrg', entry, 'coReferenceId', testOrgCode);
        assertContains('AddShellOrg', entry, 'coName',        testOrgCode);
        assertContains('AddShellOrg', entry, 'details',       'Application:');
        assertContains('AddShellOrg', entry, 'details',       'Effective Date:');
      }
    }
  }

  // ── TEST 3: Direct audit log POST (unit test of BO endpoint) ──────────────
  // This tests that the comsAuditLogs BO accepts POSTs with all fields
  {
    const result = await runAction('DirectAuditLogPost', async () => {
      return await POST(`${BASE_BO}/comsAuditLogs`, token, {
        timestamp:    new Date().toISOString(),
        objectType:   'AUTOMATED_TEST',
        action:       'TEST',
        coReferenceId: 'AUTO_TEST_REF',
        coName:       'Automated Test Entry',
        details:      `E2E test run at ${new Date().toISOString()}`,
        triggeredBy:  me.descriptor
      });
    });

    if (result) {
      const { entry } = result;
      assertField('DirectAuditLogPost', entry, 'objectType',    'AUTOMATED_TEST');
      assertField('DirectAuditLogPost', entry, 'action',        'TEST');
      assertField('DirectAuditLogPost', entry, 'coReferenceId', 'AUTO_TEST_REF');
      assertField('DirectAuditLogPost', entry, 'coName',        'Automated Test Entry');
      assertContains('DirectAuditLogPost', entry, 'details',    'E2E test run');
    }
  }

  // ── TEST 4: Check existing audit entries for expected field shapes ─────────
  {
    console.log('\n─── TEST 4: Existing audit entry field shapes ───────');
    const logs = await fetchAuditLogs(token, 20);
    const byType = {};
    for (const l of logs) {
      if (!byType[l.objectType]) byType[l.objectType] = l;
    }

    const expectedTypes = [
      'Add New Shell Organization',
      'Add New Shell Org Pattern',
      'COMSAssignableRole',
    ];

    for (const t of expectedTypes) {
      if (byType[t]) {
        const e = byType[t];
        const hasRequired = e.objectType && e.action && e.timestamp;
        if (hasRequired) {
          pass(`ExistingEntry[${t}]`, `Found with objectType, action, timestamp`);
        } else {
          fail(`ExistingEntry[${t}]`, `Missing required fields`, ['objectType','action','timestamp'],
               Object.keys(e).filter(k => e[k]));
        }
      } else {
        skip(`ExistingEntry[${t}]`, 'No existing entry of this type found yet');
      }
    }
  }

  // ── TEST 5: Validate assignable role audit entries ─────────────────────────
  {
    console.log('\n─── TEST 5: Assignable role audit entries ───────────');
    const logs = await fetchAuditLogs(token, 50);
    const roleEntries = logs.filter(l => l.objectType === 'COMSAssignableRole');

    if (roleEntries.length === 0) {
      skip('AssignableRoleAudit', 'No COMSAssignableRole entries found yet');
    } else {
      pass('AssignableRoleAudit', `Found ${roleEntries.length} role audit entries`);
      const e = roleEntries[0];
      // Role coReferenceId should follow pattern: <appCode>:ROLE:<roleName>
      if (e.coReferenceId && e.coReferenceId.includes(':ROLE:')) {
        pass('AssignableRoleAudit.coReferenceId', `Has :ROLE: separator: ${e.coReferenceId}`);
      } else if (e.coReferenceId) {
        fail('AssignableRoleAudit.coReferenceId',
          'Expected pattern <appCode>:ROLE:<roleName>', '<x>:ROLE:<y>', e.coReferenceId);
      } else {
        skip('AssignableRoleAudit.coReferenceId', 'coReferenceId is empty');
      }
    }
  }

  // ── TEST 6: Validate immutability (DELETE should fail) ────────────────────
  {
    console.log('\n─── TEST 6: Audit log immutability ─────────────────');
    const logs = await fetchAuditLogs(token, 1);
    if (logs.length === 0) {
      skip('AuditLogImmutability', 'No entries to test DELETE against');
    } else {
      const testId = logs[0].id;
      try {
        await req('DELETE', `${BASE_BO}/comsAuditLogs/${testId}`, token);
        fail('AuditLogImmutability', 'DELETE succeeded — log should be immutable!');
      } catch (e) {
        if (e.message.includes('HTTP 4')) {
          pass('AuditLogImmutability', `DELETE correctly rejected (${e.message.slice(0, 40)})`);
        } else {
          skip('AuditLogImmutability', `Unexpected error: ${e.message.slice(0, 80)}`);
        }
      }
    }
  }

  // ── Summary ────────────────────────────────────────────────────────────────
  const passed  = results.filter(r => r.status === 'PASS').length;
  const failed  = results.filter(r => r.status === 'FAIL').length;
  const skipped = results.filter(r => r.status === 'SKIP').length;

  console.log('\n═══════════════════════════════════════════════════════');
  console.log(` TEST RESULTS: ${passed} passed | ${failed} failed | ${skipped} skipped`);
  console.log('═══════════════════════════════════════════════════════\n');

  if (failed > 0) {
    console.error('FAILURES:\n');
    results.filter(r => r.status === 'FAIL').forEach(r => {
      console.error(`  ❌ ${r.name}: ${r.msg}`);
      if (r.expected !== undefined) console.error(`     Expected: ${JSON.stringify(r.expected)}`);
      if (r.actual   !== undefined) console.error(`     Actual:   ${JSON.stringify(r.actual)}`);
    });
    console.log('');
  }

  // Write JSON report
  const reportPath = path.join(__dirname, 'e2e-results.json');
  fs.writeFileSync(reportPath, JSON.stringify({
    runAt:   new Date().toISOString(),
    tenant:  TENANT,
    worker:  me.descriptor,
    summary: { passed, failed, skipped },
    results
  }, null, 2));
  console.log(`📄 Full report written to: ${reportPath}\n`);

  process.exit(failed > 0 ? 1 : 0);
}

// ─── Main ─────────────────────────────────────────────────────────────────────

const token = resolveToken();
if (!token) {
  console.error(`
ERROR: No Workday bearer token found.

Provide one via:
  1. CLI:  node test/e2e-audit-log.js --token <your_token>
  2. Env:  WD_DEV_TOKEN=<token> node test/e2e-audit-log.js
  3. wdcli: run 'wdcli app deploy ${APP_ID}' to log in, then re-run.

Token location after wdcli login:
  ~/.config/@workday/wdcli/config.json → wcpTenantAccessToken.${TENANT}
`);
  process.exit(1);
}

runTests(token).catch(e => {
  console.error('Unexpected error:', e);
  process.exit(1);
});
