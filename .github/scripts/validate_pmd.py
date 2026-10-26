#!/usr/bin/env python3
"""
validate_pmd.py — Pre-upload validation for ECO-COMS presentation files.

Checks all .pmd and .pod files in presentation/ before they are uploaded
to Workday App Hub. Exits non-zero (blocking upload) if any error is found.

Validations:
  1. JSON syntax — every file must parse cleanly
  2. Protected-key guard — endPoints, outboundData, securityDomains, include
     must NOT appear inside the presentation block
  3. fieldSet integrity — a fieldSet must not carry both 'label' and 'title'
  4. Footer type — a footer block must have type: "footer"
"""

import json
import glob
import sys
import os

PROTECTED_KEYS: set[str] = {"endPoints", "outboundData", "securityDomains", "include"}

SEP = "=" * 62

errors: int = 0


def fail(msg: str) -> None:
    global errors
    print(f"❌  {msg}", flush=True)
    errors += 1


def walk_fieldsets(node: object, filename: str) -> None:
    """Recursively check all fieldSet nodes for structural issues."""
    if not isinstance(node, dict):
        return
    if node.get("type") == "fieldSet":
        if "label" in node and "title" in node:
            fail(f"{filename}: fieldSet '{node.get('id', '?')}' has both 'label' and 'title' — remove one")
    for v in node.values():
        if isinstance(v, list):
            for item in v:
                walk_fieldsets(item, filename)
        elif isinstance(v, dict):
            walk_fieldsets(v, filename)


def validate_file(path: str) -> None:
    filename = os.path.basename(path)

    # 1. JSON syntax
    try:
        data: dict = json.load(open(path, encoding="utf-8"))
    except json.JSONDecodeError as exc:
        fail(f"{filename}: JSON parse error at line {exc.lineno} col {exc.colno}: {exc.msg}")
        return  # can't check further without a parsed doc

    presentation: dict = data.get("presentation", {})

    if not presentation:
        # Files like home.pmd / errorPage.pmd have minimal presentation blocks — warn only
        print(f"⚠️  {filename}: no 'presentation' block found (skipping structure checks)")
        return

    # 2. Protected keys must not appear inside the presentation block
    for key in PROTECTED_KEYS:
        if key in presentation:
            fail(f"{filename}: protected key '{key}' found inside 'presentation' block — move it to root level")

    # 3. fieldSet integrity
    walk_fieldsets(presentation, filename)

    # 4. Footer type guard
    footer: dict = presentation.get("footer", {})
    if footer and footer.get("type") != "footer":
        fail(f"{filename}: 'footer' block is missing type:\"footer\" (got type={footer.get('type')!r})")

    print(f"✅  {filename}: valid")


# ── Main ──────────────────────────────────────────────────────────────────────

print(SEP)
print("ECO-COMS presentation file validator")
print(SEP)

files = sorted(glob.glob("presentation/*.pmd") + glob.glob("presentation/*.pod"))

if not files:
    print("⚠️  No .pmd or .pod files found in presentation/ — nothing to validate")
    sys.exit(0)

for path in files:
    validate_file(path)

print()
if errors > 0:
    print(SEP)
    print(f"❌  VALIDATION FAILED — {errors} ERROR(S) FOUND")
    print(SEP)
    print("   Upload to App Hub has been BLOCKED.")
    print("   Fix all errors listed above, then re-run the workflow.")
    print(SEP)
    sys.exit(1)

print(SEP)
print(f"✅  ALL {len(files)} PRESENTATION FILES VALIDATED SUCCESSFULLY")
print(SEP)
