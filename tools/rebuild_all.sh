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

run tools/subtype_apps.py --restore      # pages as the later steps left them; first, before the other restores (the subtype rewrite runs again near the end)
run tools/title_banner.py --restore    # put Workday titles back so every builder sees ordinary pages
run tools/merge_nav_about.py --restore  # back links in their own navSection again
run tools/extract_subflows.py --restore # full orchestrations back, so the patch steps find their steps (re-extracted last)
run tools/build_bulk_orchestration.py   # orchestration/IORC_0037_XFD_SEC_Bulk_Role_Changes_From_CSV.orchestration
run tools/build_bulk_pages.py           # bulk template / upload / results / apply pages (+ empty messages)
run tools/build_bulk_grid.py            # Bulk Edit Role Assignments (in-app grid)
run tools/build_org_detail.py           # shellOrgDetail + Details buttons in Shell Org Manager
run tools/build_request_lists.py        # My Assignable Role Requests, AAA Role Requests
run tools/build_filter_pills.py         # pill filters, Home action cards, SOM summary, error page
run tools/build_schema_pattern.py      # Add Shell Org Pattern for any application (schema-driven)
run tools/new_shell_org_meta.py        # Add Shell Org: X:META without an application (a new application, code X:NEWAPP)
run tools/build_insights.py             # Insights page across the business objects + lean reports
run tools/build_access_review.py        # Access Review page + hub card (role assignments still needed?)
run tools/build_app_patterns.py         # Application Patterns setup: list + edit page for each application's pattern format
run tools/build_activity_chart.py      # App Activity chart (7 days by area) on the RBAC Hub
run tools/build_pending_age.py         # Pending Requests by Age chart on the RBAC Hub
run tools/build_home_cards.py           # Home card data orchestrations (Workday Home Card wrap once the template exists)
run tools/patch_pattern_orchestrations.py  # pattern guards + org subtypes in the create orchestrations
run tools/title_case.py                 # headings and card titles in Title Case
run tools/consistency.py                # titles, back links, help text size, success pages
run tools/add_empty_messages.py         # "Nothing to show" texts
run tools/polish.py                     # final pass: labels, About boxes, names, Pacific times
run tools/ux_improvements.py          # UI recommendations 2026-11-02: help text, Waiting column, counters, links
run tools/grid_style.py                # one grid format: list look, sortable columns, no +/- on display grids
run tools/ui_tweaks.py                 # ISC Queue: one Role column
run tools/enabled_for_choice.py        # request pages: Enabled For type first, then only that picker (--off to roll back)
run tools/pos_search_limit.py          # position searches: first 50 matches (--off to roll back)
run tools/pos_tree.py                  # position picker: browse by supervisory organization too (pilot, --off to roll back)
run tools/unit_tree.py                 # FUH / Academic Unit pickers: browse by type too (--off to roll back)
run tools/aaa_full_app_id.py           # AAA Role Request: full application ID in the role name (--off to roll back)
run tools/clear_on_change.py           # a field OK flagged clears its error when changed (edited pages)
run tools/collapse_about.py            # About boxes start closed on the long pages
run tools/merge_nav_about.py           # back links at the top of the About box
run tools/title_banner.py              # white title tile instead of Workday's square page banner

run tools/ux_improvements.py --tiles  # one-line summary under the title tile where the About box starts closed
run tools/request_audit.py          # REQUEST audit records written by the review orchestrations (with event + run ID)
run tools/audit_run_id.py           # audit records carry the orchestration run ID (field runId)
run tools/audit_event_ref.py        # audit records carry their Workday event (field eventWid)
run tools/graphql_audit.py          # audit records through the Graph API (newest first, sorted on the server)
run tools/audit_speed.py            # Audit Log: no lookup lists, empty Graph pages skipped
run tools/som_speed.py              # Shell Org Manager: one organization list, not two
run tools/som_pill_cards.py         # Shell Org Manager: the Application bar's pill cards (--off)
run tools/som_app_bar.py            # Shell Org Manager: Application bar, every application as pills (--off)
run tools/arm_speed.py              # Assignable Role Manager: unused position lists dropped
run tools/audit_filters_more.py      # Audit Log Changed By + Organization filters, Shell Org Detail link
run tools/app_pattern_audit.py       # Audit Log: Application Pattern rows link to their application record
run tools/excel_export_values.py     # fieldSet columns get an Excel export value (else the export fails)
run tools/clear_submit_errors.py      # every OK check clears its own earlier errors first
run tools/subtype_apps.py             # organizations by subtype, applications by organization type
run tools/apply_icons.py              # every icon from one table (CLAUDE.md "Icons" framework)
run tools/extract_subflows.py         # shared logic moved into sub-orchestrations (runs last, after every patch)

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
