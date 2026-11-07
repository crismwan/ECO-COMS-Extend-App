#!/usr/bin/env python3
"""Schema-driven pattern guards and correct org subtypes in the create orchestrations (idempotent).

* IORC_0037_XFD_SEC_Create_Application_Shell_Org sends subtype X:META (plain shell/meta orgs); IORC_0037_XFD_SEC_Create_Pattern_Shell_Org sends X:SHELL.
  Organization_Add_Update only accepts Organization_Subtype_Name (no reference ID), checked in the
  v47.0 Human_Resources XSD on 2026-11-02 (Organization_Subtype_Reference_DataType).
* IORC_0037_XFD_SEC_Create_Pattern_Shell_Org's CheckPatternName re-checks every name against the application's record:
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
# 20 characters per optional field: the stored schema is compact JSON ("optionalField":true)
OPT = f'({SCH}.length() - {SCH}.replace("\\"optionalField\\":true", "").length())'
COLONS = f'(({P}.length() - {P}.replace(":", "").length()) - ({APP}.length() - {APP}.replace(":", "").length()) - 1)'

ASSERTIONS = [
    (f'{APP}.isEmpty().not()', '"The pattern\'s application has no application ID"'),
    (f'{P}.startsWith({APP}.append(":"))', f'"Pattern name must start with " + {APP} + ":, got " + {P}'),
    (f'",".append({PREF}.defaultIfBlank("PATTERN")).append(",").contains(",".append({SEG}).append(","))',
     f'"Pattern prefix " + {SEG} + " is not allowed for " + {APP} + ", got " + {P}'),
    # optional trailing fields (2026-11-06): between the required count and the full count of fields
    (f'(if ({LABELS} == 0) true else (if ({COLONS} * 10 <= {LABELS}) ({COLONS} * 20 >= {LABELS} * 2 - {OPT}) else false))',
     f'"Pattern name has the wrong number of fields for " + {APP} + ": " + {P}'),
    (f'(if ({SCH}.isEmpty()) true else {P}.upperCase().equals({P}))', f'"Pattern name must be upper case: " + {P}'),
    (f'{P}.contains(" ").not()', f'"Pattern name must not contain spaces: " + {P}'),
]


# Academic unit Code check (2026-11-07): a field whose Workday check is "Academic unit code" ("lookup":"academicUnitCode"
# in the stored schema, written by Maintain Application Pattern) must hold the Code of an active academic unit. The page
# checks it; this re-checks it on the server. Its value is the matching attributeN the page sends (fields 1-5).
# The WQL call always runs (an empty value finds nothing); the check only applies when there is a value other than *.
# Query URL hand-encoded as Change Shell Org Status does ('+' in a code as %2B; G+PS exists); probe 2026-11-07 found
# MATH and G+PS, not MAHT.
LK = '"\\"lookup\\":\\"academicUnitCode\\""'
PRE = f'{SCH}.substringBefore({LK})'
# Workday stores the record's JSON keys in its own order ("lookup" can come before "fieldLabel", live record 2026-11-07),
# so the field's position is the number of "},{" boundaries between field objects before its lookup key (3 characters each).
POS = f'({PRE}.length() - {PRE}.replace("}},{{", "").length())'
ATTR = lambda n: f'data.GetInputParams.attribute{n}.replace("\'", "")'
UNIT_VALUE = (f'(if ({SCH}.contains({LK}).not()) "" else '
              + ''.join(f'(if ({POS} == {3 * (n - 1)}) {ATTR(n)} else ' for n in range(1, 6)) + '""' + ')' * 6)
UV = 'data.UnitCodeInput.unitValue'
UNIT_PATH = ('"/wql/v1/data?limit=1&query=SELECT%20academicUnitCode%20FROM%20academicUnits%20WHERE%20inactive%20%3D%20false'
             '%20AND%20academicUnitCode%20%3D%20%27"'
             f'.append({UV}.replace("%", "").replace("+", "%2B").replace("&", "").replace("#", "")).append("%27")')
UNIT_ASSERT = (f'(if ({UV}.isEmpty().or({UV}.equals("*"))) true else '
               f'data.LookupUnitCode.response.asJSON().stringAtJsonPathWithDefault("$.data[0].academicUnitCode", "").equals({UV}))',
               f'"Academic unit code " + {UV} + " is not an active academic unit in Workday"')


# Course subject and academic period checks (2026-11-07), the same way: the field's value (fields 1-5) is looked up with
# a one-row WQL query, so this stays quick with tens of thousands of subjects or periods. A value that is empty or starts
# with * is not checked. A period's short form names a period: 2024W1 = a name starting 2024 that contains
# "Winter Term 1" (W2 Winter Term 2, W Winter, S Summer, a bare year any period); comsPatterns.lookupWql does the same.
def field_value(kind):
    lk = f'"\\"lookup\\":\\"{kind}\\""'
    pre = f'{SCH}.substringBefore({lk})'
    pos = f'({pre}.length() - {pre}.replace("}},{{", "").length())'
    return (f'(if ({SCH}.contains({lk}).not()) "" else '
            + ''.join(f'(if ({pos} == {3 * (n - 1)}) {ATTR(n)}.replace("\\\\", "").trim() else ' for n in range(1, 6)) + '""' + ')' * 6)


ENC = lambda v: f'{v}.replace("%", "").replace("+", "%2B").replace("&", "").replace("#", "").replace(" ", "%20")'
SV = 'data.SubjectInput.subjectValue'
SUBJECT_PATH = ('"/wql/v1/data?limit=1&query=SELECT%20abbreviation%20FROM%20courseSubjects%20WHERE%20inactive%20%3D%20false'
                f'%20AND%20abbreviation%20%3D%20%27".append({ENC(SV)}).append("%27")')
SUBJECT_ASSERT = (f'(if ({SV}.isEmpty().or({SV}.startsWith("*"))) true else '
                  f'data.LookupSubject.response.asJSON().stringAtJsonPathWithDefault("$.data[0].abbreviation", "").equals({SV}))',
                  f'"Course subject " + {SV} + " is not the abbreviation of an active course subject in Workday"')
PV = 'data.PeriodInput.periodValue'
P_YEAR = f'{PV}.truncate(4)'
P_REST = f'{PV}.replace({PV}.truncate(4), "")'
P_WORDS = (f'(if ({P_REST}.equals("W1")) "Winter%20Term%201" else (if ({P_REST}.equals("W2")) "Winter%20Term%202" else '
           f'(if ({P_REST}.equals("W")) "Winter" else (if ({P_REST}.equals("S")) "Summer" else ""))))')
PERIOD_PATH = ('"/wql/v1/data?limit=1&query=SELECT%20name%20FROM%20academicPeriods%20WHERE%20inactive%20%3D%20false'
               f'%20AND%20name%20startswith%20%27".append({ENC(P_YEAR)}).append("%27")'
               f'.append((if ({P_WORDS}.isEmpty()) "" else "%20AND%20name%20contains%20%27".append({P_WORDS}).append("%27")))')
PERIOD_ASSERT = (f'(if ({PV}.isEmpty().or({PV}.startsWith("*"))) true else '
                 f'data.LookupPeriod.response.asJSON().stringAtJsonPathWithDefault("$.data[0].name", "").isEmpty().not())',
                 f'"No active academic period in Workday matches " + {PV} + " (2024W1 means a 2024-25 Winter Term 1 period)"')
LOOKUP_GUARDS = [  # (kind, input node, value param, path param, lookup node, check node, value, path, assertion, notes)
    ('courseSubject', 'SubjectInput', 'subjectValue', 'subjectPath', 'LookupSubject', 'CheckSubject', SUBJECT_PATH, SUBJECT_ASSERT,
     "Find the active course subject with that Abbreviation (WQL courseSubjects.abbreviation)",
     "Guard: a field whose Workday check is Course subject holds an active subject's Abbreviation (or * for any)"),
    ('academicPeriod', 'PeriodInput', 'periodValue', 'periodPath', 'LookupPeriod', 'CheckPeriod', PERIOD_PATH, PERIOD_ASSERT,
     "Find an active academic period the short form names (WQL academicPeriods.name)",
     "Guard: a field whose Workday check is Academic period names an active period (2024W1, 2024W, 2024S, 2024; * for any)"),
]


# Add Shell Org (product owner 2026-11-05): an X:META organization may be a new application's own
# organization, named exactly as its organization type. Since 2026-11-06 (product owner) that code can be anything
# (X: not required); an organization under an application uses the application as its type. The page checks the same rules.
N = 'data.GetInputParams.organizationName'
T = 'data.GetInputParams.orgType'
ST = 'data.GetInputParams.orgSubtype'
ORG_ASSERTIONS = [
    (f'{T}.isEmpty().not()', '"Organization type is required"'),
    # applications can be named anything (product owner 2026-11-06): the type is the application, any name, no spaces
    (f'{T}.contains(" ").not()', f'"Organization type must not contain spaces, got " + {T}'),
    (f'{N}.equals({T}).or({N}.startsWith({T}.append(":")))', f'"Organization name must be " + {T} + " or start with " + {T} + ":, got " + {N}'),
    (f'(if ({N}.equals({T})) {ST}.equals("X:META") else true)', f'"A new application organization (" + {N} + ") must have subtype X:META"'),
    (f'{N}.contains(" ").not()', f'"Organization name must not contain spaces: " + {N}'),
    # with an application the name starts with its ID once (product owner 2026-11-05): no second X: after it
    (f'(if ({N}.equals({T})) true else {N}.substringAfter({T}.append(":")).startsWith("X:").not())',
     f'"Organization name must start with " + {T} + ": once, got " + {N}'),
]


def main():
    # Add Shell Org: the page picks X:META or X:SHELL; anything else becomes X:META (never free text)
    d = set_subtype(load('IORC_0037_XFD_SEC_Create_Application_Shell_Org'), '{{data.GetInputParams.orgSubtype}}')
    gip = find(d, 'GetInputParams')['_value']['values']['_value']
    if not any(a['_value']['param']['_value']['name']['_value'] == 'orgSubtype' for a in gip):
        proto = next(a for a in gip if a['_value']['param']['_value']['name']['_value'] == 'orgType')
        a = copy.deepcopy(proto)
        a['_value']['param']['_value']['name']['_value'] = 'orgSubtype'
        a['_value']['expr']['_value']['source']['_value'] = (
            '(if (data("start", "queryParams").getParam("orgSubtype", "X:META").equals("X:SHELL")) "X:SHELL" else "X:META")')
        gip.insert(gip.index(proto) + 1, a)
    # CheckOrgName right after GetInputParams (cloned from IORC_0037_XFD_SEC_Create_Pattern_Shell_Org's CheckPatternName)
    nodes = d['_value']['nodes']['_value']
    names = [n['_value']['name']['_value'] for n in nodes]
    proto_node = find(load('IORC_0037_XFD_SEC_Create_Pattern_Shell_Org'), 'CheckPatternName')
    chk = copy.deepcopy(proto_node)
    chk['_value']['name']['_value'] = 'CheckOrgName'
    pa = chk['_value']['assertions']['_value'][0]
    chk['_value']['assertions']['_value'] = []
    for cond, msg in ORG_ASSERTIONS:
        a = copy.deepcopy(pa)
        a['_value']['assertion']['_value']['source']['_value'] = cond
        a['_value']['message']['_value']['source']['_value'] = msg
        chk['_value']['assertions']['_value'].append(a)
    chk['_value']['notes']['_value'][0]['_value']['value']['_value'] = (
        "Guard: the name is the type itself (a new application's X:META organization, any code) or starts with the "
        "type and ':'; no spaces")
    if 'CheckOrgName' in names:
        nodes[names.index('CheckOrgName')] = chk
    else:
        nodes.insert(names.index('GetInputParams') + 1, chk)
    save('IORC_0037_XFD_SEC_Create_Application_Shell_Org', d)

    d = set_subtype(load('IORC_0037_XFD_SEC_Create_Pattern_Shell_Org'), 'X:SHELL')
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
    # academic unit Code check right after CheckPatternName (prototypes: ExtractOrgType, GetApplication, CheckPatternName)
    nodes = d['_value']['nodes']['_value']
    nodes[:] = [n for n in nodes if n['_value']['name']['_value'] not in ('UnitCodeInput', 'LookupUnitCode', 'CheckUnitCode')]
    names = [n['_value']['name']['_value'] for n in nodes]
    cv = copy.deepcopy(find(d, 'ExtractOrgType'))
    cv['_value']['name']['_value'] = 'UnitCodeInput'
    proto_a = cv['_value']['values']['_value'][0]
    cv['_value']['values']['_value'] = []
    for pname, src in (('unitValue', UNIT_VALUE), ('unitPath', UNIT_PATH)):
        a = copy.deepcopy(proto_a)
        a['_value']['param']['_value']['name']['_value'] = pname
        a['_value']['expr']['_value']['source']['_value'] = src
        cv['_value']['values']['_value'].append(a)
    cv['_value']['notes']['_value'][0]['_value']['value']['_value'] = (
        "The value of the field checked against academic unit codes (Maintain Application Pattern: Workday check), and the WQL URL that looks it up")
    lk = copy.deepcopy(find(d, 'GetApplication'))
    lk['_value']['name']['_value'] = 'LookupUnitCode'
    lk['_value']['path']['_value']['source']['_value'] = 'data.UnitCodeInput.unitPath'
    lk['_value']['notes']['_value'][0]['_value']['value']['_value'] = "Find the active academic unit with that Code (WQL academicUnits.academicUnitCode)"
    ck = copy.deepcopy(node)
    ck['_value']['name']['_value'] = 'CheckUnitCode'
    a = copy.deepcopy(proto)
    a['_value']['assertion']['_value']['source']['_value'] = UNIT_ASSERT[0]
    a['_value']['message']['_value']['source']['_value'] = UNIT_ASSERT[1]
    ck['_value']['assertions']['_value'] = [a]
    ck['_value']['notes']['_value'][0]['_value']['value']['_value'] = (
        "Guard: a field whose Workday check is Academic unit code holds the Code of an active academic unit (or * for any)")
    at = names.index('CheckPatternName') + 1
    nodes[at:at] = [cv, lk, ck]
    # course subject and academic period checks after the unit check, built from the same three prototypes
    after = 'CheckUnitCode'
    for kind, inp, vparam, pparam, lname, cname, path, (cond, msg), lnote, cnote in LOOKUP_GUARDS:
        nodes[:] = [n for n in nodes if n['_value']['name']['_value'] not in (inp, lname, cname)]
        c2 = copy.deepcopy(cv)
        c2['_value']['name']['_value'] = inp
        c2['_value']['values']['_value'] = []
        for pname, src in ((vparam, field_value(kind)), (pparam, path)):
            a2 = copy.deepcopy(proto_a)
            a2['_value']['param']['_value']['name']['_value'] = pname
            a2['_value']['expr']['_value']['source']['_value'] = src
            c2['_value']['values']['_value'].append(a2)
        c2['_value']['notes']['_value'][0]['_value']['value']['_value'] = f"The value of the field checked against {kind} (Maintain Application Pattern: Workday check), and the WQL URL that looks it up"
        l2 = copy.deepcopy(lk)
        l2['_value']['name']['_value'] = lname
        l2['_value']['path']['_value']['source']['_value'] = f'data.{inp}.{pparam}'
        l2['_value']['notes']['_value'][0]['_value']['value']['_value'] = lnote
        k2 = copy.deepcopy(ck)
        k2['_value']['name']['_value'] = cname
        a3 = copy.deepcopy(proto)
        a3['_value']['assertion']['_value']['source']['_value'] = cond
        a3['_value']['message']['_value']['source']['_value'] = msg
        k2['_value']['assertions']['_value'] = [a3]
        k2['_value']['notes']['_value'][0]['_value']['value']['_value'] = cnote
        at = [n['_value']['name']['_value'] for n in nodes].index(after) + 1
        nodes[at:at] = [c2, l2, k2]
        after = cname
    save('IORC_0037_XFD_SEC_Create_Pattern_Shell_Org', d)
    print('IORC_0037_XFD_SEC_Create_Application_Shell_Org: subtype from orgSubtype (X:META or X:SHELL); IORC_0037_XFD_SEC_Create_Pattern_Shell_Org: subtype X:SHELL,', len(out), 'assertions')


if __name__ == '__main__':
    main()
