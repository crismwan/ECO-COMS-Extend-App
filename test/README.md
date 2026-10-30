# ECO-COMS tests

Three layers run on every push to `main` (`.github/workflows/deploy.yml`). Flows that need a human approver are in the manual checklist below.

| Layer | Script | When | Blocks? | Tenant changes |
|---|---|---|---|---|
| Presentation shape | `.github/scripts/validate_pmd.py` | before upload | yes | none |
| Static checks | `test/static_checks.py` | before upload | yes | none |
| Smoke e2e | `node test/e2e.js` | after deploy, every push | marks the run failed | none (read-only) |
| Full e2e | `node test/e2e.js --suite full` | manual run only (Actions → Deploy → Run workflow → e2e_suite = full) | marks the run failed | creates one `X:ADM:TEST:CI:<yyMMddHHmm>` shell org, inactivates it 45 days out, writes 2 audit records |

Run locally: `python3 test/static_checks.py` and `node test/e2e.js [--suite full] [--verbose]` (uses `WD_DEV_TOKEN` or your wdcli login).

## What the static checks catch

All are pitfalls that broke this app before (see CLAUDE.md):

- JSON that won't parse (pages, AMD, SMD, cards, pods, business objects, orchestrations, WQL)
- `pageType` not exactly `EDIT` / `VIEW`
- App Builder `_underscore` attributes left in a page
- `standardEditButtonsHidden` without an `editButtonBar` (no way to submit)
- invalid widget types (`checkbox`, `dropDown`, `select`)
- a button with both `parameters` and `parameterBindings`
- `taskId` references (buttons, hubs, wizards, `cancelOverride`, flows) that aren't AMD tasks; AMD tasks pointing at missing pages
- orchestration launches whose `orchestration/<Name>.orchestration` doesn't exist
- business-process `pageRoute`s with no matching AMD `routingPattern`
- cards with declared-but-unused parameters or single-quoted literals in `<% %>` (both fail upload)
- forbidden test text in anything shipped to the tenant
- files over 100 KB, more than 75 pages
- warning only: inbound endpoints without `failOnStatusCodes`

Known issues are listed in `KNOWN_ISSUES` at the top of the script. They are reported as warnings, each with a reason. Remove an entry once it's fixed.

## Coverage by flow

| Flow | Static | Smoke (every deploy) | Full (manual run) | Manual checklist |
|---|---|---|---|---|
| Add shell org (wizard → AddShellOrg) | launch target exists | `allShellOrgs`, `customOrganizations` WQL run; shell orgs exist | add, verify by WQL, audit `Shell Org / ADD` | wizard UI and success page |
| Add shell org pattern (AddShellOrgPattern) | launch target exists | `existingPatterns` WQL runs | not automated: each run would leave a permanent pattern org | yes |
| Inactivate / reactivate org (ManageShellOrgStatus) | launch target exists | none | inactivate, audit `Org Status / INACTIVATE` | reactivate |
| Role position assign / remove (AssignRolePositions) | launch target exists | `allShellAssignableRolesinTenant`, `allPositions` WQL run | not automated: needs a dedicated test role and position | yes |
| Assignable role / AAA request (+ StartRoleRequestReview) | launch target exists | requests readable | not automated: would leave open review events each run | yes |
| ISC review BP: approve path | BP routes match AMD tasks | BP-approved requests have a security group; pending requests have an open event | none | yes (needs approver) |
| ISC review BP: deny / cancel (DenyRoleRequest) | none | every Denied request is inactive | none | yes (needs approver) |
| Audit log viewer | page shape | audit readable; fixed vocabulary; required fields | every write is checked through its audit record | none |
| BO data access | none | all 5 collections readable | none | none |
| Completion notification, step help text | none | none | none | yes |

## Manual checklist (before each phase sign-off)

Use neutral test values (`TEST:ORG:<n>`, `TESTROLE<n>`). Proxy as the approver where noted.

1. **Create Shell Organization** wizard: create `X:ADM:TEST:ORG:<n>`. Success page shows; Shell Org Manager count goes up by 1; audit `Shell Org / ADD`.
2. **Add Shell Org Pattern** wizard: create a TEST pattern. Success page shows; audit `Shell Org Pattern / ADD`.
3. **Manage status**: inactivate the step-1 org, then reactivate it. Audit `INACTIVATE` and `REACTIVATE`.
4. **Manage Role Assignments**: add one position to a test role, then remove it. Audit `ASSIGN POSITION` and `REMOVE POSITION`.
5. **Assignable Role Manager**: submit `X:ADM:ROLE:TESTROLE<n>`. It appears in Pending ISC Requests with a Review Process link; the approval step lists the approver group's members.
6. **Deny**: as the approver, deny it. Within a minute it's Denied, gone from Pending, audit `DENY`.
7. **Approve**: submit another, approve as the approver, complete To Dos 3 and 4 as HR Administrator, finish step 5. Request is Approved, audit `APPROVE`, requester gets the "ECO-COMS role request completed" notification.
8. Check each step's help text reads correctly in the inbox.
