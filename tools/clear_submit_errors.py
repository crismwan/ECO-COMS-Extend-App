#!/usr/bin/env python3
"""Every OK check (onSubmit) starts by clearing the error on each widget it may flag.

An error set by onSubmit stays after the user fixes the cause, so OK keeps failing until a reload
(CLAUDE.md "Widget validation"). This pass adds the missing clearError() calls at the top of every
page's onSubmit; the static check Static.submitClears fails if one is missing.
"""
import glob, json, os, re

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')


def missing(sub):
    first = sub.find('setError(')
    if first < 0:
        return []
    flagged = sorted(set(re.findall(r'\b([a-zA-Z][A-Za-z0-9]*)\.setError\(', sub)) - {'self'})
    cleared = set(re.findall(r'\b([a-zA-Z][A-Za-z0-9]*)\.clearError\(\)', sub[:first]))
    return [w for w in flagged if w not in cleared]


changed = 0
for p in sorted(glob.glob(os.path.join(ROOT, 'presentation', '*.pmd'))):
    d = json.load(open(p, encoding='utf-8'))
    holder = d if isinstance(d.get('onSubmit'), str) else d.get('presentation', {})
    sub = holder.get('onSubmit')
    if not isinstance(sub, str):
        continue
    add = missing(sub)
    if not add:
        continue
    assert sub.lstrip().startswith('<%'), p
    head, rest = sub.split('<%', 1)
    holder['onSubmit'] = head + '<%\n' + ''.join(f'  {w}.clearError();\n' for w in add) + rest.lstrip('\n')
    open(p, 'w', encoding='utf-8').write(json.dumps(d, indent=2, ensure_ascii=False) + '\n')
    changed += 1
    print(f'  {os.path.basename(p)}: clear {", ".join(add)} first')
print(f'onSubmit clears added on {changed} page(s)')
