#!/usr/bin/env bash
# Rebuilds every generated page, card and orchestration from the tools/ scripts, in the order they
# were first applied, then runs the repo-wide passes. Every step is idempotent, so on a clean checkout
# this must leave `git status` unchanged; `--check` fails if it doesn't (a hand edit that a builder
# would overwrite, or a builder that drifted from the committed files).
#
#   tools/rebuild_all.sh           rebuild
#   tools/rebuild_all.sh --check   rebuild, then fail if anything changed (and show what)
set -euo pipefail
cd "$(dirname "$0")/.."

if [[ "${1:-}" == "--check" ]] && [[ -n "$(git status --porcelain -- presentation orchestration model)" ]]; then
  echo "rebuild_all --check: commit or stash your changes under presentation/, orchestration/, model/ first" >&2
  exit 2
fi

run() { echo "== $*"; python3 "$@" | sed 's/^/   /'; }

run tools/build_bulk_orchestration.py   # orchestration/BulkRoleApply.orchestration
run tools/build_bulk_pages.py           # bulk template / upload / results / apply pages (+ empty messages)
run tools/build_bulk_grid.py            # Bulk Edit Role Assignments (in-app grid)
run tools/build_org_detail.py           # shellOrgDetail + Details buttons in Shell Org Manager
run tools/build_request_lists.py        # My Assignable Role Requests, AAA Role Requests
run tools/build_filter_pills.py         # pill filters, Home action cards, SOM summary, error page
run tools/build_schema_pattern.py      # Add Shell Org Pattern for any application (schema-driven)
run tools/patch_pattern_orchestrations.py  # pattern guards + org subtypes in the create orchestrations
run tools/title_case.py                 # headings and card titles in Title Case
run tools/consistency.py                # titles, back links, help text size, success pages
run tools/add_empty_messages.py         # "Nothing to show" texts
run tools/polish.py                     # final pass: labels, About boxes, names, Pacific times

if [[ "${1:-}" == "--check" ]]; then
  changed="$(git status --porcelain -- presentation orchestration model)"
  if [[ -n "$changed" ]]; then
    echo "rebuild_all --check: the builders don't reproduce the committed files:" >&2
    echo "$changed" >&2
    git --no-pager diff --stat -- presentation orchestration model >&2
    exit 1
  fi
  echo "rebuild_all --check: OK, the builders reproduce the committed files exactly"
fi
