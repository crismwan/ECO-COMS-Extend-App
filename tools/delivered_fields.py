#!/usr/bin/env python3
"""Delivered Workday fields instead of tenant calculated fields (user, 2026-11-10).

A calculated field (`cf_...`) is tenant report setup, not part of the app, so every tenant the app moves to would need
it recreated under the same alias. Three have delivered fields that gave the same value on every row (e2e probe
2026-11-10, ubc_wcpdev2), so the app reads those instead:

  allPositions          cf_PositionID        -> positionID          (829/829 equal)
  allPositions          cf_PositionIsFilled  -> worker is not empty (829/829)
  topLevelOrganizations cf_active1           -> not inactive        (1704/1704)

Two stay, because nothing delivered matches (they are tenant prerequisites, see docs/ECO-COMS-NOTES.md):
  cf_PositionText (position search: the descriptor isn't searchable and positionTitle misses words, 22 vs 51 for
  "analyst"), cf_ZCF_EE_RoleAssignedToAsPositionRestrictions (role assignments: the delivered roleAssignedTo also
  lists workers and names positions by their worker, 2768/3459 equal).

Runs near the end of rebuild_all, after every page builder and before the sub-orchestration extraction. Earlier steps
patch files in place and look for their own text, so this step keeps each file as it found it in
tools/delivered_src/, and `--restore` (first in rebuild_all) puts those back.
"""
import glob, os, re, shutil, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, '..'))
SRC = os.path.join(HERE, 'delivered_src')

if '--restore' in sys.argv:
    n = 0
    for p in glob.glob(os.path.join(SRC, '**', '*'), recursive=True):
        if os.path.isfile(p):
            dst = os.path.join(ROOT, os.path.relpath(p, SRC))
            open(dst, 'w', encoding='utf-8').write(open(p, encoding='utf-8').read())
            n += 1
    print(f'delivered_fields --restore: {n} files as the earlier build steps left them')
    sys.exit(0)

shutil.rmtree(SRC, ignore_errors=True)


def keep(p):
    dst = os.path.join(SRC, os.path.relpath(p, ROOT))
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    if not os.path.exists(dst):
        shutil.copyfile(p, dst)


# Workday Script (pages, scripts): read the delivered field the way the calculated one was read
SCRIPT = [
    (re.compile(r'(\b[\w\]\)]+)\.cf_PositionIsFilled == false'), r'empty(\1.worker)'),
    (re.compile(r'(\b[\w\]\)]+)\.cf_PositionIsFilled == true'), r'!empty(\1.worker)'),
    (re.compile(r'\.cf_active1 == true'), '.inactive != true'),
    (re.compile(r'\.cf_active1 != true'), '.inactive == true'),
]
# WQL field lists and filters, and any leftover name (comments, JSON paths)
COMMON = [
    (re.compile(r'\bcf_PositionIsFilled = false\b'), 'worker is empty'),
    (re.compile(r'\bcf_PositionIsFilled\b'), 'worker'),
    (re.compile(r'\bcf_active1\b'), 'inactive'),
    (re.compile(r'\bcf_PositionID\b'), 'positionID'),
]
# Orchestrations (bulk role changes): "the position was found and has nobody in it", from the WQL response text.
# An empty instance field is left out of the response (probe: P-00030 had no "worker" key).
ORCH_UNFILLED = (
    'data.LookupPosition.response.toString().replace(\\" \\", \\"\\").contains(\\"\\\\\\"cf_PositionIsFilled\\\\\\":false\\")',
    '(if (data.LookupPosition.response.toString().replace(\\" \\", \\"\\").contains(\\"\\\\\\"positionID\\\\\\":\\")) '
    'data.LookupPosition.response.toString().replace(\\" \\", \\"\\").contains(\\"\\\\\\"worker\\\\\\":\\").not() else false)',
)

files = (glob.glob(os.path.join(ROOT, 'presentation', '*.pmd')) + glob.glob(os.path.join(ROOT, 'presentation', 'scripts', '*.script'))
         + glob.glob(os.path.join(ROOT, 'presentation', 'wqlQueries', '*.wqlquery'))
         + glob.glob(os.path.join(ROOT, 'presentation', 'cards', '*')) + glob.glob(os.path.join(ROOT, 'orchestration', '*')))
changed = []
for p in sorted(files):
    t = open(p, encoding='utf-8').read()
    n = t
    if '/orchestration/' in p.replace('\\', '/'):
        if 'LookupPosition' in n and 'cf_PositionIsFilled' in n:
            if ORCH_UNFILLED[0] not in n:
                sys.exit('delivered_fields: unfilled check not found in ' + os.path.basename(p))
            n = n.replace(*ORCH_UNFILLED)
    for rx, rep in SCRIPT + COMMON:
        n = rx.sub(rep, n)
    if n != t:
        keep(p)
        open(p, 'w', encoding='utf-8').write(n)
        changed.append(os.path.relpath(p, ROOT))

left = [os.path.relpath(p, ROOT) for p in files if re.search(r'cf_(PositionID|PositionIsFilled|active1)\b', open(p, encoding='utf-8').read())]
if left:
    sys.exit('delivered_fields: calculated fields left in ' + ', '.join(left))
dup = [os.path.relpath(p, ROOT) for p in files if re.search(r'\bworker, (\w+, )*worker\b', open(p, encoding='utf-8').read())]
if dup:
    sys.exit('delivered_fields: worker selected twice in ' + ', '.join(dup))
print(f'delivered_fields: positionID / worker / inactive instead of three calculated fields; {len(changed)} files')
