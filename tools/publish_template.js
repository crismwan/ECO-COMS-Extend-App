#!/usr/bin/env node
/*
 * Publishes the pre-filled Bulk Role Changes Excel template to the app (EIB-style "get").
 *
 * 1. Reads every current role assignment on X: shell organizations from Workday (the same WQL query
 *    component the Download Template page uses: allShellAssignableRolesinTenant).
 * 2. Builds the validated workbook with tools/build_bulk_xlsx.py --data, one row per position, Action empty.
 * 3. Uploads it as a new COMSBulkTemplate record (POST comsBulkTemplatesCollection, multipart, as documented
 *    in developer.workday.com "Concept: fileUploader"). The Download Template page links the newest record.
 * 4. Reads it back (metadata and file size) to confirm.
 *
 *   node tools/publish_template.js            build and publish
 *   node tools/publish_template.js --dry-run  build only (writes the file, prints where)
 *
 * Token: WD_DEV_TOKEN (never printed). Needs python3 with openpyxl.
 */
const fs = require('fs');
const os = require('os');
const path = require('path');
const { execFileSync } = require('child_process');

const ROOT = path.join(__dirname, '..');
const APP_ID = 'ecocomsphase_xclw_cm_sync2_vmzvxm';
const API = 'https://api.workday.com';
const BO = `${API}/apps/${APP_ID}/v1`;
const DRY = process.argv.includes('--dry-run');
const token = process.env.WD_DEV_TOKEN;
const FILE_NAME = 'ECO-COMS-Bulk-Role-Template.xlsx';
const XLSX = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet';

async function call(method, url, opts = {}) {
  const res = await fetch(url, { method, ...opts, headers: { Authorization: `Bearer ${token}`, ...(opts.headers || {}) } });
  const text = await res.text();
  if (!res.ok) throw new Error(`HTTP ${res.status} ${method} ${new URL(url).pathname}: ${text.slice(0, 300)}`);
  try { return JSON.parse(text); } catch (_) { return text; }
}

function pacificNow() {
  const d = new Date();
  const parts = Object.fromEntries(new Intl.DateTimeFormat('en-CA', {
    timeZone: 'America/Los_Angeles', year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit',
    hour12: false, timeZoneName: 'short',
  }).formatToParts(d).map((p) => [p.type, p.value]));
  return `${parts.year}-${parts.month}-${parts.day} ${parts.hour === '24' ? '00' : parts.hour}:${parts.minute} ${parts.timeZoneName}`;
}

(async () => {
  if (!token) { console.error('WD_DEV_TOKEN is not set'); process.exit(2); }

  // 1. current assignments (same flattening as the Download Template grid)
  // the query takes the applications' organization types as a parameter (since the X:META / X:SHELL change); fill it the
  // way the pages do: the distinct first type of each application organization from the appTypes query (2026-11-08:
  // sending the raw <% types %> made WQL refuse the query, so the template hadn't refreshed since 2026-11-06)
  const wq = (name) => JSON.parse(fs.readFileSync(path.join(ROOT, 'presentation', 'wqlQueries', name + '.wqlquery'), 'utf8')).query;
  // appTypes takes the X:META / X:SHELL subtype WIDs, looked up by name as the pages do (WIDs differ between tenants)
  const subs = await call('GET', `${API}/wql/v1/data?limit=1000&query=${encodeURIComponent('SELECT subtype, COUNT(workdayID) FROM topLevelOrganizations GROUP BY subtype')}`, { headers: { Accept: 'application/json' } });
  const subtypeIds = (subs.data || []).filter((r) => r.subtype && ['X:META', 'X:SHELL'].includes(r.subtype.descriptor)).map((r) => r.subtype.id).join(',');
  const apps = await call('GET', `${API}/wql/v1/data?limit=10000&query=${encodeURIComponent(wq('appTypes').replace('<% subtypes %>', subtypeIds))}`, { headers: { Accept: 'application/json' } });
  const types = [...new Set((apps.data || []).map((o) => ((o.type1 || [])[0] || {}).id).filter(Boolean))];
  const q = wq('allShellAssignableRolesinTenant').replace('<% types %>', types.length ? types.join(',') : 'none');
  const res = await call('GET', `${API}/wql/v1/data?limit=10000&query=${encodeURIComponent(q)}`, { headers: { Accept: 'application/json' } });
  const rows = [];
  for (const r of res.data || []) {
    for (const ra of r.roleAssignments || []) {
      if (!ra.organization || !String(ra.organization.descriptor || '').startsWith('X:')) continue;
      for (const p of ra.cf_ZCF_EE_RoleAssignedToAsPositionRestrictions || []) {
        rows.push({
          role: r.role?.descriptor || '', roleWid: r.role?.id || '',
          org: ra.organization.descriptor || '', orgWid: ra.organization.id || '',
          position: p.descriptor || '', positionId: String(p.descriptor || '').split(' ')[0], assigneeWid: p.id || '',
        });
      }
    }
  }
  rows.sort((a, b) => (a.role + a.org + a.positionId).localeCompare(b.role + b.org + b.positionId));
  if (!rows.length) throw new Error('Workday returned no role assignments on X: organizations; not publishing an empty template');
  const asOf = pacificNow();
  console.log(`${rows.length} current role assignments (${new Set(rows.map((r) => r.role)).size} roles), as of ${asOf}`);

  // 2. build
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'ecocoms-template-'));
  const dataPath = path.join(dir, 'rows.json');
  const out = path.join(dir, FILE_NAME);
  fs.writeFileSync(dataPath, JSON.stringify(rows));
  execFileSync('python3', [path.join(ROOT, 'tools', 'build_bulk_xlsx.py'), '--data', dataPath, '--asof', asOf, '--out', out], { stdio: 'inherit' });
  const bytes = fs.readFileSync(out);
  console.log(`built ${out} (${bytes.length} bytes)`);
  if (DRY) return console.log('dry run: not published');

  // 3. publish (multipart: the file part plus a "data" part listing it under the collection name)
  const version = `v2 · ${asOf}`;
  // The JSON "data" part goes first: Workday treats the first part as the root body
  // ("Multipart Attachment requests must contain exactly one root body" otherwise).
  const form = new FormData();
  // A plain string field (no filename), as curl --form 'data="{...}"' sends it: the root body is the
  // one part that isn't a file.
  form.append('data', JSON.stringify({ comsBulkTemplates: [{
    file: 'cid:comsBulkTemplates0', version, asOf, rowCount: String(rows.length),
    notes: 'Pre-filled with every current role assignment on shell organizations', uploadedByName: 'Template publisher', uploadedAt: new Date().toISOString(),
  }] }));
  form.append('comsBulkTemplates0', new Blob([bytes], { type: XLSX }), FILE_NAME);
  const created = await call('POST', `${BO}/comsBulkTemplatesCollection`, { body: form, headers: { Accept: 'application/json' } });
  const rec = (created.comsBulkTemplates || [])[0];
  if (!rec || !rec.id) throw new Error(`unexpected response: ${JSON.stringify(created).slice(0, 300)}`);

  // 4. read back
  const meta = await call('GET', `${BO}/comsBulkTemplates/${rec.id}`, { headers: { Accept: 'application/json' } });
  const file = await fetch(`${BO}/comsBulkTemplates/${rec.id}`, { headers: { Authorization: `Bearer ${token}` } });
  const got = Buffer.from(await file.arrayBuffer());
  if (!file.ok || got.length !== bytes.length) throw new Error(`read-back failed: HTTP ${file.status}, ${got.length} of ${bytes.length} bytes`);
  const total = (await call('GET', `${BO}/comsBulkTemplates?limit=1`, { headers: { Accept: 'application/json' } })).total;
  console.log(`published ${meta.fileName} ${meta.version} (record ${rec.id}, ${got.length} bytes read back); ${total} template version(s) stored`);
})().catch((e) => { console.error('publish_template failed:', e.message); process.exit(1); });
