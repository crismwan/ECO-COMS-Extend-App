#!/usr/bin/env python3
"""Drop inbound endpoints that nothing on their page uses (App Hub build warnings, 2026-11-06).

App Hub warns "The endpoint: X is declared but never used in the PMD" and each eager endpoint costs a call on every
page load. Its own check misses uses in tabs, card parameters, outbound values and event scripts (it flagged
shellOrgManager's allShellOrgs, used 26 times), so this step decides for itself: an endpoint is unused when its name
appears nowhere else on the page, other than as a quoted map key (a card parameter named like it, e.g. 'requestCount').

Runs last in rebuild_all. Earlier steps patch pages in place and may expect an endpoint they added, so this step keeps
every page it changes as it found it in tools/unused_src/, and `--restore` (first in rebuild_all) puts those back.
"""
import glob, json, os, re, shutil, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, '..', 'presentation')
SRC = os.path.join(HERE, 'unused_src')

if '--restore' in sys.argv:
    for p in glob.glob(os.path.join(SRC, '*.pmd')):
        shutil.copyfile(p, os.path.join(ROOT, os.path.basename(p)))
    print('drop_unused_endpoints --restore: pages as the earlier build steps left them')
    sys.exit(0)

shutil.rmtree(SRC, ignore_errors=True)
dropped = []
for p in sorted(glob.glob(os.path.join(ROOT, '*.pmd'))):
    d = json.load(open(p, encoding='utf-8'))
    orig = None
    # repeat: an endpoint used only by one just dropped (e.g. orgSubtypes feeding customOrganizations) goes too
    while True:
        eps = d.get('endPoints') or []
        keep, gone = [], []
        for e in eps:
            rest = dict(d)
            rest['endPoints'] = [x for x in eps if x is not e]
            text = json.dumps(rest)
            used = re.search(r"(?<![\w])" + re.escape(e['name']) + r"\b(?!['\"]\s*:)", text)
            (keep if used else gone).append(e)
        if not gone:
            break
        if orig is None:
            os.makedirs(SRC, exist_ok=True)
            shutil.copyfile(p, os.path.join(SRC, os.path.basename(p)))
            orig = True
        d['endPoints'] = keep
        dropped += [f"{os.path.basename(p)[:-4]}.{e['name']}" for e in gone]
    if orig:
        open(p, 'w', encoding='utf-8').write(json.dumps(d, indent=2, ensure_ascii=False) + '\n')
print('drop_unused_endpoints:', ', '.join(dropped) if dropped else 'none')
