# ECO-COMS admin runbook

For the developer or admin of the ECO-COMS Extend app (`ecocomsphase_xclw_cm_sync2_vmzvxm`, dev tenant `ubc_wcpdev2`, repo `crismwan/ECO-COMS-Extend-App`). Background and history: `docs/ECO-COMS-NOTES.md` and `CLAUDE.md`. Test details: `test/README.md`.

Changes to security policies, permission grants and tenant setup are made by a person, not by an automated agent.

---

## 1. Deploy pipeline

`.github/workflows/deploy.yml` ("Deploy to Workday Extend") runs on every push to `main`. You can also start it by hand with `e2e_suite` = `smoke` (the default) or `full`. Its steps, in order:

1. **Static checks** (`node test/run-tests.js static`). These run before any login, so a code error is reported even when the tokens have expired. A failure here blocks the upload.
2. Install WDCLI.
3. **Pre-populate wdcli config with developer token** (`WD_DEV_TOKEN`). This step also checks the token's expiry.
4. **Check platform token (WD_WCP_TOKEN) expiry**
5. **Authenticate as system user (for upload)**
6. **Upload app to App Hub**
7. Restore tenant token, patch wdcli
8. **Deploy to ubc_wcpdev2 via wdcli**
9. **Post-deploy e2e tests**: waits 30 s, then runs the smoke suite (or full)

A healthy run takes about 1–3 minutes (baseline about 1m15s).

After every push:

```
gh run list --limit 5
gh api repos/crismwan/ECO-COMS-Extend-App/actions/runs/<run-id>/jobs
```

Don't call anything deployed until the job shows `conclusion: success`. If the upload fails, read the App Hub build errors in the browser: run page → Summary → "Upload Failure". `gh run view --log` is blocked from the cloud container.

### Which token is the problem

| Symptom | Cause | Fix |
|---|---|---|
| Fails in under 20 s at **Pre-populate wdcli config with developer token**: "WARNING: WD_DEV_TOKEN EXPIRED ..." | `WD_DEV_TOKEN` expired (it lasts about 8 h) | Refresh `WD_DEV_TOKEN` |
| Fails at **Check platform token (WD_WCP_TOKEN) expiry**: "ERROR: WD_WCP_TOKEN expired ..." | `WD_WCP_TOKEN` expired | Refresh `WD_WCP_TOKEN` |
| Both checks pass, then **Deploy to ubc_wcpdev2 via wdcli** fails with `[CI-401] UNAUTHORIZED URL: https://api.us.wcp.workday.com/aos/v1/deploy`, "The supplied authentication is invalid" | Session revoked or invalidated (not a plain expiry) | Refresh **both** tokens |
| Deploy fails with "Cannot read properties of undefined (reading 'success')" | A token expired during the deploy | Refresh both, then rerun straight away |
| **Authenticate as system user (for upload)** fails in about 20 s | Usually transient | Rerun once |
| Run stuck at "in_progress", every step completed, job conclusion success | It deployed. It can't be cancelled or rerun | Nothing to do |

A token failure is never a code problem. Don't revert or change code because of one.

### Refresh the tokens

This needs a browser login, so a person has to do it.

1. On a machine with `wdcli` installed, run:
   ```
   wdcli app deploy ecocomsphase_xclw_cm_sync2_vmzvxm
   ```
2. Complete the browser login for `ubc_wcpdev2`.
3. Open `~/.config/@workday/wdcli/config.json` and copy:
   - `wcpTenantAccessToken["ubc_wcpdev2"]` → secret `WD_DEV_TOKEN`
   - `wcpAccessToken` → secret `WD_WCP_TOKEN`
4. Paste them at `https://github.com/crismwan/ECO-COMS-Extend-App/settings/secrets/actions`. Update both when in doubt.
5. Rerun straight away: `gh run rerun <run-id>`. Don't reuse tokens from an old config.json.

---

## 1b. How the pages are built

Most pages and cards are generated or post-processed by the scripts in `tools/`. Change the script, not the page, or the next rebuild undoes your edit.

- `tools/rebuild_all.sh` runs them all in order: bulk orchestration and pages, org detail, request lists, filter pills and Home cards, Title Case, consistency, empty messages, and `polish.py` last.
- `tools/rebuild_all.sh --check` fails if the result differs from what's committed. The deploy workflow runs it as a warning-only step, "Builders reproduce the committed pages".
- `tools/polish.py` holds the 2026-10-31/11-01 review decisions: grid labels without counts, About boxes, page names, Pacific timestamps, AAA wording. Every builder runs it at the end.
- A hand edit to a page none of the scripts touches is fine. If the check flags your page, move the change into the script that writes it.

## 2. Running tests

All suites are in `test/run-tests.js`.

| Suite | Changes the tenant? | When to run |
|---|---|---|
| `static` | No (no tenant access) | Every push (first deploy step) |
| `smoke` | No (read-only) | After every deploy (automatic) |
| `full` | Yes, writes TEST data (about 15 min) | By hand, before a sign-off or after a risky change |
| `cleanup` | Dry run by default; `--apply` removes data | After `full` |
| `isu` | No, if it passes | By hand, only once ISU writes are live |

Suites combine with commas (`static,smoke`). `isu` never runs unless you name it.

### Locally

```
node test/run-tests.js smoke --verbose
node test/run-tests.js full --role "X:BPMS(ODMT):ROLE:ADVISORS"
node test/run-tests.js cleanup                                    # dry run
node test/run-tests.js cleanup --apply --also <id1,id2> --effective 2026-12-16 --only <orgCode1,orgCode2>
```

The token comes from `--token`, then `WD_DEV_TOKEN`, then `~/.config/@workday/wdcli/config.json`. Results go to the console and `test/results.json`. The runner exits 1 if any test fails.

### From GitHub: "Tests (no deploy)"

`.github/workflows/e2e.yml` runs tests against the deployed app without deploying. Tasks: `static`, `smoke`, `full`, `isu`, `cleanup-dry-run`, `cleanup-apply`. Cleanup inputs: `also` (extra record IDs), `effective` (inactivation date `yyyy-MM-dd`), `only` (limit to these org codes).

Dispatch it through REST. `gh workflow run` fails because GraphQL is blocked.

```
gh api -X POST repos/crismwan/ECO-COMS-Extend-App/actions/workflows/e2e.yml/dispatches \
  -f ref=main -f 'inputs[task]=full'

gh api -X POST repos/crismwan/ECO-COMS-Extend-App/actions/workflows/e2e.yml/dispatches \
  -f ref=main -f 'inputs[task]=cleanup-apply' -f 'inputs[effective]=2026-12-16'
```

**Reading results:** open the run's **Summary** page in the browser. The runner writes its full output there; job logs are truncated or blocked. `test/results.json` is also uploaded as the artifact `test-results-<task>`.

### What a full run leaves behind

- one shell org `X:ADM:TEST:CI:RUN<n>` and one pattern `X:CLW:PATTERN:TEST:TEST:<nnn>:900:<yyyy>W1`, both inactive 45 days out. Orgs can't be deleted.
- one position added to and removed from `X:BPMS(ODMT):ROLE:ADVISORS` (net no change)
- one Denied request `X:ADM:ROLE:TESTROLECIRUN<n>`. It is linked to its review event, so it can't be deleted.
- two pending ISC requests (`<shell org>:ROLE:TESTROLE`, `<pattern>:ROLE:TESTROLE`). Cleanup cancels them.
- about 9 audit records. Cleanup removes them.

Use short run-number names (`...:TEST:CI:RUN<n>`), never timestamp names.

### Cleanup

1. Run `cleanup-dry-run`. Read the Summary: it lists what it would touch next to what it keeps.
2. Run `cleanup-apply`. It cancels the reviews of pending test requests and waits for them to turn Denied, inactivates test orgs, and deletes test audit records.
3. Orgs that already have a scheduled inactivation are reported as failed, because Workday allows only one. They still go inactive on that date.

`ManageShellOrgStatus` writes an audit record even with `validateOnly=true`, so validate-only can't be used for safe write tests yet.

---

## 3. ISU setup (per tenant)

Goal: pages write audit records and request status as the ISU, orchestrations use the ISU credential, and users have View/Get only. A user then can't create, edit or delete these records through direct REST calls.

1. **Create the ISU** and its security group (Workday doc: "Create Integration System Users for apps").
2. **Assign the ISU to the app** with the **App Manager** task. Until you do, every `isuAuth` endpoint fails with HTTP 500 and an empty body.
3. **Create the orchestration credential** for the ISU in Orchestration Builder. ISU credentials can't be used in Custom Agent Action orchestrations.
4. **Switch the page writes to the ISU.** Merge branch `isu-writes-v2`, or run `python3 tools/isu_writes.py` on an up-to-date branch. It adds `{"id": "isuAuth", "scheme": "ISU", "username": "DNU_ISU_ECO_COMS_DEPLOY_CMM"}` to the SMD `siteAuth.authTypes` and sets `"authType": "isuAuth"` on every page write to `comsAuditLogs` and `comsAssignableRoles` (9 as of 2026-11-01). Business process calls and orchestration launches stay `sso`, so the requester stays the initiator. `python3 tools/isu_writes.py --undo` reverts it.
5. **Grant the ISU's security group Put/Get** on the domains that secure the data: **View: COMS Audit Log** (`comsAuditLogs`) and **Manage: COMS Assignable Roles** (`comsAssignableRoles`).
6. **Reduce the user groups to View/Get only** on those domains. Then **Activate Pending Security Policy Changes**.
7. **Run the isu suite:** `node test/run-tests.js isu`, or the e2e workflow with `task=isu`. It checks that every page write uses `isuAuth`, and that a signed-in user's attempts to create an audit record, create a request and edit a request are refused with 401/403. It doesn't probe deletes.
8. Run `full` to confirm the orchestrations' audit writes still land.

**Re-check after every promotion** (dev → impl → sandbox → prod). The App Manager assignment doesn't carry over. Assign the ISU again in each tenant before testing.

---

## 3b. Orchestration security (since 2026-10-31)

Every orchestration a user can launch is secured by the same domain as the page that launches it:

| Orchestration | Security domain |
|---|---|
| AddShellOrg, AddShellOrgPattern, ManageShellOrgStatus, AssignRolePositions | Manage: COMS Shell Organizations |
| StartRoleRequestReview (My Assignable Role Requests) | Manage: COMS Assignable Roles |
| StartAAARequestReview (Submit AAA Role Request; same steps) | Manage: COMS Admin Provisioning |
| DenyRoleRequest | none (launched by the business process as the tenant's launch user) |

Those three domains have `enabledForOrchestrationSecurity: true`. After deploying:

1. Open each domain's security policy and check that the groups who use the pages have the permission a launch needs. Which permission that is (View or Modify) isn't documented; if a user who can open the page gets a permission error on OK, add Modify for their group. **Activate Pending Security Policy Changes**.
2. Test with a user who has the page but not the domain: the launch must be refused.
3. The static suite fails if a user-launched orchestration has no domain, or its domain isn't enabled for orchestration security.

**Withdraw needs Cancel on the business process.** The Withdraw Assignable Role Request page cancels the requester's own review as that user. Add the requester group (or Initiator) to **Cancel** on the Review COMS Assignable Role Request policy, then activate.

---

## 3c. Worker Profile section and Home cards (since 2026-11-02)

These are in the app but stay hidden until an administrator turns them on in each tenant. Security changes are yours to make.

**COMS section on the Worker Profile** (profile group `COMSWorkerProfile`, tasks My Role Requests and Submit Role Request):
1. Grant the domain **View: COMS Profile Section** (`ViewCOMSProfileGroup`) to the groups that should see it: AAA holders, security administrators, and whichever group you use for shell assignable-role holders (shell roles have no security group of their own, so a user-based or role-based group is needed). Then Activate Pending Security Policy Changes.
2. **App Manager** → the app → Configure → Profile Groups grid → "COMS for Worker Profile" → Configure → tick **Display in Profile** → OK. Done in ubc_wcpdev2 on 2026-11-02. (The form only lists reports; the two tasks come from the app.)
3. Check: open your own worker profile and look for **COMS** in the left pane.

The section is context-free: on someone else's profile it still opens *your* requests.

**Home cards** (`cards/*.cardtenantsetting`):
- **ECO-COMS: My Role Requests**: pending and approved-this-month counts for the signed-in user; buttons Open My Requests and Submit a Request. Domain: ManageCOMSAssignableRoles.
- **ECO-COMS: ISC Queue**: number waiting for review and the oldest request date; button Open ISC Queue. Domain: MaintainCOMSAssignableRoles.
- **Not on Workday Home:** Home Cards Workspace doesn't list Extend Cards. Add them to a Workday-delivered hub with card sections: Maintain Hubs → the hub → View Overview Configuration → Edit → Customize Sections and Cards → add a row → pick the card (needs Set Up: Tenant Setup - Hub). My Role Requests reads up to 100 of your own requests; ISC Queue reads the newest 100 requests (Workday allows two data calls per card).
- **Workday Home cards** (`orchestration/MyRoleRequestsHomeCard`, `IscQueueHomeCard`; Workday Home Card orchestrations built by `tools/build_home_cards.py` with the same steps as the tested `*CardData` orchestrations; cached 1 hour). After a deploy, in Workday: **Home Cards Workspace → Add Card → Create External Card**, pick the orchestration, then choose who sees it (needs the Set Up: Custom Card and View: Custom Card policies, granted by the security admin). The card runs as the person viewing Workday Home, so My Role Requests shows their own requests; ISC Queue should only be offered to ISC reviewers (it has no security domain of its own: Workday allows those only on synchronous and asynchronous orchestrations).
  The Home version counts all approved requests (the hub card counts this month's).

## 4. ISC review business process from scratch

Business process type: **Review COMS Assignable Role Request** (`model/ReviewCOMSAssignableRoleRequest.businessprocess`, target COMSAssignableRole, secured by **Maintain: COMS Assignable Roles**, cancel allowed).

### 4.1 Security policy

1. Open the BP type → **Edit Policy**. Give the admin group (HR Administrator) Initiate, the action steps, View All, Approve, Deny and Cancel. Give the approval group **Approve, Deny and View All**.
2. Run **Activate Pending Security Policy Changes**. Groups only appear in the step prompts after this; before it you get "No matches found".

### 4.2 Definition

1. Run **Create Business Process Definition** (Default Definition). Later, find it by searching `bp: Review COMS Assignable Role Request` → related actions → Business Process → **Edit Definition**.
2. Add the steps:

   | Step | Type | Group | Notes |
   |---|---|---|---|
   | a | Initiation | | |
   | b | Approval | Approval group (see 4.3) | ECO-COMS page "Step 2 of 5: Approve / Deny" |
   | c1 | To Do: "Add Assignable Role" | HR Administrator (to confirm) | |
   | c2 | To Do: "Create Role Based Security Group" | HR Administrator (to confirm) | Type Role-Based Security Group, Name = full role name as-is |
   | d | Action: Add Workday Assignable Role ("Link Workday Role") | HR Administrator | ECO-COMS page `reviewRoleRequestAssignableRole` |

   The model's other action step, Create Security Group (page `reviewRoleRequestSecurityGroup`), is no longer used in the definition.
3. Edit Definition shows a page error if a step's group isn't in the BP policy.

### 4.3 The approval group

- The COMSAssignableRole object has no organization context. Its domain's View Domain page lists **Allowed Security Group Types: Public Groups, Unconstrained Groups**. A constrained role-based group shows the approval as Awaiting Action with **All Persons = 0**. Use a user-based group or the **(Unconstrained)** variant of a role-based group.
- The approval group needs **three** policies:
  1. the BP security policy (Approve, Deny, View All)
  2. **Maintain: COMS Assignable Roles** (secures the step pages)
  3. **Manage: COMS Assignable Roles** (secures the request data)

  Then run **Activate Pending Security Policy Changes**.
- An in-flight event keeps its original routing. Definition changes affect only new requests.
- Which group step b uses today (to confirm): the notes record Compliance Administrator in the current definition, and "Accounts Payable Data Entry Specialist (Unconstrained)" as the group used for the live Deny test.

### 4.4 Block self-approval

1. Open step b → **View Workflow Step** → related actions → Business Process → **Maintain Advanced Routing**.
2. Set Routing Restrictions → **Exclude Initiator** = Yes. The definition grid shows "Restriction: Initiator".
3. Consider adding an **Alternate Security Group**. If the restriction excludes everyone eligible, Workday marks the step **Not Required** and skips the approval.
4. The review is started by `StartRoleRequestReview` running as the requester (`AccessTokenFromInitiatingUser`), so the requester is the initiator. Don't move that call to an ISU, or Exclude Initiator stops working.
5. Not yet tested live: it needs a requester who is in the approval group.

### 4.5 Orchestrations on Deny and Cancel

`DenyRoleRequest` marks the request `status: Denied, active: false` and writes a DENY audit record.

1. Tenant-wide, first: **Edit Tenant Setup – Business Processes** → set **User to perform Orchestration Launches**. Without it, the launch configuration below can't be saved.
2. Definition related actions → Business Process → **Configure Orchestrations** → Add:
   - Action **Deny** → Orchestration → **Create Orchestration Launch Configuration** ("ECO-COMS Deny Role Request", BP type Review COMS Assignable Role Request, no parameters)
   - Action **Cancel** → the same launch configuration
3. Pair it with **Cancel** as well as Deny. Deny is offered only while an approval is awaiting action; if the approval auto-completes, only Cancel remains, and without the pairing a cancelled request would stay Pending forever.
4. Launches are queued. Workday says they usually run within about 15 minutes; in practice it is 2–3 minutes. Check the status in **Find Events** → the event → **Orchestrations** tab.
5. After any deploy that changes `DenyRoleRequest`, confirm it still fires (see Open items).

### 4.6 Help text, notification, inbox title

- **Step help text:** definition related actions → Business Process → **Maintain Help Text** → pick the step → **Edit Step Help Text** → fill Help Text (the **Format Text** button opens the rich-text editor) → OK → Done. Format used for all 5 steps: bold "Step N of 5: <name>" title, one-line purpose, a bold "Check" or "How to" bulleted list, then a bold "Next:" or "Outcome:" line. Step numbers match the "Step X of 5" banners on the ECO-COMS pages. Example names use `X:ADM:ROLE:EXAMPLE`.
- **Completion notification:** definition related actions → Business Process → **Add Notification** → Create Workflow Notification:
  - Trigger on Status = **Completed**
  - Recipients = **Initiator**
  - Subject "ECO-COMS role request completed", plus a short body

  Remove the empty Email Addresses row before OK. Completed fires only on the approve path.
- **Inbox titles** read "Review COMS Assignable Role Request: <role name>" because of `useForDisplay: true` on `roleName`.

### 4.7 API facts the pages rely on

- Start an event: POST `/apps/<app>/v1/reviewCOMSAssignableRoleRequestEvents` with `businessProcessTarget.id`. Done by `StartRoleRequestReview`, which then PATCHes `reviewEventWid` onto the request.
- Complete an action step: POST `businessProcess/v1/eventSteps/<id>/submit` with `stepAction.id = d9e4223e446c11de98360015c5e6daf6` (Submitted).
- Cancel: POST `businessProcess/v1/events/<id>/cancel` with `{ "comment": "..." }`.
- A denied or cancelled event reads **"Process Terminated"** in the API.

---

## 5. Debugging orchestrations

Orchestrations: `AddShellOrg`, `AddShellOrgPattern`, `ManageShellOrgStatus`, `AssignRolePositions`, `StartRoleRequestReview`, `DenyRoleRequest`.

- **A launch returns HTTP 200 even when the orchestration fails.** The page's `failOnStatusCodes` never fires, so never trust the success page alone.
- **Run-and-verify:** newShellOrg, newShellOrgPattern, manageShellOrgStatus and editRoleAssignment launch from `onSubmit` with a deferred endpoint, then re-read:
  - org or pattern created → the code is in WQL
  - status or position change → the `/comsAuditLogs?limit=1` `.total` went up, because the orchestration writes its audit record only after its `CheckWWSAccepted` success check

  If the check fails, the page shows "Workday rejected ..." and OK is blocked.
- **Logs:** developer.workday.com → Apps → this app → **Logs** tab (last 15 minutes). Find the "Aggregated step totals" line for the run's commonId: it lists each step with its success and failure counts. `ManageShellOrgStatus` logs the full SOAP response (`LogWWSResponse`), including fault text.
- **Orchestration Activity** tab: runs per orchestration. A BP-triggered run that never launched shows no failed run at all; check the event's Orchestrations tab instead.
- **Input guards:** `ManageShellOrgStatus` → `CheckInputs` (the org code starts with `X:`, the org is a real shell org, and the action matches the inactivate flag). `AddShellOrgPattern` → `CheckPatternName` (the name starts with `<appId>:PATTERN:`). A guard rejection is an ERROR in the logs.
- **Common Workday rejections:**
  - "Organization has conflicting events (in progress or future events)": a future-dated status change already exists.
  - "not valid as an Event Target Role Assignee": a position WID was sent instead of `Position_ID`.
  - InvalidEndPointUrlException "Illegal character": a value in a launch URL wasn't `urlEncode()`d.
- **Getting component JSON:** Orchestration Builder → orchestration Settings → **Open Current Source Code**. If the session is stale: ⋮ → **Revert to App Hub**, or **Discard Session**. The next CI upload overwrites App Hub with the repo version.

---

## 6. Known open items

From `docs/ECO-COMS-NOTES.md` (2026-10-30):

- `DenyRoleRequest` didn't run for test request `X:ADM:ROLE:TESTROLECIRUN22` after its review was cancelled: no failed runs in Orchestration Activity, simply no launch. The run-20 cancel worked. Check the event's Orchestrations tab (Find Events) and the BP's Configure Orchestrations after the deploy that changed the orchestration.
- Fixed 2026-10-31: the two older pending requests (`X:ADM:KEYCLOAK:ANY:ROLE:COORDINATOR` and the AAA request) had a WID as their Enabled For text; `node test/run-tests.js repair --apply` corrected them.
- Branch `isu-writes` (ISU page writes) is ready but unmerged: merge it after the ISU is assigned in App Manager (section 3).

Also outstanding:

- Exclude Initiator is not yet tested live.
- Fixed 2026-10-31: after OK, Manage Role Assignments now goes to a confirmation page (`roleAssignmentSuccess`, flow `editRoleAssignmentFlow`) with a button back to Shell Org Manager for the same application.
- Done 2026-10-31: P-00001 was removed from `X:BPMS(ODMT):ROLE:ADVISORS`.
- The stray org "COMS Application:PATTERN:TEST:TEST:302:152:2026W1" is still active and needs someone with organization maintenance rights to inactivate it.
- Done 2026-10-31: Bulk Role Changes real runs (Apply button and direct) tested live on ADVISORS; the role was left as it was.

## 7. Test data that can't be deleted

- **Orgs and patterns** can only be inactivated:
  - `X:ADM:TEST:ORG:1029`, `1030`, `1031` and `X:CLW:PATTERN:MATH:MATH:300/301/302:951:2026W1`. These six were re-inactivated effective 2026-12-16 after a test accidentally reactivated them.
  - `X:ADM:TEST:ORG:1032` (reactivated, Active)
  - `X:CLW:PATTERN:MATH:MATH_V:303:951:2026W1`
  - every `X:ADM:TEST:CI:RUN<n>` org and `X:CLW:PATTERN:TEST:TEST:...` pattern from full runs
- **Stray org** `COMS Application:PATTERN:TEST:TEST:302:152:2026W1`, from a test bug. It is still active. The app's guard can't touch it (not an `X:` code), and no inactivate task was found in the tenant UI. It is hidden from Shell Org Manager.
- **Requests linked to a BP event** (HTTP 500 "Attempt to delete instance ... with references"):
  - `X:ADM:ROLE:TESTROLE1030`
  - `TESTROLE1031`–`TESTROLE1038`
  - every `X:ADM:ROLE:TESTROLECIRUN<n>`

  Close them by cancelling the review; don't plan to delete them.
- **BP events** are permanent history.
- **Role assignment tests** change a real role, `X:BPMS(ODMT):ROLE:ADVISORS`. As of 2026-10-30 it holds P-00009, P-00010 and P-00011, left for user testing.
- Audit records and requests not linked to an event *can* be deleted through REST, so the audit log isn't tamper-proof until the ISU lockdown is live.
