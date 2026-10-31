# ECO-COMS project notes

App-specific findings for the ECO-COMS Extend app (`ecocomsphase_xclw_cm_sync2_vmzvxm`, tenant `ubc_wcpdev2`). The general platform lessons drawn from them live in `CLAUDE.md`; this file keeps the details: this app's names, tenant configuration, test records and history. Like CLAUDE.md, it can be out of date, so check the tenant and the repo before relying on it.

Tests for this app: `test/run-tests.js` and `test/README.md`.

## AMD data providers — this app's full list

These `dataProviders` are registered in the AMD. All use `apiGatewayEndpoint` (the Workday gateway for the tenant):

| Key | URL template | Use |
|---|---|---|
| `BUSINESS-OBJECT` | `https://api.workday.com/apps/{{site.applicationId}}/v1` | Extend model BOs |
| `COMMON` | `https://api.workday.com/common/v1` | Static common API (worker `/me`) |
| `workday-app` | `{{apiGatewayEndpoint}}/apps/{{site.applicationId}}/v1/` | Gateway BO endpoint |
| `workday-common` | `{{apiGatewayEndpoint}}/common/v1/` | Gateway common API |
| `workday-staffing` | `{{apiGatewayEndpoint}}/staffing/v1/` | Staffing v1 |
| `workday-staffing-v6` | `{{apiGatewayEndpoint}}/staffing/v6/` | Staffing v6 (job positions) |
| `workday-staffing-v7` | `{{apiGatewayEndpoint}}/staffing/v7/` | Staffing v7 |
| `workday-academic` | `{{apiGatewayEndpoint}}/studentAcademicFoundation/v1/` | Academic Foundation API |
| `workday-wql` | `{{apiGatewayEndpoint}}/wql/v1/` | WQL query endpoint |
| `workday-orchestrate` | `{{apiGatewayEndpoint}}/orchestrate/v1/` | Orchestrate API |
| `orchestrate` | `{{apiGatewayEndpoint}}/orchestrate/v1/apps/{{site.applicationId}}/orchestrations/` | App orchestration base |
| `orchestration` | `apiGatewayEndpoint + '/orchestrate/v1/apps/' + site.applicationId + '/orchestrations'` | Alt orchestration key (script form) |
| `workday-bp` | `{{apiGatewayEndpoint}}/businessProcess/v1/` | Business Process API |
| `wdayCom` | `{{apiGatewayEndpoint}}/staffing/v1` | Alt staffing (no trailing slash) |
| `wdayRef` | `{{apiGatewayEndpoint}}/referenceData/v1` | Reference Data API |
| `workday-org` | `{{apiGatewayEndpoint}}/common/v1/` | Common API aliased as org |

**Endpoint for the signed-in worker:** use `baseUrlType: "COMMON"`, `url: "/workers/me"`.

**Endpoint for BO collections:** use `baseUrlType: "BUSINESS-OBJECT"`, `url: "/collectionName"` with `isCollection: true`.


## Orchestrations — debugging runs (confirmed 2026-10-29)

- A page's "success" only means the orchestration launch returned 200. AddShellOrg / AddShellOrgPattern catch errors in a global error handler and still return 200, so **always verify the record exists** (Shell Org Manager counts) and read the run log.
- Run logs: developer.workday.com → Apps → this app → **Logs** tab (last 15 min). Find the "Aggregated step totals" line for the run's commonId: it lists each step with success/failure counts. **Orchestration Activity** tab lists runs.
- Root cause found this way: the PMD sent an empty `comsAppId` (`dropdown.value.id` is empty), so `GetApplication` hit `/comsApplications/` (the collection) and `ExtractOrgType` failed before the SOAP call.
- Shell-org apps like X:ADM have no COMSApplication record. AddShellOrg now takes `orgType` (= application code) as a query param; its GetApplication node is disabled (`isDisabled: true`).
- Organization_Code = Organization_Name = the generated name for both orchestrations (user decision).
- The `Organization_Add_Update` SOAP body via `SendWorkdayApiRequest` POST `/soap/v42.2/Human_Resources` works (HTTP 200, org created) with Organization_Type_Name = `X:CLW` / `X:ADM` and subtype `X:Shell`.
- Orchestration files are single-line JSON: when editing with a script, re-serialize compactly (`separators=(',',':')`) to keep diffs small.

## Orchestrations — failure handling (confirmed live 2026-10-29)

- AddShellOrg / AddShellOrgPattern now have a **Continue on Conditions** step `CheckWWSAccepted` right after `CallAddUpdateOrganization`: assertion `data.CallAddUpdateOrganization.responseStatusCode.is2xxStatusCode().not().or(data.CallAddUpdateOrganization.response.isSoapFault()).not()`, message `"Workday rejected the request for " + <name>`. Node `_type` is `ContinueOnConditions` with `assertions: List<Assertion{assertion: Expr Boolean, message: Expr String}>` (JSON taken from Orchestration Builder output, source: developer.workday.com "Concept: Orchestration Logic Components").
- The global error handler was removed (it only logged and swallowed errors).
- **Confirmed:** a forced WWS rejection (SOAP 500) → CheckWWSAccepted fails with an ERROR log → nothing created. **But the Orchestrate `/launch` call still returns HTTP 200** (text/plain body ~107 bytes) to the PMD, so the page's `failOnStatusCodes` never fires and the success page still shows. The page cannot see failures through the outbound launch endpoint. Solved by run-and-verify, below.
- Getting real JSON for a component the repo doesn't use yet: add it in Orchestration Builder (drag from Components; synthetic drags need HTML5 DragEvents), save that orchestration to App Hub (no deploy), then console → app → Related Actions → **View Source** → Activity build → open the `.orchestration` file. CI's next upload overwrites App Hub with the repo version.
- Orchestration Builder may show "Updates Available in App Hub" with an old session; Discard Session loads the latest.


### Run-and-verify in `onSubmit` (confirmed live 2026-10-30)

Used by newShellOrg / newShellOrgPattern so a Workday rejection blocks OK instead of showing "Created":

- Launch the orchestration from `onSubmit` through a **deferred inbound** endpoint (`baseUrlType: "orchestration"`, url `'/<Name>/launch?param=' + p + ...`, params bare in the URL) with `endpoint.invoke({'p': value, ...})`.
- Then re-read the data with a second deferred endpoint and check the record exists. If it doesn't, call `someField.setError('Workday rejected this request, so nothing was created...')` and return `false`.
- **`.invoke()` on a WQL endpoint that uses `wqlQuery` / `queryId` throws `Unknown Function call: .invoke({ })`.** Instead, call WQL as a plain GET: `"baseUrlType": "workday-wql"`, `"url": "<% 'data?limit=' + lim + '&query=<URL-encoded WQL>' %>"`, and invoke it with `.invoke({'lim': '10000'})`. Keep the WQL static (no user input) and filter in script.
- In an editWizard, Next on a step runs the step's `onSubmit` validation, and the final OK runs it again. The launch only fires once all validation passes, on OK.
- Tested: forced failure → field error, nothing created; valid submit → success page, record verified (Active Orgs 195→196, patterns 377→378).

## manageShellOrgStatus — working (confirmed live 2026-10-30)

- **`Organization_Add_Update` cannot change status.** Its `Organization_DataType` (v42.2 WSDL) has no Inactive element. Sending `<bsvc:Inactive>` returns the SOAP fault "Invalid Subelement Inactive ... for element Organization_Data". Source: the tenant WSDL at `https://wcpdev-services1.wd101.myworkday.com/ccx/service/ubc_wcpdev2/Human_Resources/v42.2?wsdl`. The community.workday.com docs page has moved.
- **The status change uses `Organization_Inactivate` / `Reactivate_Organization_Request`** in the same Human_Resources service:
  ```xml
  <bsvc:Organization_Inactivate bsvc:version="v42.2">
    <bsvc:Validate_Only>false</bsvc:Validate_Only>
    <bsvc:Organization_Reference_Data>
      <bsvc:Integration_ID_Reference><bsvc:ID bsvc:System_ID="WD-WID">{{orgWID}}</bsvc:ID></bsvc:Integration_ID_Reference>
    </bsvc:Organization_Reference_Data>
    <bsvc:Organization_Inactivate_Data bsvc:Effective_Date="{{yyyy-MM-dd}}"/>
  </bsvc:Organization_Inactivate>

  <bsvc:Reactivate_Organization_Request bsvc:version="v42.2">
    <bsvc:Organization_Reference><bsvc:ID bsvc:type="WID">{{orgWID}}</bsvc:ID></bsvc:Organization_Reference>
  </bsvc:Reactivate_Organization_Request>
  ```
  `System_ID="WD-WID"` with the org's WID is accepted. A success response is an empty SOAP Body. Reactivate is untested.
- **Use `Validate_Only=true` to test a WWS call safely.** Workday checks the request fully and changes nothing.
- **Orchestration text templates support `{{#if}}` but NOT `{{else}}`.** The build fails with "illegal start of simple expression". Use two `{{#if}}` blocks with Boolean flags. Handlebars treats any non-empty string as true, so the flags come from CreateValues Boolean assignments: `data.GetInputParams.includeInactive.equals("true")` (type `Boolean`, Expr `["Expr","Boolean"]`). This uploaded and ran fine.
- **Logging the WWS response:** a `Log` node with message `"..." + data.CallOrganizationUpdate.response.toString()` writes the full SOAP response, including fault text, to developer.workday.com → app → Logs. Kept in ManageShellOrgStatus as `LogWWSResponse`.
- **Reading CI build errors:** `gh run view --log` is blocked from the cloud container. The GitHub run page (Summary → "Upload Failure") in the browser shows the App Hub build output.
- **Page check (run-and-verify):**
  - The page reads `GET BUSINESS-OBJECT /comsAuditLogs?limit=1` `.total` before and after the launch. The orchestration writes an audit record only when Workday accepts the change.
  - A WQL count of `comsAuditLogs` lagged and gave false "rejected" errors.
  - Checking `cf_active1` can't work for future-dated changes, because the org is still active today.
- The page has an **Effective Date** field (sent to the SOAP request) and standard OK/Cancel, with `cancelOverride` to shellOrgManager.
- **Scope note:** a status change dated in the future leaves Shell Org Manager showing "Active" until that date.
- Test records inactivated effective 2026-12-15:
  - `X:ADM:TEST:ORG:1029`, `1030`, `1031`
  - `X:CLW:PATTERN:MATH:MATH:300/301/302:951:2026W1`
  - 1029 was confirmed in its Workday audit trail ("made inactive on 2026-12-15").

## Role assignments (Assign_Roles) — working (confirmed live 2026-10-30)

- Pages:
  - shellOrgManager "Manage Role Assignments" grid has one row per role + org, with positions taken from `cf_ZCF_EE_RoleAssignedToAsPositionRestrictions`.
  - Manage → `editRoleAssignment` (EDIT) directly; the separate view page was removed 2026-10-30 at the user's request (fewer clicks). Related actions stay on the shellOrgManager grid.
  - The edit page's `onSubmit` launches `AssignRolePositions` once per change and run-and-verifies with the `/comsAuditLogs?limit=1` `.total` count.
- WWS: Staffing v42.2 `Assign_Roles_Request` (`/soap/v42.2/Staffing`). Structure matches the user's Assign Roles EIB v35.0:
  - Event_Target_Assignee
  - Role_Assigner (WID)
  - Assignable_Role (WID)
  - Update_Later_Dated_Assignments=true
  - Assignees_to_Add / Assignees_to_Remove
  - Auto_Complete=true, Run_Now=true
- **Assignee IDs:**
  - The `allPositions` WID is rejected ("The provided Role Assignee is not valid as an Event Target Role Assignee").
  - **Add:** use `bsvc:type="Position_ID"` with `cf_PositionID` (e.g. P-00010).
  - **Remove:** use `type="WID"` with the current assignee id from the role-assignment data.
  - Both were tested live: P-00010 was added to X:BPMS(ODMT):ROLE:ADVISORS and then removed. Multi-position also tested: P-00009 + P-00010 added in one submit, then both removed in one submit (2 launches each, audit-count check passed).
- **`relatedTask` / instance links on instanceList render only on VIEW pages** (developer.workday.com instanceList reference). This is why there are separate view and edit pages.
  - On VIEW grids: an instanceList cell with `values` + `widKey:"id"` + `view:true` + `relatedTask:true` gives related actions on hover.
- **Read-only instanceList on an EDIT page:** `values` alone or `instanceList` showed "(empty)". Use `"values": "<% [] %>"` + `selectedValuesAndDescriptors`.
- **URL-encode free text in launch URLs** (`name.urlEncode()`). A space in a role or org name gives InvalidEndPointUrlException "Illegal character".
- **2026-10-30 (user request: fewer clicks):** the separate manageRoleAssignment view page was removed. Manage on the grid now opens editRoleAssignment directly. That page shows a one-row "Current Assignment" grid (role, org, current positions) above the Change Positions fields.
- **Confirmed live:** an instanceList grid cell on an EDIT page with `view:true` + `relatedTask:true` renders plain text, with no link and no related actions.
  - `values` alone renders blank cells on an edit page. Use `values:[]` + `multiSelect:true` + `selectedValuesAndDescriptors`.
  - An edit-page grid needs `doNotAdd:true` / `doNotRemove:true` to hide the +/- row icons. `readOnly:true` did not hide them.
- **More edit-page attempts at grid related actions, all failed (live 2026-10-30):**
  - `instanceList` as a script string fails the build ("Cannot deserialize ... ArrayList<Instance> from String"). It must be a literal array. For a variable list use `instanceListLoopTag` (`type: instanceLoop`, `on`, `as`, `templateInstance`).
  - Literal `instanceList` / `instanceLoop` with `wid` and `view:true`, plus grid `enabled:false`: the cells render blank.
  - Adding `id` + `selectedValues` + `relatedTask:true`: the values show as removable prompt pills, with no related actions.
  - Build warning: "If you set the relatedTask attribute ... the pmd must be a view page."
  - Conclusion: related actions need a VIEW page. The "pending ISC requests" grid that has them (iscRoleRequestsView) is a VIEW page.
- **Left for user testing (2026-10-30):** X:BPMS(ODMT):ROLE:ADVISORS now holds P-00009 (Pedro Santiago), P-00010 (Beth Liu) and P-00011 (Maria Cardoza). P-00009 and P-00010 were added in one submit, effective 2026-10-30.
- Position search matches by ID too (e.g. "P-00010").
- The Current Assignment grid's narrow positions column only shows up in a narrow (~800px) window. At desktop width it displays in full. The grid now uses `gridType: LIST`.
- **Audit Log Viewer "Property Error found: .worker" (fixed 2026-10-30):** audit records written by the orchestrations (role assignment, status) have no `worker` / `application`. Guard SINGLE_INSTANCE sub-properties with `!empty(logEntry.worker) ? (logEntry.worker.descriptor ?? '') : ''`, and default the text fields with `?? ''`.
- After OK, the edit page returns to the app home, not the manage page (seen on both tests). A flow or conclusion page would be needed to land back on Shell Org Manager.

## Audit log design (confirmed live 2026-10-30)

- **One writer per change.**
  - Orchestrated changes (AddShellOrg, AddShellOrgPattern, ManageShellOrgStatus, AssignRolePositions): the orchestration writes the record after CheckWWSAccepted.
  - The page-level `postAuditLog` outbound was removed from newShellOrg, newShellOrgPattern and manageShellOrgStatus.
  - Assignable-role pages (assignableRoleManager, adminProvisioning, assignableRoleManagerMaintain, deleteAssignableRole) have no orchestration, so they still write via their own outbound.
- **Pages pass to every launch:** `changedBy` (selectedWorker.descriptor, urlEncoded), `changedByWid` (selectedWorker.id), and `timestamp` (`date:now().format("yyyy-MM-dd'T'HH:mm:ss'Z'")`, urlEncoded). Before this, the orchestrations had no timestamp or user.
- **Previous AddShellOrg / AddShellOrgPattern audit writes never landed.** The template sent `"worker": "<wid>"` and `"application": ""` as plain strings to SINGLE_INSTANCE fields. Don't template SINGLE_INSTANCE fields as strings. Store WIDs in TEXT fields instead (`changedByWid`, `orgWid`, `roleWid`, `positionWid`).
- **COMSAuditLog new fields:** `effectiveDate` (DATE; the template sends "yyyy-MM-dd", which works), `roleName`, `positionName`, plus the TEXT WID fields above. `worker` and `application` stay but are unused.
- **Fixed vocabulary:**
  - `objectType` (Change Type): Shell Org | Shell Org Pattern | Org Status | Role Assignment | Assignable Role.
  - `action`: ADD | INACTIVATE | REACTIVATE | ASSIGN POSITION | REMOVE POSITION | REQUEST | APPROVE | DENY | DELETE.
  - manageShellOrgStatus now sends REACTIVATE (not ACTIVATE).
- **Viewer** (auditLogViewer, VIEW page):
  - Columns: Timestamp, Change Type, Action, Organization, Role, Position, Effective Date, Changed By, Details. Rows use `list:sort(auditLogs.data ?? [], 'timestamp', false)`, newest first.
  - **Related actions from a stored WID:** the cellTemplate is a `fieldSet` with two children: an `instanceList` (`values: [{'id': wid, 'descriptor': name}]`, `widKey:"id"`, `view`/`relatedTask` true, `visible: !empty(wid)`) and a `text` fallback (`visible: empty(wid)`). Confirmed: 4 related-action icons render.
- **Position WID for adds:** editRoleAssignment looks it up per added position with a deferred WQL GET (`posWidLookup`): `SELECT workdayID FROM allPositions WHERE cf_PositionID = '<P-id>'`. For removes, the assignee WID is `p.id`.
- **Deleting BO records from a page:**
  - An outbound `DELETE /collection?bulk=true` with a `values` body is **silently skipped**. Nothing is deleted and there's no error.
  - What works: a grid with `deleteEndPoint` + DELETE `'/collection/' + idCell.value`, removing rows and then OK (one DELETE per row).
  - Rows can be removed in bulk with JS that clicks `button[data-automation-id="removeRow"]`.
  - Used once to purge the 30 old audit records (2026-10-30). The temporary purgeAuditLogs page was then removed.
- **Reports consolidated 10 → 4:**
  - AllAssignableRoles (label "All Assignable Role Requests", 21 columns, 3 domains)
  - AllShellOrgs ("All Shell Org Requests", 11 columns, 2 domains)
  - AcademicUnits ("All COMS Applications")
  - AllAuditLogs (new columns)
  - A report can take multiple `defaultSecurityDomains`.
  - Unused WQL components were removed: academicUnits, auditLog, customOrganizationsFUH, shellOrgManager.
- **COMSShellOrgRequest business object:** nothing writes to it. Its only reader (assignableRoleManager) is `exclude: true`. It predates creating shell orgs directly via WWS, and its report was kept.
- **Full end-to-end test, all six flows (2026-10-30 ~17:30–17:55 UTC).** Each wrote exactly one complete audit record:
  - Assignable role request `X:ADM:ROLE:TESTROLE1030` (now Pending ISC Review)
  - AAA request for X:ADM
  - Shell org `X:ADM:TEST:ORG:1032`
  - Pattern `X:CLW:PATTERN:MATH:MATH_V:303:951:2026W1`
  - Inactivate and **Reactivate** of 1032. This was the first live Reactivate; 1032 is Active again.
- **Fixed during the test:**
  - assignableRoleManager and adminProvisioning had `standardEditButtonsHidden: true` with no editButtonBar, so there was no way to submit. The flag was removed and `cancelOverride` set to home.
  - Org names for inactive orgs carry " (inactive)". manageShellOrgStatus must `urlEncode()` the name and code (InvalidEndPointUrlException "Illegal character ' '") and strip " (inactive)". newShellOrg and newShellOrgPattern now urlEncode their names too.
  - Request audit records now include the selected positions and, for AAA, the application as Organization. Deployed but not yet seen live.
- **Linking to Workday events (developer.workday.com "Reference: Context Global Functions" + tenant WSDLs):**
  - `context.orchestrateId()` returns the orchestration instance ID (X-Orchestrate-Id). It is not a tenant instance, so it can be stored as text but cannot have related actions.
  - Staffing `Assign_Roles_Response` returns `Assign_Roles_Event_Reference`, the BP event. This is linkable.
  - Human_Resources `Organization_Add_Update` and `Organization_Inactivate` have **no output message** (one-way, empty body). They give no event and no new-org WID.
  - `Reactivate_Organization_Response` returns `Organization_Reference`.
- **CI:** a run stuck at "in_progress" with every step completed (job conclusion success) had actually deployed. `gh run cancel/rerun` and force-cancel all refuse such a run. Check the job conclusion with `gh api .../runs/<id>/jobs`.
- **CI:** a failure at "Authenticate as system user (for upload)" in about 20s was transient; a rerun passed.

## Request data (updated 2026-10-30)

- **Enabled For:** Assignable Role Manager and Admin Provisioning compute it once in the `postAssignableRole` endpoint `values`: the picked Functional Unit Hierarchy or Academic Unit's **name** in `enabledForOrganizationTypes` (shown as text by every page), its WID in `enabledForWid`, plus `functionalUnitHierarchyWid/Description` or `academicUnitWid/Description`. Nothing picked → "Academic Unit - University of British Columbia". The pickers and Delegated Roles no longer bind these fields (they used to write a WID / a role list into the display field).
- **Positions:** requests save `positions` / `positionWids` (WIDs, comma-separated) and `positionNames`. The pending, manager, maintain and delete pages show the saved names (split with `', (?=P-[0-9])'`) instead of looking them up in the uncapped `workday-staffing-v6 jobs` call, which returns 20 rows by default. Older requests without names still use the lookup.
- **Audit records for requests** save `positionWid` (comma-separated) next to `positionName`, so the Audit Log Viewer can link each position. DenyRoleRequest saves `positionWid` from the request's `positionWids` too. The viewer resolves role WIDs for the AAA role from `allAAArolesinTenant`; a requested role that doesn't exist in Workday yet stays text.
- **Audit Log Viewer memory limit (fixed):** the grid used to filter all ~580 shell orgs and all roles inside every row; it now builds the two lookup lists once, cut down to the names the records mention.
- **Shell Org Manager** lists only pattern codes that start with `X:` and contain `:PATTERN:`.

## CI/CD — GitHub Actions deploy pipeline

The deploy workflow (`.github/workflows/deploy.yml`) pushes to Workday on every `main` branch push. After every `git push`, check `gh run list` and confirm `conclusion: success` before declaring anything deployed.

### WD_DEV_TOKEN expiry (most common failure)

**Symptom:** GitHub Actions run fails in ~11–16 seconds at the step "Pre-populate wdcli config with developer token". All other steps are skipped.

**Root cause:** The `WD_DEV_TOKEN` GitHub secret holds a Workday PKCE user token (JWT) scoped to `ubc_wcpdev2`. This token has an ~8-hour TTL. When it expires, the workflow decodes the JWT, compares `exp` to `now`, and exits 1 with:
```
WARNING: WD_DEV_TOKEN EXPIRED (exp=..., now=..., expired ...s ago)
ACTION: run 'wdcli app deploy ...' locally, log in, update WD_DEV_TOKEN secret
```

**Fix (must be done by the user — requires browser login):**
1. On the local machine with `wdcli` installed, run:
   ```
   wdcli app deploy ecocomsphase_xclw_cm_sync2_vmzvxm
   ```
2. Complete the browser login for the `ubc_wcpdev2` tenant.
3. Open `~/.config/@workday/wdcli/config.json` and copy the value at `wcpTenantAccessToken["ubc_wcpdev2"]`.
4. Update the `WD_DEV_TOKEN` GitHub secret at:
   `https://github.com/crismwan/ECO-COMS-Extend-App/settings/secrets/actions`
5. Re-run the failed workflow with `gh run rerun <run-id>`.

**Important:** The code itself is fine when this failure occurs — do not revert commits or alter the code. The failure is purely an infrastructure/secrets rotation issue.

### Tests in the pipeline (updated 2026-10-30)

- One runner, `test/run-tests.js`, with suites static (first deploy step, no tenant access), smoke (after every deploy), full and cleanup (by hand), and isu (by hand, only once ISU writes are live). Details and coverage: `test/README.md`.
- Live suites use the PKCE `WD_DEV_TOKEN`. It works for api.workday.com BO REST, WQL, BP events and orchestration launch.
- `ManageShellOrgStatus` writes its audit record even when `validateOnly=true`, so validate-only can't be used for safe write tests until the audit write is made conditional.
- Full-suite test data uses short run-number names (`X:ADM:TEST:CI:RUN<n>`); don't reuse the old timestamp names such as `CI:2610302152` (user request).
- The test role for position add/remove is `X:BPMS(ODMT):ROLE:ADVISORS` (override with `--role`). Run 22 left **P-00001** assigned there because WQL hadn't shown the add yet; check and remove it by hand. The readback now waits 90 s.
- Stray org from a test bug: `COMS Application:PATTERN:TEST:TEST:302:152:2026W1` (a pattern named from the app's display name instead of `appId`). Still active; the app's status guard can't touch it (not an `X:` code) and no inactivate task was found in the tenant UI. Hidden from Shell Org Manager since the page only lists `X:…:PATTERN:` codes.

### ManageShellOrgStatus input guard (deployed and confirmed live 2026-10-30)

- `auditAction` (ExtractInactiveFlag) = `(if (data.ExtractInactiveFlag.isInactivate) "INACTIVATE" else "REACTIVATE")`. The audit template and logs use it, not the caller's `action`.
- `LookupShellOrgs`: GET `/wql/v1/data?limit=10000&query=<encoded: SELECT workdayID FROM topLevelOrganizations WHERE code contains 'X:'>` with the default credential. Untested: that the orchestration's Workday API path base accepts `/wql/v1/...`.
- `CheckInputs` (ContinueOnConditions) runs before the SOAP call. It requires:
  - includeInactive is true or false
  - action equals auditAction
  - orgCode startsWith "X:"
  - orgId is not empty
  - LookupShellOrgs response `.toString().contains(orgId)`
- String member functions (developer.workday.com "Reference: String Member Functions") include contains, startsWith, equals, isEmpty, toString.
- The full suite's Guard.actionMismatch and Guard.notShellOrg tests prove the rejections; they pass, so the orchestration's GET to `/wql/v1/data?...` works with the default credential.
- AddShellOrgPattern has a matching guard, `CheckPatternName`: the name must start with the COMS application's `appId` + `:PATTERN:` (test Guard.patternName).

### ISU authentication (developer.workday.com "Configure ISU Authentication in Presentation Components")

- SMD: `"siteAuth": {"authTypes": [{"id": "isuAuth", "scheme": "ISU", "username": "<ISU username>"}]}`. On each PMD endpoint, set `"authType": "isuAuth"`.
- Setup ("Create Integration System Users for apps"):
  1. Create the ISU.
  2. Assign it to the app with the **App Manager** task.
  3. Create orchestration credentials in Orchestration Builder. ISU credentials can't be used in Custom Agent Action orchestrations.
- Planned use: make audit records and request status writable only by the ISU, through app logic, with users on View only.

### Test-only workflow and cleanup (confirmed live 2026-10-30)

- `.github/workflows/e2e.yml` ("Tests (no deploy)") runs `test/run-tests.js` without deploying. Tasks: static, smoke, full, isu, cleanup-dry-run, cleanup-apply. Cleanup options: also, effective, only.
- Dispatch it with `gh api -X POST repos/crismwan/ECO-COMS-Extend-App/actions/workflows/e2e.yml/dispatches -f ref=main -f 'inputs[task]=full'`. `gh workflow run` fails because GraphQL is blocked.
- Read results on the run's Summary page in the browser. run-tests.js writes its full output to `GITHUB_STEP_SUMMARY`; job logs are truncated or blocked.
- **The PKCE `WD_DEV_TOKEN` works for api.workday.com BO REST, WQL, BP events and orchestration `POST .../orchestrations/<Name>/launch`.** The first full run passed 21 tests.
- **ManageShellOrgStatus picks inactivate vs reactivate from `includeInactive`** ("true" = inactivate), **not from `action`**. `action` only goes into the audit record. Sending action=INACTIVATE with includeInactive=false reactivated 6 test orgs, cancelling their 2026-12-15 inactivations, and wrote INACTIVATE audit records.
- **Future-dated events block status changes.** "Organization has conflicting events (in progress or future events) so it cannot be inactivated." Choose an effective date after the last future event. The 6 orgs were re-inactivated effective 2026-12-16.
- **A request linked to a BP event can't be deleted:** HTTP 500 "Attempt to delete instance ... with references". TESTROLE1031-1038 remain (Approved/Denied, not pending). Audit records and unlinked requests delete fine via REST DELETE, so the audit log is not immutable.
- Each full run leaves one `X:ADM:TEST:CI:<stamp>` org (inactive 45 days out) and 2 audit records. cleanup-apply removes the audit records.

### WD_WCP_TOKEN expiry (2026-10-30)

- **Symptom:** "Pre-populate" passes, then "Deploy to ubc_wcpdev2 via wdcli" fails with `[CI-401] UNAUTHORIZED URL: https://api.us.wcp.workday.com/aos/v1/deploy` and "The supplied authentication is invalid". It started about 20:00 UTC on 2026-10-30, roughly 1 h after the 19:49 success.
- **Cause not pinned down:** the `WD_DEV_TOKEN` expiry check passed, and so did the new "Check platform token (WD_WCP_TOKEN) expiry" step (it fails early with instructions if it can decode an expired `exp`). So the 401 is a revoked or invalidated session, not a plain expiry. Refreshing both tokens is the fix to try first.
- The 4 failed runs before the test commit were CLAUDE.md-only commits. The tenant still has the 19:49 UTC app version.
- **Fix:** do the same interactive `wdcli app deploy`, then update BOTH secrets from config.json: `WD_DEV_TOKEN` = `wcpTenantAccessToken.ubc_wcpdev2`, `WD_WCP_TOKEN` = `wcpAccessToken`.

### Run time baseline

- A healthy deploy run completes in **~1m15s**.
- A run that finishes in **<20 seconds** has almost certainly failed at the token step (not a code error).

## ISC review business process (confirmed live 2026-10-30)

- `model/ReviewCOMSAssignableRoleRequest.businessprocess` targets COMSAssignableRole. Steps: details (VIEW `/reviewRoleRequestDetails/{eventId}`), approval (VIEW `/reviewRoleRequestApproval/{eventId}`), action steps CreateSecurityGroup and AddWorkdayAssignableRole (EDIT `/...{eventStepId}`). AMD tasks use those routingPatterns.
- Request pages save a fixed `referenceId` (hidden `requestRefHidden`, set at page load) and then launch `StartRoleRequestReview` (outbound POST, `orchestration` base, `?ref=`). The orchestration finds the request by `referenceId` (now indexed), POSTs `/apps/<app>/v1/reviewCOMSAssignableRoleRequestEvents` with `businessProcessTarget.id`, and PATCHes `reviewEventWid` onto the request.
- Orchestration build error "Function stringAtJsonPath cannot be applied to an instance of DataType": read API responses as `data.X.response.asJSON().stringAtJsonPath(...)`.
- Step pages get context with `GET workday-bp eventSteps/<eventStepId>` → `event.id`, then `GET workday-bp events/<id>` → `for.id` (the request WID). Inbound endpoints can reference earlier ones in their URL.
- An action step is completed by outbound `POST workday-bp eventSteps/<id>/submit` with `stepAction.id = d9e4223e446c11de98360015c5e6daf6` (Submitted). Tested: the step closed and the next step arrived in the inbox.
- Tenant setup, done by hand:
  1. BP type page → **Edit Policy**. HR Administrator on Initiate, both action steps, View All, Approve, Cancel, Deny.
  2. **Activate Pending Security Policy Changes**.
  3. **Create Business Process Definition (Default Definition)** → Edit Definition: a Initiation, b Approval, c Action Create Security Group, d Action Add Workday Assignable Role, each with Group HR Administrator.
  - Step groups only appear in the prompt AFTER the policy is activated ("No matches found" before that).
  - The definition is found by searching `bp: <name>`. Its related actions → Business Process → Edit Definition / Configure Orchestrations.
- When the initiator is in the approval group, Workday auto-completes the approval step. HR Admin testing goes straight to step 3.
- **Deny handling (tested live 2026-10-30 via a Cancel pairing):** orchestration `DenyRoleRequest` (template "Workday Business Process", flow type `.maya.FlowBusinessProcessTriggered`, start `StartBusinessProcess`, end `EndEmptyMaya`, default credential `AccessTokenFromInitiatingUser` — JSON copied from Orchestration Builder → Settings → Open Current Source Code). It GETs the request, PATCHes `status: Denied, active: false`, and POSTs a DENY audit record.
  - Denied request WID: `bp.eventTarget().getIDValues("WID").get(0)`. `bp.eventTarget().toString("WID")` is in the docs but fails the build ("Wrong number of arguments for function toString").
  - Timestamp: `datetime.now("UTC").format("yyyy-MM-dd'T'HH:mm:ss'Z'")` (developer.workday.com "Reference: DateTime Global Functions" + LocalDateTime member `format`). `bp.*` functions: "Reference: Business Process Global Functions".
  - Tenant: definition related actions → Business Process → **Configure Orchestrations** → Add → Action Deny → Orchestration → Create Orchestration Launch Configuration ("ECO-COMS Deny Role Request", BP type Review COMS Assignable Role Request, no parameters).
  - The launch configuration can't be saved until the tenant-wide **Edit Tenant Setup – Business Processes → User to perform Orchestration Launches** is set. Set to lmcneil (user approved, 2026-10-30).
  - Workday says BP-triggered orchestrations usually launch within ~15 minutes; in practice they ran in about 2–3 minutes. Status: Find Events → Orchestrations tab.
  - **Deny is only offered while an approval is awaiting action.** When the initiator is in the approval group, approval auto-completes and only Cancel remains. So DenyRoleRequest is also paired with the **Cancel** action (Configure Orchestrations). A cancelled request is marked Denied with a DENY audit record; without this it would stay "Pending" forever.
  - The DENY audit shows position names: request pages save `positionNames` (TEXT, from the positions widget's `selectedEntries` descriptors) and the orchestration uses it, falling back to `positionWids`.
- **Current BP definition (user-edited 2026-10-30):** a Initiation → b Approval (Compliance Administrator) → c1 To Do "Add Assignable Role" → c2 To Do "Create Role Based Security Group" → d Action (EDIT page reviewRoleRequestAssignableRole, "Link Workday Role"). The old CreateSecurityGroup action step / reviewRoleRequestSecurityGroup page is unused.
  - Security group: Type of Tenanted Security Group = **Role-Based Security Group**, Name = the **full role name as-is** (e.g. X:ADM:ROLE:TESTROLE1035; user decision). Step d prefills the name with `request.securityGroupName ?? request.roleName`.
  - Compliance Administrator needs Deny / View All on the BP policy for the Deny button to appear. Saving that policy change was blocked for the agent (permission grant); the user does it, then Activate Pending Security Policy Changes.
- **Approval group must be able to resolve people (live 2026-10-30):** with step b set to "Accounts Payable Data Entry Specialist" (a *constrained* role-based group), TESTROLE1036's approval showed Awaiting Action with **All Persons = 0**. Confirmed: the app domain "Manage: COMS Assignable Roles" lists **Allowed Security Group Types: Public Groups, Unconstrained Groups** (View Domain page), because COMSAssignableRole has no organization context. Use a user-based group or the **(Unconstrained)** variant.
  - An approver needs the group in **three** policies: the BP security policy (Approve, Deny, View All), the domain **Maintain: COMS Assignable Roles** (secures the four step pages; on 2026-10-30 it held only HR Administrator + the deploy ISSG), and **Manage: COMS Assignable Roles** (the request data). Then Activate Pending Security Policy Changes. The agent may not edit security policies; the user does this.
- **Fixed (live 2026-10-30):** with "Accounts Payable Data Entry Specialist (Unconstrained)" on the BP policy (View All, Approve, Deny), both domains, and step b, TESTROLE1038's approval resolved **8 persons** (incl. James Walker). Real Deny then tested end to end: James Walker (proxied by the user) denied TESTROLE1038 at 13:30:17, DenyRoleRequest completed the same second, a DENY audit record was written and the request left the pending list. An in-flight request keeps its original routing; definition changes only affect new requests. Edit Definition shows a page error if a step's group isn't in the BP policy.
- **Self-approval blocked (2026-10-30):** step b → View Workflow Step → related actions → Business Process → **Maintain Advanced Routing** → Routing Restrictions → **Exclude Initiator** = Yes. The definition grid shows "Restriction: Initiator".
  - The review is started by StartRoleRequestReview running as the requester (AccessTokenFromInitiatingUser), so the initiator is the requester.
  - Per Workday docs (Business Process Step Types), if a restriction excludes everyone eligible, the step is marked **Not Required** and skipped. Consider an Alternate Security Group so a lone approver who is also the requester can't skip approval.
  - Not yet tested live. Testing needs a requester who is in the approval group, and temporarily swapping the step group was blocked for the agent (permission change).
- **Step help text:** definition related actions → Business Process → **Maintain Help Text** → pick the step → Edit Step Help Text → fill Help Text → OK → Done. Rewritten for all 5 steps on 2026-10-30 in one format: bold "Step N of 5: <name>" title (+ who does it), one-line purpose, bold "Check" / "How to" label with a bulleted list, then a bold "Next:" or "Outcome:" line. Step numbers match the "Step X of 5" banners on the ECO-COMS step pages. Example names use X:ADM:ROLE:EXAMPLE.
  - The Help Text cell is a plain textarea plus a **Format Text** button that opens a ProseMirror rich-text editor (bold, italic, underline, colour, bulleted list, link, email). No numbered list. Line breaks typed in the textarea are kept.
  - Agent technique: clear the *textarea* first (click it, ctrl+a, Delete; keys reach the textarea but not the ProseMirror editor), open Format Text, then dispatch a synthetic `paste` ClipboardEvent with `text/html` on `.ProseMirror`. Formatting is preserved. Then Done → OK.
- **Completion notification (2026-10-30):** definition related actions → Business Process → **Add Notification** → Create Workflow Notification: Trigger on Status = **Completed**, Recipients = **Initiator**, subject "ECO-COMS role request completed", short body. Completed only fires on the approve path (a deny ends with status Denied). Remove the empty Email Addresses row before OK.
- **Inbox titles:** `useForDisplay: true` on COMSAssignableRole `roleName` makes inbox items read "Review COMS Assignable Role Request: <role name>".
- **Orchestration Builder "Open Current Source Code"** (orchestration Settings page) shows the JSON without saving to App Hub — easier than Save + View Source. A stale App Builder session can be reset with ⋮ → Revert to App Hub.
- Browser pane tips: narrow window → Workday prompts open as full-screen pickers. Use resize_window 1600x1000 for BP grids. Related-action menus need hover to open sub-menus. Date fields need per-key input (`key "1 0 3 0 2 0 2 6"`).

## Open items (2026-10-30, Workday down overnight)

- `DenyRoleRequest` did not run for test request `X:ADM:ROLE:TESTROLECIRUN22` after its review was cancelled (no failed runs in Orchestration Activity, simply no launch). The run-20 cancel worked. Check the event's Orchestrations tab (Find Events) and the BP's Configure Orchestrations after the deploy that changed the orchestration.
- Two real pending requests (`X:ADM:KEYCLOAK:ANY:ROLE:COORDINATOR` and the AAA request) were saved before the Enabled For fix and hold a WID (`b40d8b01636710017a4c968020320000`) as their Enabled For text. The smoke check Requests.pendingEnabledFor fails on them until they're corrected or closed (user decision pending).
- Branch `isu-writes` (ISU page writes) is unmerged; its static check now lives in the isu suite of `test/run-tests.js`. When merging, drop its edits to the deleted `test/static_checks.py` / `test/e2e.js`.
