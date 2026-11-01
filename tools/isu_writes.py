#!/usr/bin/env python3
"""ISU lockdown for page writes (ADMIN-RUNBOOK section 3). NOT applied on main: run it on a branch once the
ISU exists and is assigned to the app in App Manager in the target tenant, then deploy and run
`node test/run-tests.js isu`.

- SMD: adds the `isuAuth` auth type (scheme ISU, username below) next to `sso`.
- Every page write (outbound endpoint) to the request or audit records (BUSINESS-OBJECT `comsAssignableRoles`
  / `comsAuditLogs`) runs as the ISU instead of the signed-in user, so users can be cut back to View/Get on
  those records (tamper-resistant audit log and request status). This is the rule the isu test suite checks.
- Business process calls (`workday-bp`) and orchestration launches stay `sso`: the requester must stay the
  initiator, or Exclude Initiator stops working.

Idempotent. `--undo` switches the same endpoints back to `sso` and removes the SMD entry.
Replaces the old `isu-writes` branch (one commit from 2026-10-31, 61 commits behind main by 2026-11-01).
"""
import json, os, re, sys

ROOT = os.path.join(os.path.dirname(__file__), '..', 'presentation')
ISU_USER = 'DNU_ISU_ECO_COMS_DEPLOY_CMM'
TARGET = re.compile(r'comsAuditLogs|comsAssignableRoles')
undo = '--undo' in sys.argv
new_auth, old_auth = ('sso', 'isuAuth') if undo else ('isuAuth', 'sso')

changed = []
for f in sorted(os.listdir(ROOT)):
    if not f.endswith('.pmd'):
        continue
    p = os.path.join(ROOT, f)
    raw = open(p).read()
    d = json.loads(raw)
    hit = False
    for e in (d.get('outboundData') or {}).get('outboundEndPoints', []):
        if e.get('type') != 'outboundVariable' and e.get('baseUrlType') == 'BUSINESS-OBJECT' \
                and TARGET.search(str(e.get('url', ''))) and e.get('authType', 'sso') == old_auth:
            e['authType'] = new_auth
            hit = True
    if hit:
        open(p, 'w').write(json.dumps(d, indent=2, ensure_ascii=False) + '\n')
        changed.append(f[:-4])

smd_path = [os.path.join(ROOT, f) for f in os.listdir(ROOT) if f.endswith('.smd')][0]
smd = json.load(open(smd_path))
types = smd['siteAuth']['authTypes']
has = any(t.get('id') == 'isuAuth' for t in types)
if undo and has:
    smd['siteAuth']['authTypes'] = [t for t in types if t.get('id') != 'isuAuth']
elif not undo and not has:
    types.append({"id": "isuAuth", "scheme": "ISU", "username": ISU_USER})
if has == undo:
    open(smd_path, 'w').write(json.dumps(smd, indent=2, ensure_ascii=False) + '\n')
    changed.append(os.path.basename(smd_path))
print(('undo: ' if undo else '') + 'isu_writes changed:', changed)
