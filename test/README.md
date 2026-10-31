# ECO-COMS tests

Everything runs from one file, `test/run-tests.js`, which has five suites:

| Suite | Command | When it runs | Blocks? | Tenant changes |
|---|---|---|---|---|
| static | `node test/run-tests.js static` | every push, first step of the deploy (before any login) | yes: nothing is uploaded | none (no tenant access) |
| smoke | `node test/run-tests.js smoke` | after every deploy | marks the run failed | none (read-only) |
| full | `node test/run-tests.js full` | by hand: Actions → Tests → task = full (or Deploy → e2e_suite = full) | marks the run failed | writes TEST data, listed below |
| cleanup | `node test/run-tests.js cleanup [--apply]` | by hand: Actions → Tests → cleanup-dry-run, then cleanup-apply | n/a | removes TEST data |
| isu | `node test/run-tests.js isu` | by hand, and only once ISU writes are live | marks the run failed | none if it passes; anything a probe manages to write is deleted again |

Suites combine with commas (`static,smoke`). **The isu suite never runs unless you name it**, so it can't fire before the ISU setup is done. Flows that need a human approver are in the manual checklist at the end.

Run locally with your wdcli login or `WD_DEV_TOKEN`: `node test/run-tests.js smoke --verbose`. Results go to `test/results.json` and, in GitHub, the run's Summary page.

### Why not run everything on every deploy

- **static** and **smoke** are free and change nothing, so they run every time.
- **full** creates orgs and patterns that can't be deleted (only inactivated), adds and removes a position on a real role, leaves BP events that are permanent history, and takes about 15 minutes. Run it before a sign-off or after a risky change, not on every push. A nightly scheduled run is the next step up if you want it.
- **isu** checks the lockdown (users can't write audit records or requests directly). Before the ISU branch is merged and the user groups are cut back to view-only, it is expected to fail, which is why it is opt-in.

### What full writes per run

One `X:ADM:TEST:CI:RUN<n>` shell org and one `X:CLW:PATTERN:TEST:TEST:<nnn>:900:<yyyy>W1` pattern (both left inactive 45 days out); adds and removes one position on `X:BPMS(ODMT):ROLE:ADVISORS` (net no change); one Denied `X:ADM:ROLE:TESTROLECIRUN<n>` request (can't be deleted: linked to its review event); two pending ISC requests left open for review (`<shell org>:ROLE:TESTROLE` and `<pattern>:ROLE:TESTROLE`; cleanup cancels them); about 9 audit records (removed by cleanup).

## What the static suite catches

All are pitfalls that broke this app before (see CLAUDE.md):

- JSON that won't parse (pages, AMD, SMD, cards, pods, business objects, orchestrations, WQL)
- `endPoints`, `outboundData`, `securityDomains` or `include` inside the `presentation` block; a footer without `type: "footer"`
- `pageType` not exactly `EDIT` / `VIEW`
- App Builder `_underscore` attributes left in a page
- `standardEditButtonsHidden` without an `editButtonBar` (no way to submit)
- invalid widget types (`checkbox`, `dropDown`, `select`); a fieldSet with both `label` and `title`
- a button with both `parameters` and `parameterBindings`; a bare `errorCode` instead of `queryParams.errorCode`
- `taskId` references (buttons, hubs, wizards, `cancelOverride`, flows) that aren't AMD tasks; AMD tasks pointing at missing pages
- orchestration launches whose `orchestration/<Name>.orchestration` doesn't exist
- business-process `pageRoute`s with no matching AMD `routingPattern`
- cards with declared-but-unused parameters or single-quoted literals in `<% %>` (both fail upload)
- forbidden test text in anything shipped to the tenant
- files over 100 KB, more than 75 pages
- warning only: inbound endpoints without `failOnStatusCodes`

Known issues are listed in `KNOWN_ISSUES` near the top of the static section. They are reported as warnings, each with a reason. Remove an entry once it's fixed.

## What the isu suite checks

- every page write to `comsAuditLogs` / `comsAssignableRoles` uses `authType: "isuAuth"`, and the SMD defines `isuAuth`
- as the signed-in user: creating an audit record, creating a request and editing a request are all refused (401/403)
- Deleting isn't probed, because a probe that succeeded would destroy data. Orchestration writes through the ISU credential are covered by the full suite's audit checks.

## Coverage by flow

| Flow | Static | Smoke (every deploy) | Full (manual run) | Manual checklist |
|---|---|---|---|---|
| Add shell org (wizard → AddShellOrg) | launch target exists | `allShellOrgs`, `customOrganizations` WQL run; shell orgs exist | add, verify by WQL, audit `Shell Org / ADD` | wizard UI and success page |
| Add shell org pattern (AddShellOrgPattern) | launch target exists | `existingPatterns` WQL runs | add, verify by WQL, audit `Shell Org Pattern / ADD`, inactivate | wizard UI |
| Inactivate / reactivate org (ManageShellOrgStatus) | launch target exists | none | inactivate today, reactivate, inactivate 45 days out (each audited); guard rejects a mismatched action and a non-shell org | page UI |
| Role position assign / remove (AssignRolePositions) | launch target exists | WQL runs; every role assignment audit shows the full position name | add an unassigned position to the test role, confirm it's on the assignment, remove it; both audits show the same full position name | page UI |
| Assignable role / AAA request (+ StartRoleRequestReview) | launch target exists | requests readable | create request, start review, confirm an open event; leave two pending requests (one on the run's shell org, one on its pattern) with REQUEST audits | page UI |
| ISC review BP: approve path | BP routes match AMD tasks | BP-approved requests have a security group; pending requests have an open event | none | yes (needs approver) |
| ISC review BP: deny / cancel (DenyRoleRequest) | none | every Denied request is inactive; every closed request matches its review event | cancel the review event → request Denied, inactive, DENY audit | approver Deny |
| Audit log viewer | page shape | audit readable; fixed vocabulary; required fields | every write is checked through its audit record | none |
| BO data access | none | all 5 collections readable | none | none |
| Completion notification, step help text | none | none | none | yes |

Cleanup: Actions → E2E tests → task = cleanup-dry-run, then cleanup-apply. It cancels the reviews of pending test requests and waits for them to turn Denied. Orgs that already have a scheduled inactivation are reported as failed (Workday allows only one); they still go inactive on that date.

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
