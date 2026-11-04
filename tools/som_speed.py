#!/usr/bin/env python3
"""Shell Org Manager speed (2026-11-04; page took 1.4-1.8 s, 188 KB).

The page loaded two lists of the same organizations: allShellOrgs (code contains 'X:', 609 rows) and
shellOrgPatterns (existingPatterns: code contains 'PATTERN', 396 rows). Every use of the pattern list filters it to
codes starting 'X:' and containing ':PATTERN:', which allShellOrgs already holds with the same fields (workdayID,
organizationByName, code, cf_active1). So the pattern filters read allShellOrgs and the second query is dropped.
Server-side filtering by application isn't used: some filters match organizations by name prefix, not code.
Idempotent; runs after the builders that write shellOrgManager.pmd.
"""
import json, os
p = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'presentation', 'shellOrgManager.pmd')
raw = open(p, encoding='utf-8').read()
d = json.loads(raw)
s = json.dumps(d, ensure_ascii=False).replace('shellOrgPatterns.data', 'allShellOrgs.data')
d = json.loads(s)
if 'shellOrgPatterns.' not in s:
    d['endPoints'] = [e for e in d['endPoints'] if e['name'] != 'shellOrgPatterns']
new = json.dumps(d, indent=2, ensure_ascii=False) + '\n'
if new != raw:
    open(p, 'w', encoding='utf-8').write(new)
print('som_speed: ' + ('patterns read from allShellOrgs' if new != raw else 'no change'))
