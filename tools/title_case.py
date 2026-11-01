#!/usr/bin/env python3
"""Title Case for section headings (fieldSet titles) and card titles, chosen 2026-10-31 to match the
app's majority and Workday's own pages. Also rewrites the same strings in the builder scripts so a
rebuild keeps them. Idempotent."""
import json, os, re, glob
ROOT = os.path.join(os.path.dirname(__file__), '..')
SMALL = {'a', 'an', 'the', 'and', 'or', 'but', 'of', 'to', 'in', 'on', 'at', 'for', 'by', 'with', 'as', 'vs'}
def tc(s):
    if not isinstance(s, str) or '<%' in s or not s.strip(): return s
    words = s.split(' ')
    out = []
    for i, w in enumerate(words):
        core = w.strip('()"\'')
        if core.islower() and core.isalpha() and not (0 < i < len(words) - 1 and core in SMALL and not words[i - 1].endswith(':')):
            w = w.replace(core, core[0].upper() + core[1:], 1)
        out.append(w)
    return ' '.join(out)
changes = {}
def fix(o):
    if isinstance(o, dict):
        if o.get('type') == 'fieldSet' and isinstance(o.get('title'), str):
            new = tc(o['title'])
            if new != o['title']: changes[o['title']] = new; o['title'] = new
        for v in o.values(): fix(v)
    elif isinstance(o, list):
        for v in o: fix(v)
for f in glob.glob(os.path.join(ROOT, 'presentation', '*.pmd')):
    d = json.load(open(f)); before = json.dumps(d); fix(d)
    if json.dumps(d) != before: open(f, 'w').write(json.dumps(d, indent=2, ensure_ascii=False) + '\n')
for f in glob.glob(os.path.join(ROOT, 'presentation', 'cards', '*.card')):
    d = json.load(open(f)); h = d.get('header', {})
    new = tc(h.get('title'))
    if new != h.get('title'):
        changes[h['title']] = new; h['title'] = new
        open(f, 'w').write(json.dumps(d, indent=2, ensure_ascii=False) + '\n')
# keep the builders in step
for f in glob.glob(os.path.join(ROOT, 'tools', 'build_*.py')):
    s = open(f).read(); t = s
    for old, new in changes.items():
        t = t.replace('"' + old + '"', '"' + new + '"')
    if t != s: open(f, 'w').write(t)
for old, new in sorted(changes.items()): print(f'{old!r} -> {new!r}')
