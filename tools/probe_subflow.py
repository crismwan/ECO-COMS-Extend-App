#!/usr/bin/env python3
"""Probe (2026-11-04): does a hand-written sub-orchestration call build and run? Writes two throwaway orchestrations:
  ProbeEcho          .maya.FlowSubflow, input `text`, export `echo` (shape from Orchestration Builder's own source view)
  ProbeSubflowCall   sync, calls ProbeEcho via a CallSubflow step and returns {"echo": ...}
Unknowns being tested: CallSubflow.subflowId = the sub-orchestration's name; inputs read as data.start.<name>;
outputs read as data.<callStep>.<export>. Delete both files (and this script) once the answer is in CLAUDE.md.
Not part of rebuild_all."""
import json, os, copy
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'orchestration')
S = lambda v: {"_type": "String", "_value": v}
I = lambda v: {"_type": "Identifier", "_value": v}
B = lambda v: {"_type": "Boolean", "_value": v}
EXPR = lambda src, t="String": {"_type": ["Expr", t], "_value": {"type": {"_type": "Type", "_value": t}, "source": S(src), "isAuto": B(False)}}
NOTES = lambda text: {"_type": ["List", "Note"], "_value": [{"_type": "Note", "_value": {"key": S("description"), "value": S(text)}}]}
PARAM = lambda name, t="String": {"_type": "Parameter", "_value": {"name": I(name), "type": {"_type": "Type", "_value": t}, "default": {"_type": ["Opt", "Any"], "_value": None}}}
ASSIGN = lambda name, src: {"_type": "Assignment", "_value": {"param": PARAM(name), "expr": EXPR(src)}}

base = json.load(open(os.path.join(ROOT, 'IscQueueCardData.orchestration')))
resources = base['_value']['resources']
locale = base['_value']['defaultLocale']

sub = {"flowVersion": "3.7.0", "_type": "Flow", "_value": {
  "id": S("5ab7e0c2d3f14a6b9c8e7f6a5b4c3d21"), "name": I("ProbeEcho"), "type": {"_type": "FlowType", "_value": ".maya.FlowSubflow"},
  "start": {"_type": "StartSubflow", "_value": {
    "parameters": {"_type": ["List", "ExprParameter"], "_value": [{"_type": "ExprParameter", "_value": {
      "name": I("text"), "type": {"_type": "Type", "_value": "String"}, "expr": {"_type": ["Opt", ["Expr", ["Opt", "Any"]]], "_value": None}}}]},
    "notes": NOTES("text: any string")}},
  "end": {"_type": "EndSubflow", "_value": {
    "exports": {"_type": ["List", "Assignment"], "_value": [ASSIGN("echo", '"echo:".append(data.start.text)')]},
    "notes": NOTES("echo: echo:<text>")}},
  "nodes": {"_type": ["List", "Node"], "_value": []},
  "notes": NOTES("Throwaway probe for sub-orchestration calls (tools/probe_subflow.py)."),
  "resources": copy.deepcopy(resources),
  "defaultWorkdayCredentialRef": {"_type": ["Opt", "AccessTokenFromInitiatingUser"], "_value": {"_type": "AccessTokenFromInitiatingUser", "_value": "AccessTokenFromInitiatingUser"}},
  "defaultTlsConfigRef": {"_type": ["Opt", "TlsConfigRefOrDefault"], "_value": None},
  "defaultFtpCredRef": {"_type": ["Opt", "FtpCredentialRef"], "_value": None},
  "mayaVersion": base['_value']['mayaVersion'], "errorHandler": {"_type": ["Opt", "ErrorHandler"], "_value": None},
  "cancelBarrier": {"_type": ["Opt", "Identifier"], "_value": None}, "defaultLocale": copy.deepcopy(locale),
  "securityDomains": {"_type": ["Opt", ["List", "String"]], "_value": None}}}

parent = copy.deepcopy(base)
pv = parent['_value']
pv['id'] = S("6bc8f1d3e4a25b7cad9f8a7b6c5d4e32")
pv['name'] = I("ProbeSubflowCall")
card = next(n for n in pv['nodes']['_value'] if n['_value']['name']['_value'] == 'Card')
card['_value']['message']['_value'] = '{"echo": "{{data.CallEcho.echo}}"}'
call = {"_type": "CallSubflow", "_value": {
  "name": I("CallEcho"), "isDisabled": B(False), "errorHandler": {"_type": ["Opt", "ErrorHandler"], "_value": None},
  "subflowId": S("ProbeEcho"),
  "parameters": {"_type": ["List", "Assignment"], "_value": [ASSIGN("text", '"hello"')]},
  "executionDelay": {"_type": ["Opt", "SubflowExecutionDelay"], "_value": None}}}
pv['nodes']['_value'] = [call, card]
pv['notes'] = NOTES("Throwaway probe: calls ProbeEcho and returns its output (tools/probe_subflow.py).")
for name, d in (('ProbeEcho', sub), ('ProbeSubflowCall', parent)):
    ext = '.suborchestration' if name == 'ProbeEcho' else '.orchestration'   # App Hub's own extension for a FlowSubflow
    open(os.path.join(ROOT, name + ext), 'w').write(json.dumps(d, separators=(',', ':')))
print('wrote ProbeEcho, ProbeSubflowCall')
