#!/usr/bin/env python3
"""Schema-driven pattern guards and correct org subtypes in the create orchestrations (idempotent).

* AddShellOrg sends subtype X:META (plain shell/meta orgs); AddShellOrgPattern sends X:SHELL.
  Organization_Add_Update only accepts Organization_Subtype_Name (no reference ID), checked in the
  v47.0 Human_Resources XSD on 2026-11-02 (Organization_Subtype_Reference_DataType).
* AddShellOrgPattern's CheckPatternName re-checks every name against the application's record:
    - starts with the application code + ':'
    - the next part is one of the record's namePrefix values (comma-separated; blank = PATTERN)
    - when the record has a patternSchema: the number of fields matches the schema (each schema
      field carries a "fieldLabel" key, so fields = occurrences of fieldLabel), and the name is upper case
    - no spaces
  Records without a patternSchema (Clockwork) keep exactly the old rule (APP:PATTERN:...).
Only functions already used in this repo's orchestrations or listed in developer.workday.com
"Reference: String Member Functions" are used.
"""
import copy, json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ORCH = ROOT / 'orchestration'


def load(name):
    return json.loads((ORCH / f'{name}.orchestration').read_text())


def save(name, d):
    (ORCH / f'{name}.orchestration').write_text(json.dumps(d, separators=(',', ':'), ensure_ascii=False))


def find(n, name):
    if isinstance(n, dict):
        v = n.get('_value')
        if isinstance(v, dict) and isinstance(v.get('name'), dict) and v['name'].get('_value') == name:
            return n
        for x in n.values():
            r = find(x, name)
            if r: return r
    elif isinstance(n, list):
        for x in n:
            r = find(x, name)
            if r: return r
    return None


def set_subtype(d, value):
    s = json.dumps(d, separators=(',', ':'), ensure_ascii=False)
    import re
    s2, n = re.subn(r'(Organization_Subtype_Name>)[^<]*(</bsvc:Organization_Subtype_Name)', r'\g<1>' + value + r'\g<2>', s)
    if n != 1: sys.exit(f'expected 1 subtype in template, found {n}')
    return json.loads(s2)


APP = 'data.GetApplication.response.asJSON().stringAtJsonPathWithDefault("$.appId", "")'
PREF = 'data.GetApplication.response.asJSON().stringAtJsonPathWithDefault("$.namePrefix", "")'
SCH = 'data.GetApplication.response.asJSON().stringAtJsonPathWithDefault("$.patternSchema", "")'
P = 'data.GetInputParams.patternName'
SEG = f'{P}.substringAfter({APP}.append(":")).substringBefore(":")'
LABELS = f'({SCH}.length() - {SCH}.replace("fieldLabel", "").length())'
COLONS = f'(({P}.length() - {P}.replace(":", "").length()) - ({APP}.length() - {APP}.replace(":", "").length()) - 1)'

ASSERTIONS = [
    (f'{APP}.startsWith("X:")', '"COMS application code must start with X:"'),
    (f'{P}.startsWith({APP}.append(":"))', f'"Pattern name must start with " + {APP} + ":, got " + {P}'),
    (f'",".append({PREF}.defaultIfBlank("PATTERN")).append(",").contains(",".append({SEG}).append(","))',
     f'"Pattern prefix " + {SEG} + " is not allowed for " + {APP} + ", got " + {P}'),
    (f'(if ({LABELS} == 0) true else ({LABELS} == {COLONS} * 10))',
     f'"Pattern name has the wrong number of fields for " + {APP} + ": " + {P}'),
    (f'(if ({SCH}.isEmpty()) true else {P}.upperCase().equals({P}))', f'"Pattern name must be upper case: " + {P}'),
    (f'{P}.contains(" ").not()', f'"Pattern name must not contain spaces: " + {P}'),
]


def main():
    # Add Shell Org: the page picks X:META or X:SHELL; anything else becomes X:META (never free text)
    d = set_subtype(load('AddShellOrg'), '{{data.GetInputParams.orgSubtype}}')
    gip = find(d, 'GetInputParams')['_value']['values']['_value']
    if not any(a['_value']['param']['_value']['name']['_value'] == 'orgSubtype' for a in gip):
        proto = next(a for a in gip if a['_value']['param']['_value']['name']['_value'] == 'orgType')
        a = copy.deepcopy(proto)
        a['_value']['param']['_value']['name']['_value'] = 'orgSubtype'
        a['_value']['expr']['_value']['source']['_value'] = (
            '(if (data("start", "queryParams").getParam("orgSubtype", "X:META").equals("X:SHELL")) "X:SHELL" else "X:META")')
        gip.insert(gip.index(proto) + 1, a)
    save('AddShellOrg', d)

    d = set_subtype(load('AddShellOrgPattern'), 'X:SHELL')
    node = find(d, 'CheckPatternName')
    proto = node['_value']['assertions']['_value'][0]
    out = []
    for cond, msg in ASSERTIONS:
        a = copy.deepcopy(proto)
        a['_value']['assertion']['_value']['source']['_value'] = cond
        a['_value']['message']['_value']['source']['_value'] = msg
        out.append(a)
    node['_value']['assertions']['_value'] = out
    node['_value']['notes']['_value'][0]['_value']['value']['_value'] = (
        "Guard: the pattern name must start with the application code, use one of the application's "
        "prefixes (namePrefix, default PATTERN), and match its patternSchema field count; upper case, no spaces")
    save('AddShellOrgPattern', d)
    print('AddShellOrg: subtype from orgSubtype (X:META or X:SHELL); AddShellOrgPattern: subtype X:SHELL,', len(out), 'assertions')


if __name__ == '__main__':
    main()
