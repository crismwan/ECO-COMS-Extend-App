#!/usr/bin/env python3
"""
static_checks.py - repo-level checks that run before every upload (no tenant access).

Each check encodes a platform pitfall that has broken this app before (see CLAUDE.md).
Exits non-zero on any ERROR, which blocks the upload. WARN lines never block.

Run locally:  python3 test/static_checks.py
"""

import glob
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)

AMD_PATH = "presentation/ecocomsphase_xclw_cm_sync2_vmzvxm.amd"
MAX_FILE_BYTES = 100 * 1024          # platform limit for .pmd/.amd/.smd/.pod/.script
MAX_PAGES = 75                       # platform limit for pages per app
UNDERSCORE_ATTRS_ALLOWED = set()     # App Builder metadata like _layout must not ship

# Known issues: reported as WARN instead of ERROR until fixed. Each needs a reason.
# Remove an entry as soon as the issue is fixed so the check protects it again.
KNOWN_ISSUES = {
    ("submitButton", "deleteAssignableRole.pmd"):
        "no way to submit; decide delete vs cancelling the ISC review BP before re-enabling",
    ("submitButton", "newShellOrgConfirm.pmd"):
        "page no longer used by createShellOrgWizard; candidate for removal",
    ("submitButton", "newShellOrgPatternConfirm.pmd"):
        "page no longer used by createShellOrgPatternWizard; candidate for removal",
}

errors, warnings = [], []


def err(check, msg, file=None):
    reason = KNOWN_ISSUES.get((check, file))
    if reason:
        warnings.append(f"[{check}] KNOWN ISSUE {msg} ({reason})")
    else:
        errors.append(f"[{check}] {msg}")


def warn(check, msg):
    warnings.append(f"[{check}] {msg}")


def load_json(path):
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except json.JSONDecodeError as exc:
        err("json", f"{path}: JSON parse error line {exc.lineno} col {exc.colno}: {exc.msg}")
    except OSError as exc:
        err("json", f"{path}: {exc}")
    return None


def walk(node, fn, parent_key=None):
    """Call fn(dict_node, parent_key) for every dict in a JSON tree."""
    if isinstance(node, dict):
        fn(node, parent_key)
        for k, v in node.items():
            walk(v, fn, k)
    elif isinstance(node, list):
        for v in node:
            walk(v, fn, parent_key)


# ── 1. Every JSON component parses ────────────────────────────────────────────
json_globs = ["presentation/*.pmd", "presentation/*.amd", "presentation/*.smd",
              "presentation/pods/*.pod", "presentation/*.pod", "presentation/*.card",
              "presentation/cards/*.card", "model/*", "orchestration/*.orchestration",
              "**/*.wqlquery"]
docs = {}
for g in json_globs:
    for p in glob.glob(g, recursive=True):
        if os.path.isfile(p) and p not in docs:
            d = load_json(p)
            if d is not None:
                docs[p] = d

pmds = {p: d for p, d in docs.items() if p.endswith(".pmd")}
cards = {p: d for p, d in docs.items() if p.endswith(".card")}
amd = docs.get(AMD_PATH)
if amd is None:
    err("amd", f"{AMD_PATH} missing or unreadable")
    amd = {}

# ── 2. Size and count limits ──────────────────────────────────────────────────
for p in glob.glob("presentation/**/*", recursive=True):
    if p.endswith((".pmd", ".amd", ".smd", ".pod", ".script")) and os.path.getsize(p) > MAX_FILE_BYTES:
        err("size", f"{p}: {os.path.getsize(p)} bytes exceeds the 100 KB file limit")
if len(pmds) > MAX_PAGES:
    err("size", f"{len(pmds)} pages exceeds the 75-page app limit")

# ── 3. PMD page rules ─────────────────────────────────────────────────────────
for path, d in pmds.items():
    name = os.path.basename(path)
    pres = d.get("presentation", {}) or {}

    page_type = pres.get("pageType", d.get("pageType"))
    if page_type is not None and page_type not in ("EDIT", "VIEW"):
        err("pageType", f"{name}: pageType {page_type!r} must be \"EDIT\" or \"VIEW\" (uppercase)")

    if pres.get("standardEditButtonsHidden") in (True, "true") and "editButtonBar" not in pres:
        err("submitButton", f"{name}: standardEditButtonsHidden without editButtonBar leaves no way to submit", name)

    def check_node(node, _pk, name=name):
        for k in node:
            if k.startswith("_") and k not in UNDERSCORE_ATTRS_ALLOWED:
                err("underscoreAttr", f"{name}: App Builder attribute {k!r} on {node.get('id', node.get('type', '?'))} is not valid PMD")
        if node.get("type") in ("checkbox", "dropDown", "select"):
            err("widgetType", f"{name}: widget type {node['type']!r} is invalid (use checkBox / dropdown)")
        tr = node.get("taskReference")
        if isinstance(tr, dict) and "parameters" in tr and "parameterBindings" in tr:
            err("taskReference", f"{name}: {node.get('id', '?')} has both parameters and parameterBindings (parameters are dropped)")
    walk(d, check_node)

    # queryParams: bare names in visible/value scripts are a classic "1 Error"; only flag known param names
    raw = json.dumps(d)
    for bare in ("errorCode",):
        if re.search(r"<%[^%]*(?<![\w.])" + bare + r"\b", raw):
            err("queryParams", f"{name}: bare '{bare}' in a script; use queryParams.{bare}")

# ── 4. Task references resolve ────────────────────────────────────────────────
tasks = {t.get("id"): t for t in amd.get("tasks", []) if isinstance(t, dict)}
page_ids = {d.get("id") for d in pmds.values()}
for tid, t in tasks.items():
    pid = (t.get("page") or {}).get("id")
    if pid and pid not in page_ids:
        err("amdTask", f"AMD task {tid!r} points at page {pid!r}, which has no .pmd file")

referenced = []


def collect_task_ids(node, pk, src):
    if pk in ("taskReference", "initialTask", "task", "cancelOverride", "conclusion") and isinstance(node.get("taskId"), str):
        referenced.append((src, node["taskId"]))
    if "flowSteps" in node:
        for s in node["flowSteps"]:
            if isinstance(s, dict) and isinstance(s.get("taskId"), str):
                referenced.append((src, s["taskId"]))


for path, d in list(pmds.items()) + list(cards.items()) + [(AMD_PATH, amd)]:
    walk(d, lambda n, pk, src=os.path.basename(path): collect_task_ids(n, pk, src))
for src, tid in referenced:
    if "<%" in tid:
        continue
    if tid not in tasks:
        err("taskRef", f"{src}: references taskId {tid!r}, which is not in the AMD tasks list")

# ── 5. Orchestration launches point at real orchestrations ────────────────────
orch_names = {os.path.splitext(os.path.basename(p))[0] for p in glob.glob("orchestration/*.orchestration")}
for path, d in pmds.items():
    for m in re.finditer(r"/([A-Za-z0-9_]+)/launch", json.dumps(d)):
        if m.group(1) not in orch_names:
            err("orchestration", f"{os.path.basename(path)}: launches {m.group(1)!r}, but orchestration/{m.group(1)}.orchestration does not exist")

# ── 6. Business process routes have matching AMD tasks ────────────────────────
routes = {t.get("routingPattern") for t in tasks.values()}
for p in glob.glob("model/*.businessprocess"):
    bp = docs.get(p) or {}
    found = []
    walk(bp, lambda n, pk: found.append(n["pageRoute"]) if isinstance(n.get("pageRoute"), str) else None)
    for r in found:
        if r not in routes:
            err("bpRoute", f"{os.path.basename(p)}: pageRoute {r!r} has no AMD task with that routingPattern")

# ── 7. Card rules ─────────────────────────────────────────────────────────────
for path, d in cards.items():
    name = os.path.basename(path)
    body = json.dumps({k: v for k, v in d.items() if k not in ("id", "parameters")})
    for prm in d.get("parameters", []) or []:
        if not re.search(r"\b" + re.escape(prm) + r"\b", body):
            err("cardParams", f"{name}: parameter {prm!r} is declared but never used (fails upload)")
    for script in re.findall(r"<%(.*?)%>", body):
        if "'" in script:
            err("cardQuotes", f"{name}: single-quoted literal inside <% %> fails tokenization; pass it in as a parameter")

# ── 8. No forbidden test text in anything shipped to the tenant ───────────────
for g in ("presentation/**/*", "model/*", "orchestration/*"):
    for p in glob.glob(g, recursive=True):
        if os.path.isfile(p):
            try:
                if re.search(r"claude", open(p, encoding="utf-8", errors="ignore").read(), re.I):
                    err("testText", f"{p}: contains forbidden test text (see CLAUDE.md 'Test data in the tenant')")
            except OSError:
                pass

# ── 9. Inbound endpoints should fail loudly (warning only) ────────────────────
for path, d in pmds.items():
    def check_ep(node, pk, name=os.path.basename(path)):
        if pk == "endPoints" and "baseUrlType" in node and "failOnStatusCodes" not in node and not node.get("deferred"):
            warn("failOnStatusCodes", f"{name}: endpoint {node.get('name')!r} has no failOnStatusCodes (errors are swallowed)")
    walk(d, check_ep)

# ── Report ────────────────────────────────────────────────────────────────────
print("=" * 62)
print("ECO-COMS static checks")
print("=" * 62)
print(f"Checked {len(docs)} JSON components, {len(pmds)} pages, {len(tasks)} AMD tasks, "
      f"{len(orch_names)} orchestrations, {len(cards)} cards")
for w in warnings:
    print(f"WARN  {w}")
for e in errors:
    print(f"ERROR {e}")
print("-" * 62)
print(f"{len(errors)} error(s), {len(warnings)} warning(s)")
sys.exit(1 if errors else 0)
