# ECO-COMS project notes

App-specific findings for the ECO-COMS Extend app, **XTND-0037-XFD_SEC-Custom_Organization_Management** (reference ID `ecocomsphase_xclw_cm_sync2_vmzvxm`, tenant `ubc_wcpdev2`). The general platform lessons drawn from them live in `CLAUDE.md`; this file keeps the details: this app's names, tenant configuration, test records and history. Like CLAUDE.md, it can be out of date, so check the tenant and the repo before relying on it.

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

- A page's "success" only means the orchestration launch returned 200. IORC_0037_XFD_SEC_Create_Application_Shell_Org / IORC_0037_XFD_SEC_Create_Pattern_Shell_Org catch errors in a global error handler and still return 200, so **always verify the record exists** (Shell Org Manager counts) and read the run log.
- Run logs: developer.workday.com → Apps → this app → **Logs** tab (last 15 min). Find the "Aggregated step totals" line for the run's commonId: it lists each step with success/failure counts. **Orchestration Activity** tab lists runs.
- Root cause found this way: the PMD sent an empty `comsAppId` (`dropdown.value.id` is empty), so `GetApplication` hit `/comsApplications/` (the collection) and `ExtractOrgType` failed before the SOAP call.
- Shell-org apps like X:ADM have no COMSApplication record. IORC_0037_XFD_SEC_Create_Application_Shell_Org now takes `orgType` (= application code) as a query param; its GetApplication node is disabled (`isDisabled: true`).
- Organization_Code = Organization_Name = the generated name for both orchestrations (user decision).
- The `Organization_Add_Update` SOAP body via `SendWorkdayApiRequest` POST `/soap/v42.2/Human_Resources` works (HTTP 200, org created) with Organization_Type_Name = `X:CLW` / `X:ADM` and subtype `X:Shell`.
- Orchestration files are single-line JSON: when editing with a script, re-serialize compactly (`separators=(',',':')`) to keep diffs small.

## Orchestrations — failure handling (confirmed live 2026-10-29)

- IORC_0037_XFD_SEC_Create_Application_Shell_Org / IORC_0037_XFD_SEC_Create_Pattern_Shell_Org now have a **Continue on Conditions** step `CheckWWSAccepted` right after `CallAddUpdateOrganization`: assertion `data.CallAddUpdateOrganization.responseStatusCode.is2xxStatusCode().not().or(data.CallAddUpdateOrganization.response.isSoapFault()).not()`, message `"Workday rejected the request for " + <name>`. Node `_type` is `ContinueOnConditions` with `assertions: List<Assertion{assertion: Expr Boolean, message: Expr String}>` (JSON taken from Orchestration Builder output, source: developer.workday.com "Concept: Orchestration Logic Components").
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
- **Logging the WWS response:** a `Log` node with message `"..." + data.CallOrganizationUpdate.response.toString()` writes the full SOAP response, including fault text, to developer.workday.com → app → Logs. Kept in IORC_0037_XFD_SEC_Change_Shell_Org_Status as `LogWWSResponse`.
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
  - The edit page's `onSubmit` launches `IORC_0037_XFD_SEC_Assign_Remove_Role_Positions` once per change and run-and-verifies with the `/comsAuditLogs?limit=1` `.total` count.
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
  - Orchestrated changes (IORC_0037_XFD_SEC_Create_Application_Shell_Org, IORC_0037_XFD_SEC_Create_Pattern_Shell_Org, IORC_0037_XFD_SEC_Change_Shell_Org_Status, IORC_0037_XFD_SEC_Assign_Remove_Role_Positions): the orchestration writes the record after CheckWWSAccepted.
  - The page-level `postAuditLog` outbound was removed from newShellOrg, newShellOrgPattern and manageShellOrgStatus.
  - Assignable-role pages (assignableRoleManager, adminProvisioning, assignableRoleManagerMaintain, deleteAssignableRole) have no orchestration, so they still write via their own outbound.
- **Pages pass to every launch:** `changedBy` (selectedWorker.descriptor, urlEncoded), `changedByWid` (selectedWorker.id), and `timestamp` (`date:now().format("yyyy-MM-dd'T'HH:mm:ss'Z'")`, urlEncoded). Before this, the orchestrations had no timestamp or user.
- **Previous IORC_0037_XFD_SEC_Create_Application_Shell_Org / IORC_0037_XFD_SEC_Create_Pattern_Shell_Org audit writes never landed.** The template sent `"worker": "<wid>"` and `"application": ""` as plain strings to SINGLE_INSTANCE fields. Don't template SINGLE_INSTANCE fields as strings. Store WIDs in TEXT fields instead (`changedByWid`, `orgWid`, `roleWid`, `positionWid`).
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
- **Audit records for requests** save `positionWid` (comma-separated) next to `positionName`, so the Audit Log Viewer can link each position. IORC_0037_XFD_SEC_Close_Denied_Role_Request saves `positionWid` from the request's `positionWids` too. The viewer resolves role WIDs for the AAA role from `allAAArolesinTenant`; a requested role that doesn't exist in Workday yet stays text.
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
- `IORC_0037_XFD_SEC_Change_Shell_Org_Status` writes its audit record even when `validateOnly=true`, so validate-only can't be used for safe write tests until the audit write is made conditional.
- Full-suite test data uses short run-number names (`X:ADM:TEST:CI:RUN<n>`); don't reuse the old timestamp names such as `CI:2610302152` (user request).
- The test role for position add/remove is `X:BPMS(ODMT):ROLE:ADVISORS` (override with `--role`). Run 22 left **P-00001** assigned there because WQL hadn't shown the add yet; check and remove it by hand. The readback now waits 90 s.
- Stray org from a test bug: `COMS Application:PATTERN:TEST:TEST:302:152:2026W1` (a pattern named from the app's display name instead of `appId`). Still active; the app's status guard can't touch it (not an `X:` code) and no inactivate task was found in the tenant UI. Hidden from Shell Org Manager since the page only lists `X:…:PATTERN:` codes.

### IORC_0037_XFD_SEC_Change_Shell_Org_Status input guard (deployed and confirmed live 2026-10-30)

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
- IORC_0037_XFD_SEC_Create_Pattern_Shell_Org has a matching guard, `CheckPatternName`: the name must start with the COMS application's `appId` + `:PATTERN:` (test Guard.patternName).

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
- **IORC_0037_XFD_SEC_Change_Shell_Org_Status picks inactivate vs reactivate from `includeInactive`** ("true" = inactivate), **not from `action`**. `action` only goes into the audit record. Sending action=INACTIVATE with includeInactive=false reactivated 6 test orgs, cancelling their 2026-12-15 inactivations, and wrote INACTIVATE audit records.
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
- Request pages save a fixed `referenceId` (hidden `requestRefHidden`, set at page load) and then launch `IORC_0037_XFD_SEC_Start_Role_Request_Review` (outbound POST, `orchestration` base, `?ref=`). The orchestration finds the request by `referenceId` (now indexed), POSTs `/apps/<app>/v1/reviewCOMSAssignableRoleRequestEvents` with `businessProcessTarget.id`, and PATCHes `reviewEventWid` onto the request.
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
- **Deny handling (tested live 2026-10-30 via a Cancel pairing):** orchestration `IORC_0037_XFD_SEC_Close_Denied_Role_Request` (template "Workday Business Process", flow type `.maya.FlowBusinessProcessTriggered`, start `StartBusinessProcess`, end `EndEmptyMaya`, default credential `AccessTokenFromInitiatingUser` — JSON copied from Orchestration Builder → Settings → Open Current Source Code). It GETs the request, PATCHes `status: Denied, active: false`, and POSTs a DENY audit record.
  - Denied request WID: `bp.eventTarget().getIDValues("WID").get(0)`. `bp.eventTarget().toString("WID")` is in the docs but fails the build ("Wrong number of arguments for function toString").
  - Timestamp: `datetime.now("UTC").format("yyyy-MM-dd'T'HH:mm:ss'Z'")` (developer.workday.com "Reference: DateTime Global Functions" + LocalDateTime member `format`). `bp.*` functions: "Reference: Business Process Global Functions".
  - Tenant: definition related actions → Business Process → **Configure Orchestrations** → Add → Action Deny → Orchestration → Create Orchestration Launch Configuration ("ECO-COMS Deny Role Request", BP type Review COMS Assignable Role Request, no parameters).
  - The launch configuration can't be saved until the tenant-wide **Edit Tenant Setup – Business Processes → User to perform Orchestration Launches** is set. Set to lmcneil (user approved, 2026-10-30).
  - Workday says BP-triggered orchestrations usually launch within ~15 minutes; in practice they ran in about 2–3 minutes. Status: Find Events → Orchestrations tab.
  - **Deny is only offered while an approval is awaiting action.** When the initiator is in the approval group, approval auto-completes and only Cancel remains. So IORC_0037_XFD_SEC_Close_Denied_Role_Request is also paired with the **Cancel** action (Configure Orchestrations). A cancelled request is marked Denied with a DENY audit record; without this it would stay "Pending" forever.
  - The DENY audit shows position names: request pages save `positionNames` (TEXT, from the positions widget's `selectedEntries` descriptors) and the orchestration uses it, falling back to `positionWids`.
- **Current BP definition (user-edited 2026-10-30):** a Initiation → b Approval (Compliance Administrator) → c1 To Do "Add Assignable Role" → c2 To Do "Create Role Based Security Group" → d Action (EDIT page reviewRoleRequestAssignableRole, "Link Workday Role"). The old CreateSecurityGroup action step / reviewRoleRequestSecurityGroup page is unused.
  - Security group: Type of Tenanted Security Group = **Role-Based Security Group**, Name = the **full role name as-is** (e.g. X:ADM:ROLE:TESTROLE1035; user decision). Step d prefills the name with `request.securityGroupName ?? request.roleName`.
  - Compliance Administrator needs Deny / View All on the BP policy for the Deny button to appear. Saving that policy change was blocked for the agent (permission grant); the user does it, then Activate Pending Security Policy Changes.
- **Approval group must be able to resolve people (live 2026-10-30):** with step b set to "Accounts Payable Data Entry Specialist" (a *constrained* role-based group), TESTROLE1036's approval showed Awaiting Action with **All Persons = 0**. Confirmed: the app domain "Manage: COMS Assignable Roles" lists **Allowed Security Group Types: Public Groups, Unconstrained Groups** (View Domain page), because COMSAssignableRole has no organization context. Use a user-based group or the **(Unconstrained)** variant.
  - An approver needs the group in **three** policies: the BP security policy (Approve, Deny, View All), the domain **Maintain: COMS Assignable Roles** (secures the four step pages; on 2026-10-30 it held only HR Administrator + the deploy ISSG), and **Manage: COMS Assignable Roles** (the request data). Then Activate Pending Security Policy Changes. The agent may not edit security policies; the user does this.
- **Fixed (live 2026-10-30):** with "Accounts Payable Data Entry Specialist (Unconstrained)" on the BP policy (View All, Approve, Deny), both domains, and step b, TESTROLE1038's approval resolved **8 persons** (incl. James Walker). Real Deny then tested end to end: James Walker (proxied by the user) denied TESTROLE1038 at 13:30:17, IORC_0037_XFD_SEC_Close_Denied_Role_Request completed the same second, a DENY audit record was written and the request left the pending list. An in-flight request keeps its original routing; definition changes only affect new requests. Edit Definition shows a page error if a step's group isn't in the BP policy.
- **Self-approval blocked (2026-10-30):** step b → View Workflow Step → related actions → Business Process → **Maintain Advanced Routing** → Routing Restrictions → **Exclude Initiator** = Yes. The definition grid shows "Restriction: Initiator".
  - The review is started by IORC_0037_XFD_SEC_Start_Role_Request_Review running as the requester (AccessTokenFromInitiatingUser), so the initiator is the requester.
  - Per Workday docs (Business Process Step Types), if a restriction excludes everyone eligible, the step is marked **Not Required** and skipped. Consider an Alternate Security Group so a lone approver who is also the requester can't skip approval.
  - Not yet tested live. Testing needs a requester who is in the approval group, and temporarily swapping the step group was blocked for the agent (permission change).
- **Step help text:** definition related actions → Business Process → **Maintain Help Text** → pick the step → Edit Step Help Text → fill Help Text → OK → Done. Rewritten for all 5 steps on 2026-10-30 in one format: bold "Step N of 5: <name>" title (+ who does it), one-line purpose, bold "Check" / "How to" label with a bulleted list, then a bold "Next:" or "Outcome:" line. Step numbers match the "Step X of 5" banners on the ECO-COMS step pages. Example names use X:ADM:ROLE:EXAMPLE.
  - The Help Text cell is a plain textarea plus a **Format Text** button that opens a ProseMirror rich-text editor (bold, italic, underline, colour, bulleted list, link, email). No numbered list. Line breaks typed in the textarea are kept.
  - Agent technique: clear the *textarea* first (click it, ctrl+a, Delete; keys reach the textarea but not the ProseMirror editor), open Format Text, then dispatch a synthetic `paste` ClipboardEvent with `text/html` on `.ProseMirror`. Formatting is preserved. Then Done → OK.
- **Completion notification (2026-10-30):** definition related actions → Business Process → **Add Notification** → Create Workflow Notification: Trigger on Status = **Completed**, Recipients = **Initiator**, subject "ECO-COMS role request completed", short body. Completed only fires on the approve path (a deny ends with status Denied). Remove the empty Email Addresses row before OK.
- **Inbox titles:** `useForDisplay: true` on COMSAssignableRole `roleName` makes inbox items read "Review COMS Assignable Role Request: <role name>".
- **Orchestration Builder "Open Current Source Code"** (orchestration Settings page) shows the JSON without saving to App Hub — easier than Save + View Source. A stale App Builder session can be reset with ⋮ → Revert to App Hub.
- Browser pane tips: narrow window → Workday prompts open as full-screen pickers. Use resize_window 1600x1000 for BP grids. Related-action menus need hover to open sub-menus. Date fields need per-key input (`key "1 0 3 0 2 0 2 6"`).

## Open items (updated 2026-10-31)

- **P-00001 on ADVISORS: resolved.** `repair` dry run on 2026-11-01 09:20 PT: P-00001 is not assigned to X:BPMS(ODMT):ROLE:ADVISORS. Tests now use Pacific dates (`tenantDate`).
- **Demo reset (2026-11-01, for the 2026-11-02 demo):** e2e `purge-apply` deleted every audit log, bulk run, bulk row result and bulk upload record (6 + 1 + 16 + 6). `demo-seed` then wrote the three demo test cases, effective 2026-11-02: pattern X:CLW:PATTERN:CPSC:CPSC_V:110:101:2026W2; P-00001 added to X:BPMS(ODMT):ROLE:DEPTSTAFF; request X:CLW:PATTERN:CPSC:CPSC_V:110:101:2026W2:ROLE:TEACHINGASSISTANT (REQ-MVY4YVGS, review pending). The live finale adds P-00009 to STAFF through the bulk grid. Afterwards, P-00001 (DEPTSTAFF) and P-00009 (STAFF) can be removed and the request cancelled.
- **36 test orgs and patterns still active:** `cleanup-apply` on 2026-11-01 was rejected for all 36, for both 11-01 and 11-02 (no audit record within 20 s). Most likely each already has an inactivation scheduled (the full suite inactivates its orgs 45 days out; earlier cleanups scheduled others), and Workday allows one pending status change per org (unverified: check the app Logs or an org's history). To inactivate sooner, the scheduled events must be rescinded in Workday first.
- Role requests linked to a review event can't be deleted; about 40 old TESTROLE requests stay as Denied/Approved history.
- **Bug sweep (2026-11-01):** fixed: review step pages showed blank Positions (looked up in the first 100 staffing jobs; now use stored positionNames); Home hub "Needs My Attention" ignored grid bulk runs (now reads comsBulkRuns too); unused `jobs` calls removed from ISC Queue and Delete Assignable Role. Confirmed fine: WQL with no limit returns every row (608/608 orgs, 829/829 positions; smoke check `WQL.noLimitReturnsAll`). **Open:** IORC_0037_XFD_SEC_Create_Application_Shell_Org and IORC_0037_XFD_SEC_Create_Pattern_Shell_Org don't write `orgWid` to their ADD audit record, so those rows have no org link in the Audit Log; needs the new org's WID from the Add_Update_Organization response (left until after the demo). New checks: `Static.cappedLookup`, e2e task `datacheck` (records missing a field a page displays; old TESTROLE records predate denialReason/securityGroupName/Enabled For).

- `IORC_0037_XFD_SEC_Close_Denied_Role_Request` did not run once (TESTROLECIRUN22, 2026-10-30); it has run every time since. Keep an eye on it after deploys that change it.
- The two older pending requests (KEYCLOAK COORDINATOR and the AAA request) were corrected on 2026-10-31 with `node test/run-tests.js repair --apply`: Enabled For now reads "Faculty of Medicine" (FUH), with the WID in `enabledForWid` / `functionalUnitHierarchyWid`.
- P-00001 was removed from X:BPMS(ODMT):ROLE:ADVISORS on 2026-10-31 through the Manage Role Assignments page (REMOVE POSITION audit at 18:58:57Z). The same removal sent by the test runner was refused by the API gateway (HTML 403); the page's request went through.
- **ISU lockdown is now a script, `tools/isu_writes.py`** (2026-11-01), not a long-lived branch: the old `isu-writes` branch was one commit 61 commits behind main. Branch `isu-writes-v2` = main + the script applied (SMD `isuAuth` + `authType: isuAuth` on the 9 page writes to comsAssignableRoles / comsAuditLogs). Once the ISU is assigned to the app in App Manager: merge `isu-writes-v2` (or run the script on main), deploy, run `node test/run-tests.js isu`. `--undo` reverts. Old `isu-writes` kept untouched for reference.
- The stray org "COMS Application:PATTERN:TEST:TEST:302:152:2026W1" is still active (hidden in the app). Logan McNeil has no inactivate action on it in Workday (related actions only offer view tasks), and IORC_0037_XFD_SEC_Change_Shell_Org_Status rightly refuses codes that don't start with X:. Someone with organization maintenance rights must inactivate it in Workday.
- ISU lockdown (`isu-writes`): App Manager → Configure for the app shows no ISU assignment, and a search for DNU_ISU_ECO_COMS_DEPLOY_CMM finds nothing for Logan McNeil (2026-10-31). Not merged; see ADMIN-RUNBOOK section 3 for the setup steps.

## After UI phase 2 (2026-10-31)

- Manage Role Assignments: OK now goes to `roleAssignmentSuccess` (flow `editRoleAssignmentFlow`), with Back to Shell Org Manager for the same application. Cancel keeps `appCode`/`appName`. Deployed; not yet seen live (needs a real change).
- Home: **Needs my attention** card (`MyAttentionCard`), checked live: "6 pending ISC review · 3 approved this month · 30 denied or withdrawn | No bulk uploads running". No separate My Requests page: Assignable Role Manager already lists the user's own requests with Withdraw.
- Bulk Role Changes: position lookup, Apply button, Refresh; real runs tested live (see BULK-ROLE-ASSIGNMENT-DESIGN.md).
- Built 2026-10-31 (commit "Org detail page, request again, ..."), **not deployed yet**: the deploy failed at the token step (WD_DEV_TOKEN expired). Static checks pass.
  - `shellOrgDetail` page + Details buttons on Shell Org Manager (`tools/build_org_detail.py`); active orgs listed first.
  - Request again / Request similar on Assignable Role Manager → `assignableRoleManager?againRoleName=...&againFrom=...&againStatus=...&againReason=...` prefills the role name and shows a note. Only the role name is prefilled, on purpose: org, positions and date drive the onChange logic that builds the generated name.
  - "Nothing to show" notes on empty grids (`tools/add_empty_messages.py`, re-run by `build_bulk_pages.py`).
  - To check after deploy (read-only): open Shell Org Manager → Details on an org; open Assignable Role Manager → Request again on a denied row (check the note and prefilled name, then Cancel); filter ISC Role Requests to a status with no rows and see the note.
  - Not built: flagging future-dated org status changes (no data source for org events in the app's WQL).

## UI polish pass (2026-10-31, all deployed)

Builders/scripts: `tools/build_filter_pills.py` (filter pill cards, Home actions, Shell Org Manager summary, error page), `tools/build_request_lists.py`, `tools/consistency.py` (titles, back links, headings, help text size, timestamps, icons, success pages), `tools/add_empty_messages.py`. Static checks added: one empty message per grid, at most three cards per grid row, titles start with "ECO-COMS: ".

Fixed: Audit Log and ISC filters as pill cards; Home actions as cards; donut total showed the pattern count (392) instead of organizations (213); Shell Org Manager summary ignored the selected application; bulk ADD audit rows had no position WID and the CSV's name (now Workday's name and WID); duplicate empty messages; stale "above" help text; '1 rows'; four-card rows wrapping; mixed timestamp formats, titles, back links, headings, icons, warning headings, success page layouts.

### Decisions (product owner, 2026-10-31 evening)

1. **ISC landing page retired.** `iscRoleRequestsHub` and its card are gone; Home, cards and the queue's back link go to `iscRoleRequestsView` / Home. The Workday menu task (`model/ISCRoleRequestsView.task`) already opened the queue.
2. **Headings in Title Case** (my choice, as asked): it was the majority style and matches Workday's own pages. `tools/title_case.py` applies it to pages, cards and builders; static check `headingCase`.
3. **BP step pages keep their Workday-style titles** (no "ECO-COMS:" prefix).
4. **Old bulk audit records corrected** (`Repair.bulkAuditPosition`, e2e repair-apply run 41267556360, 2026-11-01 ~03:05 UTC): the REMOVE record (21:09:07) got Workday's name "P-00010 Director, Payroll Operations - Beth Liu"; the ASSIGN record (21:11:38) got WID aa1562e7…, now a link. The two WIDs differ on purpose: ADD stores the `allPositions` workdayID, REMOVE the role assignee's WID, exactly as the single-change page does.
5. **No Retry/Reuse for AAA requests** (my choice, as asked): every AAA form field is driven by the Application dropdown's onChange, so a prefilled form would submit without a generated role name; the button could only show a note. AAA requests are rare (one so far).

### Live tests (2026-11-01 01:29–01:31 UTC, approved)

- Manage Role Assignments: removed P-00010 from X:BPMS(ODMT):ROLE:ADVISORS (effective 2026-10-30). OK led to the new confirmation page with role, organization, "Positions removed: P-00010 …", date; Manage This Role Again reopened the role.
- Bulk real run added P-00010 back with an **empty** Position name cell: the audit record has Workday's name and is a link (position WID filled). The role is back to P-00009, P-00010, P-00011, P-00139, P-00759.

### Found in the page review (deployed 2026-11-01 ~03:00 UTC)

- Withdraw page: five request columns were blank for every row (literal instanceList on an EDIT page); now text. Static check `editInstanceList`.
- Shell Org Manager: Applications list now includes applications that have shell orgs but no patterns (X:BPMS(ODMT) couldn't be opened before); banner wording; one warning glyph.

### Live review 2 (2026-11-01 ~03:10 UTC, after the token refresh)

Script: `tools/polish.py`, idempotent; every builder now runs it last. Static checks `gridCount`, `aboutInfo`.

- Home: card subtitles were cut off with "…" (two lines fit about 40 characters); all shortened. "Pending ISC Requests" wrapped; now "ISC Queue". The Role Requests action card dropped its "Open ISC Queue" pill (the ISC Queue card has it).
- Donuts: centre read "213 orga…" (now just the number); slice labels read "2 (0.939%)" (`showPercentLabels: false` now shows counts only).
- Shell Org Manager Summary: the count cards and the Quick Actions/chart row are one masonry container, so no half-empty rows at any width. Manage Role Assignments tab got an "About This Tab" box like the other tabs.
- Grid labels no longer repeat the count ("Applications (31) 31 items").
- Audit Log: actions in sentence case ("Assign position"), matching the chart legend; the Changes by Action chart moved in beside the filters it reflects.
- ISC queue: its unlabelled intro box merged into About This Page, which now comes first, as on the other list pages.
- "Admin Provisioning" in page text renamed to the page's own name, AAA Role Provisioning. Bulk results card "Need attention" → "Need Attention". ⓘ on every About text.
- Needs My Attention splits pending requests into assignable and AAA when there are AAA ones ("Open My Requests" shows assignable only); its ⋯ menu gained Open My AAA Requests.
- AAA request form: it was copied from the assignable form and still said "Submit New Assignable Role Request", "Pending Assignable Roles" and "Submit and manage Assignable Role requests"; now AAA wording. Both forms' intro text is in an About This Page box.
- Headings: FUH page "About FUH Administration", bulk "How It Works" / "How to Use This Template" → About This Page, like every other page. Org detail help text names the real button (Inactivate Organization).
- **Product owner, 2026-11-01:** timestamps shown in Pacific time to the minute ("2026-10-31 18:31 PDT"; `formatDateWithTimeZones` with pattern `z`, so PST after the change back), and page names match the buttons that open them: Assignable Role Manager → **My Assignable Role Requests**, AAA Role Provisioning → **AAA Role Requests** (it lists everyone's AAA requests), Pending Role Requests (ISC) → **ISC Queue – Pending Role Requests**. Workday menu tasks renamed too: Submit Assignable Role Request, Submit AAA Role Request, ISC Queue (search for the new names).
- **Review 3 (forms, wizards, confirmation pages):** wizard subtitle "Create New Shell Organization" → "Add New Shell Organization" (matches the step page and Home's Add Shell Org); pattern page "New Shell Org Pattern" → "Add New Shell Org Pattern", the "CO naming structure" jargon reworded, and its Application/preview fields got a Pattern Details heading; status page "Impact of Activating" → "Reactivating" (the action is Reactivate), no "Warning:" after ⚠; Withdraw page title and list heading follow the request type (`view=aaa` → "Withdraw AAA Role Request"); pattern confirmation said "The Custom Organization has been created" → "The pattern has been created"; role-assignment confirmation names the actions as the Audit Log shows them; Title Case field labels on the bulk Apply and role-assignment pages; step 5 help points to the ISC Queue. The unused reviewRoleRequestSecurityGroup page (old step 3) still says "Step 3 of 5"; left as is.
- **In-platform test (2026-11-01, every page):** all 31 tasks load in Workday with real parameters (crawl of every link and button address: 52 variants, all 200, no page errors; 60+ cards checked; 34 pages opened in the browser, no error banner). Fixed: Withdraw opened from Workday search (no view) listed both kinds under an "Assignable" title (now neutral "Withdraw Role Request"); ISC Queue help named the list pages as where requests come from; pattern confirmation said "submitted via the orchestration"; **Add New Shell Org Pattern** kept a stale preview while a field was invalid, and choosing the application cleared errors without re-checking what was typed (lowercase `math` slipped through until OK). Submit Assignable Role Request had an empty box above About This Page: the hidden "Requesting again" note sat in its own section; it now lives in the About box (static check `Static.hiddenSection`). Form behaviour checked live without submitting: pattern form (no-app error, preview, re-check), Add Shell Org (name preview, weekend date error once you leave the date field). Link Workday Role (reviewRoleRequestAssignableRole) tested 2026-11-01 with a step id from smoke step `BP.inProgressStep` (`GET /events/{id}/inProgressSteps`): loads the right request with the security group prefilled, no error banner. The other two step pages were loaded live with a real event id and render the request. TESTROLE1031 and TESTROLE1032 showed a bare position WID in Positions (saved before Position Names existed); `Repair.positionNames` filled both with "P-00013 Director, Accounting - Sara Goldstein" (2026-11-01). Test position P-00001 (left on X:BPMS(ODMT):ROLE:ADVISORS by run 41270107832's UTC-date ADD) was removed through Manage Role Assignment, effective 2026-11-01; ADVISORS is back to P-00009, P-00010, P-00011, P-00139, P-00759 and the Audit Log has the Remove position record. A test-runner launch of the same removal got the gateway's HTML 403; the page went through.
- The Home hub's own address is the app root (`…/ecocomsphase_xclw_cm_sync2_vmzvxm.htmld`); `…/home.htmld` gives "Route not matched".

## UI phase 2 (built 2026-10-31)

Design: `docs/UI-PHASE-2-DESIGN.md` (with the product owner's answers). Built and checked live in the tenant:

- **Home (hubLanding):** count cards (pending + overdue requests, active shell orgs, audit changes in the last 24 hours) and the Shell Org Overview donut. The nav cards PendingIscCard, ShellOrgCard and AuditLogCard take a `countText` parameter.
- **ISC queue (iscRoleRequestsView):** `?status=` filter buttons (Pending default, Approved, Denied, All) combined with `?view=`; Pending / Overdue / Approved this month cards (`CountCard`); "· overdue" on rows pending more than 3 business days. Logic in `scripts/comsRequestStats.script`.
- **Audit Log Viewer:** `?period=` (all, 24h, 7d, 30d) and `?changeType=` buttons, a "Showing N of M" line, the AuditActionChart donut, Excel export. Loads the newest 500 records (count + 5 offset pages). Logic in `scripts/comsAuditFilters.script`; periods compare timestamp text with the hours/days in the period (no date parsing).
- **Request pages** read up to 300 requests (count + 3 offset pages); the collection API returns oldest first.
- **Request summary cards** on adminProvisioningView and assignableRoleManagerView; a **Review Process** link column replaces the old Maintain buttons.
- **Legacy Maintain page retired** (assignableRoleManagerMaintain page, AMD task and model task deleted). Every pending request has a review event (smoke check Requests.pendingHaveEvent).
- **IORC_0037_XFD_SEC_Close_Denied_Role_Request** copies the review event's comment (`GET events/{id}/comments` → `$.data[0].comment`) into the request's `denialReason` and the DENY audit details.
- **New Shell Org:** weekday + this-year-or-next check (comsValidations), "Before you submit" live-org notice (also on New Pattern). Success pages show a receipt card from the user's newest ADD audit record.
- Shell Org Manager: About-this-tab notes, row counts in grid labels, empty-state messages that render (text widgets), unused include removed.
- Error page: clearer 403 text, extra links on 404.
- Orphans deleted: landingPage, iscErrorPage, AppContextCard, StatusGuideCard, QuickLinksCard, MyRoleRequestsCard, AdminProvisioningCard, comsCardGenerator.script.
- IORC_0037_XFD_SEC_Assign_Remove_Role_Positions: a Continue on Conditions step `CheckMode` (mode ADD/REMOVE; roleId, orgId, positionId required).

## DENY audit names the actor (2026-10-31)

IORC_0037_XFD_SEC_Close_Denied_Role_Request: `actorWid = bp.initiatingPerson().getIDValues("WID").get(0)` (a Person WID) → GetActor `GET /person/v4/people/{actorWid}/preferredName` → ExtractActor `$.data[0].descriptor` (fallback "Workday user") → audit `triggeredBy` = name, `changedByWid` = Person WID (the viewer's link resolves it). The full suite's Request.reviewCancelDeny asserts the name. Not yet tested with a canceller who isn't the requester.

## 2026-11-01: Bulk edits in the app, Excel template download, deck

- **Excel template download (live in dev):** Download Template shows "Excel Template", the newest COMSBulkTemplate record, built by `tools/publish_template.js` (WQL allShellAssignableRolesinTenant → `tools/build_bulk_xlsx.py --data` → multipart POST to comsBulkTemplatesCollection). Pre-filled with every current assignment, validated (ideas from the Mass Student Appointment Studio template). Refreshed after every deploy (deploy.yml, warning only) and on demand (e2e task `publish-template`). Upload New Template Version page for tenants without the pipeline. Download checked: same bytes, xlsx content type.
- **Cap:** product owner: no 200 cap for files. IORC_0037_XFD_SEC_Bulk_Role_Changes_From_CSV now rejects a file with more than 1,000 ADD/REMOVE rows (safety limit: 60-minute production process limit); unchanged rows don't count.
- **Bulk Edit Role Assignments (bulkRoleGrid):** EIB-style grid. Picker of applications (from the WQL data), Current Assignments (Remove checkboxes), Positions to Add (role/org drop-down + position search via onSearch on a deferred WQL endpoint). OK writes COMSBulkRun + one DRAFT row per change (comsBulkRowResults, batchRef <ref>-DRAFT) and launches IORC_0037_XFD_SEC_Bulk_Role_Changes_From_Grid (same builder as IORC_0037_XFD_SEC_Bulk_Role_Changes_From_CSV, reads the drafts). 50 changes per submit (60-second page limit). Results and Apply pages list grid runs too. Live-tested 2026-11-01: picker, grid load (7 rows), add row, role/org options, position search; a values-scripted drop-down's `.value.id` raised "Property Error found: id" (now `selectedEntries[0].id`).
- **Cleanup 2026-11-01:** 6 pending TEST reviews cancelled, 45 test audit entries deleted. All 36 test-org inactivations reported "not changed"; one org also refused a 2026-11-04 date, so an inactivation dated 2026-11-02 from the first attempt is likely already scheduled (its audit record was deleted by the same run). Check scheduled for 2026-11-03 08:40 PT. Cleanup now prints the real launch error.
- **Presentation:** "ECO-COMS: Role Access, Simplified" (Slides artifact, 19 slides with speaker script).


## Solution architect's requirements (briefing transcript + current architecture diagram, received 2026-11-01)

- Shell roles: Workday role assignment = assignee (position) + assigner/context (shell org X:«code»:ORG:…) + assignable role (X:«code»:ROLE:…). "Shell" = no security group, so no power in Workday; assignments are extracted to AccessUBC and pushed to target apps (Clockwork, OAMS, … AWS next). Must-have: deprovision on position vacancy; nice-to-have: replacement gets access automatically.
- COMS objectives: (1) exit Appian; (2) learn Extend on a low-change-management app. Purpose: delegate shell org creation (bounded by org type X:«code», subtype X:SHELL) so Clockwork-style teams don't file ISC tickets each term. Rebuild "the right way": schema per application (Clockwork 5 columns, others e.g. 7) with validation. Shell orgs are add-only in meaning (no change once a role assignment depends on them). Little local data model: orgs live in the custom org hierarchy.
- Phase A: move COMS off Appian (built in dev; Clockwork form is hand-built, `patternSchema` on COMSApplication unused so far). Phase B: delegate shell assignable roles (today: request + ISC review). Phase C: contextual shell role assignments so a AAA sees only their app's roles (ISC's concern: in the standard task a AAA sees all roles on a position and can request deletion: "two errors"). Proposed: scope by the user's own AAA meta role assignments (role on meta org X:«code»); later a COMS API for automation (AWS).
- Open: check whether Workday has improved custom org security since shell roles were designed.

## 2026-11-02: Schema-driven patterns for every application; org subtypes

- Source: Requirements/Application Patterns.xlsx and the product owner's answers (Instructions.docx): load every application on the sheet (the "TBC" summary table too), ignore typos, leave Clockwork's form as is, ignore Academic Unit for now, blank field = `*`, create no example orgs.
- **Schemas** live in `tools/pattern_schemas.json` (14 applications) and on each COMSApplication record (`patternSchema` JSON, `namePrefix` = allowed prefixes, comma-separated). Seeded with e2e `seed-apps-apply` (2026-11-02: 14 created; X:CLW untouched, no schema). Adding an application = add it to the JSON and rerun seed-apps.
- **Page** `newSchemaPattern` (builder `tools/build_schema_pattern.py`, script `comsPatterns.script`): without `?appCode` lists every application code (Workday X: orgs + records) with its format; with one, shows up to 7 generic fields whose label (`dynamicBinding-String`), placeholder (`stringScript`) and visibility come from the schema via `json:parse` (developer.workday.com "parse (jsonString)"). Clockwork's form lists only records without a schema.
- **Server** (`tools/patch_pattern_orchestrations.py`): IORC_0037_XFD_SEC_Create_Pattern_Shell_Org checks prefix ∈ namePrefix (blank = PATTERN), field count = number of `fieldLabel` keys in the schema, upper case, no spaces. No regex in Orchestrate (developer.workday.com "Reference: String Member Functions" has none), so field formats are checked on the page only.
- **Subtypes:** Add Pattern sends X:SHELL; Add Shell Org has a pick-list (X:META / X:SHELL, default and fallback X:META). `Organization_Add_Update`'s `Organization_Subtype_Reference` accepts only `Organization_Subtype_Name` (v47.0 Human_Resources XSD, checked 2026-11-02), so the reference IDs ORGANIZATION_SUBTYPE-17-41 (X:META) / -17-42 (X:SHELL) can't be sent there.
- Tenant facts (probe 2026-11-02): no X:SET or X:PHA orgs/types (Workday has X:BPMS(SET)); no course-subject data source; every X: org has subtype X:SHELL; WQL field for subtype is `subtype`.
- `pattern-guard` (e2e) launches 3 valid and 6 invalid names with effective date 2026-02-30 so nothing can be created; per-launch outcome is in the app Logs (developer site). 2026-11-02 run: nothing created; log check pending.
- Shell Org Manager's Application Patterns tab (2026-11-02, product owner): lists only applications with a pattern format (records with patternSchema, plus X:CLW); an application's patterns are its orgs whose next part is one of its namePrefix values (X:CLW keeps `:PATTERN:`). Its About text describes the per-application format.
- newSchemaPattern first deploy failed at page load: "Unknown Variable found: patternField1Text.value" in the preview's value, which read fields declared further down. Fixed (preview starts from empty values); `Static.forwardRef` now warns on load-time references to later widgets. A reference inside an unevaluated ternary branch is fine (the Clockwork form's preview).
- **Title tiles (2026-11-02, product owner):** 25 pages show a white rounded tile with the title in blue instead of Workday's square blue banner (`tools/title_banner.py`, last step of rebuild_all; `--restore` first step, titles kept in `tools/page_titles.json`). Not converted: the two editWizard containers, their steps (newShellOrg, newShellOrgPattern) and the four ISC review step pages (they open in the inbox). Trade-off: those pages' browser tab reads "Workday - Workday". Checked live: hub, Shell Org Manager (scripted title "– X:ADM"), Audit Log, Add Pattern.
- **Clockwork on the shared pattern form (2026-11-02, product owner: "should not have a dropdown and match all applications"):** X:CLW now has a patternSchema in `tools/pattern_schemas.json` (prefix PATTERN; Academic Unit, Subject, Course, Section, Academic Period, all blank = `*`), from the sheet's CLW-SO rows. Its five columns give the same names as the existing Clockwork patterns (e.g. `X:CLW:PATTERN:MATH:MATH_V:303:951:2026W1`) and match the request record's attribute1–5 labels. Every Clockwork link (Home, Quick Actions, ShellOrgCard, SOM Add Pattern) opens `newSchemaPattern?appCode=X:CLW`; "Add Another Pattern" opens the application picker. The old wizard (createShellOrgPatternWizard + newShellOrgPattern) was deleted from the app. seed-apps now updates an existing record's namePrefix and patternSchema only (X:CLW keeps its hand-set name, org type and subtype). Academic Period is checked by format only (the old form allowed only this year and next; the sheet's examples use 2024).
- **Back links in the About box (2026-11-02, product owner):** on the 17 pages where the back links (← Home, ← Shell Org Manager, ...) sat in their own box directly above the About box, they now sit at the top of the About box, above "About This Page" (`tools/merge_nav_about.py`; `--restore` first in rebuild_all, merge just before title_banner; pages listed in `tools/nav_merged.json`). Success pages keep their links at the bottom; Shell Org Manager (tabs) is unchanged.
- **One grid format (2026-11-02, product owner):** `tools/grid_style.py` (after polish in rebuild_all) gives every read-only grid the list look (`gridType: LIST` + `multiViewStylingEnabled`), sortable/filterable columns except button columns, autoPaging + Excel export on VIEW pages, and doNotAdd/doNotRemove on EDIT pages (adminProvisioning, assignableRoleManager and deleteAssignableRole grids could show +/- icons before). The two editable grids on Bulk Edit (Current Assignments, Positions to Add) keep the spreadsheet look. `enabled` is left alone so related-action links keep working.
- **Application grids match (2026-11-02, product owner):** Add Pattern's picker, Shell Org Manager's Application Patterns tab and Bulk Edit's picker use the same columns from `tools/app_grid.py`: Application ID (link), Name, Pattern Format (not on Bulk Edit), then the action button (Add Pattern / Manage / Edit). Bulk Edit gained a comsApplications endpoint for the names. `grid_style.py` also puts action-button columns last on every grid (Withdraw's column was first; link buttons that name the row stay put).
- **Grid headers (live 2026-11-02):** in a list grid, an unsortable column's header is drawn lower than a sortable one's, so a grid mixing them looks ragged. Workday sorts only text-type columns (aria-sort is absent on button and fieldSet headers whatever sortableAndFilterable says), so that can't be fixed per column; the three application lists (appPickGrid x2, appsGrid) have no sorting so their headers line up (product owner's choice), longer grids keep sorting and the offset. EDIT pages draw grids with cell borders and VIEW pages without; that follows the page type, not grid attributes.
- **Application list on its own page (2026-11-02):** the Add Pattern application list moved from newSchemaPattern (an EDIT page, where grids get cell borders) to the VIEW page `schemaPatternApps`, so it looks like Shell Org Manager's list. Add Pattern (Other Apps), Add Another Pattern and "Choose another application" open it; newSchemaPattern without ?appCode shows a "Choose an Application" button.
- **Bulk Edit application list on its own page (2026-11-02):** same change for Bulk Edit Role Assignments: the list moved to the VIEW page `bulkRoleGridApps` (Application ID link, Name, Edit); every "Edit in the App" link opens it. The two editable grids stay on bulkRoleGrid (EDIT), so they keep cell borders. Button columns in exported (VIEW) grids get `"excel": {"enabled": false}` on the column (grid_style.py), which App Hub requires.
- **Edit Role Assignment (2026-11-02):** the one-row Current Assignment grid became three read-only fields (Role, Organization, Current Positions) in a "Current Assignment" box. Form-page grids always draw as bordered tables with 12px text (checked live: same cell styling as every other EDIT-page grid), so a single record reads better as fields. Bulk Edit's Current Assignments keeps its grid (Remove checkboxes).
- **Template page shows one version (2026-11-02):** the attachment collection `comsBulkTemplates` returned every version despite `limit=1&offset=total-1`, so the page listed all ~20. The endpoint now reads the newest 100 and the loop shows `list:sort(data, 'asOf', false).subList(0, 1)` (checked live: one row, the newest).
- 2026-11-02: Added the COMS Worker Profile section (profile group + two context-free tasks, domain ViewCOMSProfileGroup) and two Home cards (myRoleRequestsCard, iscQueueCard). Collapsible About boxes on bulkRoleChanges, bulkRoleTemplate and newSchemaPattern (tools/collapse_about.py). Admin steps in ADMIN-RUNBOOK §3c.
- 2026-11-02: **Insights** page (`comsInsights`, builder `tools/build_insights.py`, script `comsInsights.script`, card `BreakdownChart`) in the hub. The four reports (AcademicUnits, AllAssignableRoles, AllAuditLogs, AllShellOrgs) were replaced by COMSRoleRequests, COMSAuditTrail, COMSBulkRunHistory and COMSApplicationSetup (product owner's choice). Deployed (run 41535796471); not yet opened live (computer offline). Custom reports in the tenant built on the old data sources need pointing at the new ones.
- 2026-11-02: Updated UI recommendations PDF for review (status of every October item + 10 improvements).
- 2026-11-02 (evening): **UI recommendations 1–8 built** (`tools/ux_improvements.py`, two steps in rebuild_all) and checked live: helpText on 4 fields; ISC Queue Waiting column + oldest first (Pending); empty-state buttons (My Requests, AAA); About boxes collapsed on ISC Queue, Audit Log and Shell Org Manager tabs, with a summary line under the title tile; Bulk Edit change counter (live: "1 removal and 0 additions ready"); View in Audit Log on the 3 receipt cards; Audit Log Last 90 days + Application column; ISC Turnaround card on Insights ("Median 0 days · 3 approvals"). Not built (tenant configuration, for the product owner): Denied/Withdrawn notifications, turning on the profile section and Home cards.
- 2026-11-02: Insights opens from an **Insights card on the RBAC Hub** (product owner), not a left-panel item. First deploy failed live with the PMD script memory limit in Applications at a Glance (per-org maps over ~1,000 orgs); fixed by sorted code lists + indexOf/lastIndexOf counts. Request application codes fall back to the shell org code or role name.
- Home cards checked live 2026-11-02: My Role Requests "3 pending ISC review · 0 approved this month"; ISC Queue "3 waiting for review · oldest requested 2026-10-30".
- 2026-11-02 tenant configuration (product owner approved items 9–10):
  - **Notification added** to Review COMS Assignable Role Request (Default Definition): Trigger on Status = Canceled, Denied, Rescinded; Recipients = Initiator; subject "ECO-COMS role request closed"; body points to My Assignable Role Requests and Request again. Effective 2026-11-02. The Completed notification is unchanged.
  - **COMS for Worker Profile:** Display in Profile = Yes (App Manager → Configure → Profile Groups). Not visible on Logan McNeil's profile yet: the View: COMS Profile Section domain isn't granted to any group (product owner's step).
  - **Home cards not placed:** Workday Home doesn't accept `.carddefinition` cards (see CLAUDE.md, Extend Cards). Options: put them on a delivered hub via Maintain Hubs, or rebuild as Workday Home Card orchestrations.
- 2026-11-02 Insights polish (commit pushed; deploy waiting on WD_DEV_TOKEN): AAA requests with a short application code ("AOC …") grouped under the matching X: application by name; application names fall back to the application's own organization; Approved card reads "n approved".
- 2026-11-02: **True Workday Home cards blocked.** Product owner asked for them. Orchestration Builder (Create Orchestration for this app) doesn't offer the Workday Home Card template, and the External Card route needs Workday Journeys + People Experience + Set Up/View: Custom Card policies (doc.workday.com "Steps: Create External Home Page Cards"); Workday also plans to retire External Cards for Journeys. Nothing was created in App Hub or the tenant. Needs: confirm Journeys with the Workday account team / tenant admin, then build two Home Card orchestrations (My Role Requests, ISC Queue).
- 2026-11-02: Product owner confirmed **Journeys is licensed in production**. Rechecked Create Orchestration for this app in the dev tenant: still only Synchronous, Asynchronous, Workday Business Process, Workday Integration System (no Workday Home Card template). Next step is with the tenant admin / Workday account team: turn on People Experience and the Journeys functional area in ubc_wcpdev2 (or name a non-production tenant that has them) so the template appears; then build IORC_0037_XFD_SEC_My_Role_Requests_Home_Card and IORC_0037_XFD_SEC_ISC_Queue_Home_Card orchestrations.
- 2026-11-02: **Home cards built on the code side** (product owner: "create everything on code end of things"). `tools/build_home_cards.py` (in rebuild_all) writes `IORC_0037_XFD_SEC_My_Role_Requests_Card_Data` (domain ManageCOMSAssignableRoles; GET workers/me, then `comsAssignableRoles?limit=100&requestedBy=<wid>`) and `IORC_0037_XFD_SEC_ISC_Queue_Card_Data` (domain MaintainCOMSAssignableRoles, now `enabledForOrchestrationSecurity: true`; first 100 requests, oldest pending date). Both return `{title, subtitle, linkText, linkPath}` through an EndSync DataRefBody from a CreateTextTemplate (shapes cloned from Workday's salesCommission sample, flowVersion 3.3.0, whose node keys match our 3.7.0 nodes). Smoke tests HomeCards.myRequests / HomeCards.iscQueue compare the counts with the REST data. The script also wraps them as Home Card orchestrations once `tools/home_card_template.json` is captured (ADMIN-RUNBOOK §3c). **Not yet deployed (token expired); unverified until the App Hub build:** a set EndSync body in flowVersion 3.7.0, `arrayAtJsonPath` with a `[?(@.status == '...')]` filter, `.toString()` on Json and Number, `.length()`, `.replace`, `.truncate(10)`, `stringAtJsonPathWithDefault` on a Json array.
- 2026-11-02: Card-data orchestrations **pass the App Hub build** (after making the EndSync contentType an expression). Tenant deploy then failed with 401 "The supplied authentication is invalid" at the AOS deploy: the tenant token needs refreshing too. HomeCards.* smoke tests not run yet.
- 2026-11-02 (late): **Everything deployed** (deploy run green after the token fix; the secret had been pasted with its quotes, now stripped in CI). Card-data orchestrations verified by smoke: My Role Requests "3 pending ISC review · 3 approved", ISC Queue "3 waiting for review · oldest requested 2026-10-30" (counts by text; the filtered arrayAtJsonPath failed at run time). Smoke: 31 passed, 1 skipped. Still waiting on the Workday Home Card template (People Experience + Journeys in the tenant).
- 2026-11-02 (night): **Workday Home Card orchestrations written in code** (`IORC_0037_XFD_SEC_My_Role_Requests_Home_Card`, `IORC_0037_XFD_SEC_ISC_Queue_Home_Card`, from `tools/build_home_cards.py`), since the product owner pointed out Home Cards work in WCP dev tenants without Journeys. Create Orchestration still doesn't list the type for this app, so the shapes come from Orchestration Builder's own schema; the uploaded files open in the builder as Home Card flows. First build: two fixes (card output is `.card`; no security domain). The fixed build is waiting on a token refresh (WD_WCP_TOKEN expired). After deploy: Create External Card in the tenant for each.
- 2026-11-02 (late night): **Home Card orchestrations live.** After deleting the broken copies in Orchestration Builder, GitHub uploads (system user isu_isc_extend) started failing with only "Unable to upload app. Error", even for the app without the Home Card files (diag branch `diag-upload`, to delete). Uploaded and deployed by hand instead (`wdcli app upload` from the repo files, then `wdcli app deploy`): App Hub build succeeded 4:59 PM Pacific with all 13 orchestrations, including IORC_0037_XFD_SEC_My_Role_Requests_Home_Card and IORC_0037_XFD_SEC_ISC_Queue_Home_Card. Smoke 31 passed, 1 skipped (HomeCards: "3 pending ISC review · 3 approved"; "3 waiting for review · oldest requested 2026-10-30"). Open: why CI uploads are refused; next step in the tenant is Create External Card for each card.
- 2026-11-02 (night): **CI deploys fixed** with a `.wdignore` (uploads only appManifest.json, cards, model, orchestration, presentation). Cause of the refusals: the repo root upload included `brand-assets/` (30 PNGs; App Hub allows 20 images per app) and other non-app files. Run 41560296764: upload, build, deploy and smoke all green (31 passed, 1 skipped). Home cards now show the count in the title, the oldest pending role and date, and state-dependent links ("ISC Queue · 3 waiting | Oldest: X:ADM:KEYCLOAK:ANY:ROLE:COORDINATOR · since Oct 30 | Review Now"). The `diag-upload` branch can be deleted.
- 2026-11-02 (night): **Icons from one table** (`tools/apply_icons.py`, runs last in rebuild_all; framework in CLAUDE.md "Icons"). Hub title `credentials`; nav RBAC Hub `wd-icon-contact-card-matrix-manager`, FUH Administration `wd-icon-folder-close` (they had `wd-accent-*`, which isn't allowed on navigation items, and `wd-accent-home`, which doesn't exist). Cards: role requests `id-badge`, ISC queue / Needs My Attention `inbox`, shell orgs `building`, bulk changes `people-group`, audit `scroll-shield`, Insights `chart-bar-arrow`, counts `sigma`, status pills `gauge`, period pills `calendar`, receipts `award-medal`, error page `data-refresh` / `resources`. Static check `Static.icons` fails on any other name.
- 2026-11-02 (night): RBAC Hub's Shell Org Overview donut replaced by **App Activity** (`AppActivityChart`, stackedBarChart2, built by `tools/build_activity_chart.py`): changes per day for the last 7 days split into Shell orgs (Shell Org, Pattern, Org Status), Role assignments, Role requests (Assignable Role), from `auditPage0` (newest 100 audit records) via `comsAuditFilters.activityByDay`. Footer opens the Audit Log at 7 days. Chart cards got icons too (AppActivity `time`, AuditActionChart `scroll-shield`, BreakdownChart `chart-bar-arrow`, ShellOrgStatusChart `building`). First stacked bar in this tenant: check it renders after deploy.
- 2026-11-02 (night): **Deploy values for the CLAUDE.md "Deploy decision guide":** `<appRef>` = `ecocomsphase_xclw_cm_sync2_vmzvxm`, `<tenant>` = `ubc_wcpdev2`, `<owner>/<repo>` = `crismwan/ECO-COMS-Extend-App`, secrets `WD_DEV_TOKEN` (tenant token, 1 hour) and `WD_WCP_TOKEN` (8 hours), zip `ECO-COMS-app-upload.zip`, folder `$HOME\ECO-COMS-upload`. The manual route worked tonight (upload + deploy, Success true; wdcli asked for a tenant login once the tenant token expired).
- 2026-11-03: Demo files saved with dated names (ECO-COMS-*-2026-11-03.*) after the same-name copies in OneDrive stayed at the Nov 1 versions. Live demo narration: demo stops only (slides 4-11, 7.5 min), no 'new feature' wording. Tenant check: orchestration runs from pages aren't recorded in the tenant; the Orchestration Runtime Tracker covers BP-triggered runs only.
- 2026-11-03 (morning): Demo data reset to the 3 setup audit records: removed the rehearsal record for X:CLW:PATTERN:*:CPSC:110:101:2026W2 with the new `repair --drop-audit` (e2e repair-apply, only=<org>); the org itself stays active in Workday. Cleanup check: the 36 test orgs (X:ADM:TEST:ORG:10xx, X:CLW:PATTERN:TEST:*) are still active, so the Nov 1 cleanup's inactivations didn't take; rerun cleanup-apply (one org first, to read the error) after the demo, together with the rehearsal pattern above.

- 2026-11-04: **Graph API pilot live.** Audit records are read through the Graph API on Audit Log, Insights, RBAC Hub and Shell Org Detail (build pass `tools/graphql_audit.py`, Graph Query `presentation/graphQueries/auditLogsNewest.graphquery`, provider `workday-graph`). Newest first via `orderBy: {timestamp: DESC}`, replacing the count + offset REST pages; pages 1-4 wait for page 0 (Graph offset rule). The two success pages (newShellOrgSuccess, newShellOrgPatternSuccess) still read REST: a Graph read right after a write isn't confirmed yet. Read-only suite `graphql` (e2e task) checks schema, totals vs REST, orderBy, where, offset paging and a second user (skipped: no WD_SECOND_TOKEN). In ubc_wcpdev2 the Workday Graph API Applications domain grants View to All Users; check before promoting. The two CPSC_V:110 rehearsal orgs back the 3 demo audit records: keep them.
- 2026-11-04: **Audit records carry the orchestration run ID** (field `runId`, "Orchestration Run ID"). `tools/audit_run_id.py` adds `runId = context.orchestrateId()` to GetInputParams and `"runId"` to the audit template in IORC_0037_XFD_SEC_Create_Application_Shell_Org, IORC_0037_XFD_SEC_Create_Pattern_Shell_Org, IORC_0037_XFD_SEC_Assign_Remove_Role_Positions, IORC_0037_XFD_SEC_Bulk_Role_Changes_From_CSV, IORC_0037_XFD_SEC_Bulk_Role_Changes_From_Grid, IORC_0037_XFD_SEC_Close_Denied_Role_Request, IORC_0037_XFD_SEC_Change_Shell_Org_Status. App Hub build and deploy succeeded; the Audit Log shows a Run ID column (empty on the 3 older records). **Not yet confirmed by a real run**: the smoke check `Audit.runId` will pass or fail on the first audit record written after 2026-11-05. Workday event reference (e.g. Assign_Roles_Event_Reference) not stored yet: needs the SOAP response parsed in IORC_0037_XFD_SEC_Assign_Remove_Role_Positions.
- 2026-11-04: **Audit records link to their Workday event and run.** Field `eventWid` (tools/audit_event_ref.py): Assign Roles event in IORC_0037_XFD_SEC_Assign_Remove_Role_Positions, IORC_0037_XFD_SEC_Bulk_Role_Changes_From_CSV, IORC_0037_XFD_SEC_Bulk_Role_Changes_From_Grid; review event on DENY (IORC_0037_XFD_SEC_Close_Denied_Role_Request), APPROVE (review step page) and withdraw (deleteAssignableRole). REQUEST records have none (written before the event exists). Audit Log: **Workday Event** column (related actions) and **Run ID** as a link to the app's developer console (no per-run page exists). Test `eventlinks` (e2e task) passed: P-00001 added to and removed from X:BPMS(ODMT):ROLE:ADVISORS, both runIds equal their launch's X-Orchestrate-Id, both events open. This left **2 more audit records** (ASSIGN/REMOVE POSITION, 2026-11-04 ~19:40Z), so the demo data now has 5. The gateway refused the test launch with the org's full name (HTML 403); the test retries with the org code. Not yet seen in the browser: the two new columns (the link to the computer was down).
- 2026-11-04: **Run ID column removed from the Audit Log** (user decision): the run ID is still written to every audit record (`runId`) and read by the page's Graph query, but not shown, because it only leads to the developer site (no page per run, Logs keep 15 minutes). The Workday Event column stays. RBAC Hub moved back to REST for its audit read (2.0-2.6 s with Graph vs 0.7 s before, timed in Chrome); deploy d62cc10 succeeded, re-timing pending (browser session needed a fresh Workday sign-in).
- 2026-11-04: **Audit Log Excel export writes the Workday Event address** as text (`https://wcpdev.wd101.myworkday.com/<tenant>/d/wid/<eventWid>.htmld`); the grid view is unchanged. Excel exports can't hold hyperlinks (valueType boolean/date/number/string). The host is the `WORKDAY_HOST` constant in tools/graphql_audit.py: **change it when promoting to a tenant on another host**. Not yet checked with a real export.
- 2026-11-04: **UI round.** (1) Audit Log filters **Changed By** (Anyone / Only my changes) and **Organization** (card shown only while one is picked; Shell Org Detail has "View changes in Audit Log"), all filters carry each other (tools/audit_filters_more.py); checked live: counts, labels, clearing, the link. (2) About boxes collapsed with a summary line on 6 more pages (Bulk Role Grid, Bulk Role Results, Insights, Shell Org Detail, Bulk Template Upload, AAA Role Requests). (3) Event links on request pages already existed (Review column). (4) **Audit Log Excel export was failing** (fieldSet columns had no export value; probably since those columns were added): fixed with tools/excel_export_values.py + Static.excelFieldSet; a real export now lists every row with the Workday Event address. ISC Queue export checked: works.
- 2026-11-04: **Access Review page** (`accessReview`, builder `tools/build_access_review.py`, script `comsAccessReview.script`, card `AccessReviewCard` on the RBAC Hub). One row per shell role × organization × position (WQL allShellAssignableRolesinTenant), last ECO-COMS change (ASSIGN POSITION) and last review (REVIEW) from the newest 200 audit records via Graph. Ticking Still Needed + OK writes a Role Assignment / REVIEW audit record per ticked row; Manage opens editRoleAssignment. Workday role assignments have no expiry, so there's no expiry date to show.
- 2026-11-04: **Unused parts removed** (product owner): business objects COMSRoleAssignment and COMSShellOrgRequest (never written; the tasks AdminProvisioning, ShellOrgManager and NewShellOrgPattern are now context-free), the always-excluded `selectedShellOrg` endpoint on assignableRoleManager, pod `ubcLogo`, the never-placed Extend Cards `myRoleRequestsCard` / `iscQueueCard` (carddefinitions, AMD tasks, cardtenantsettings), the gatewayprobe test suite, and branches e2e-coverage, offline-work, isu-writes, isu-writes-before-rebase. Kept: the Workday Home Card orchestrations (working) and their CardData twins (the only launchable copies, used by the HomeCards smoke tests), isu-writes-v2 / tools/isu_writes.py (security), the four reports, the timing suite.
- 2026-11-04: **Stuck-request reminder** (product owner: "use BP notification"). Review COMS Assignable Role Request (Default Definition) → Business Process → Add Notification: On Entry of step b (Approval), Delay Notification by Trigger Moment + 2 Days, Recipients = Awaiting Persons, no condition rule, subject "Reminder: ECO-COMS role request waiting for review", short body. No existing condition rule fits "step b still awaiting", and the docs don't say whether a delayed notification is re-checked at send time or who Awaiting Persons resolves to then **(unverified)**. Check on the next real request: the event's Pending Notifications grid (Delayed Until, recipient), and whether a request approved within 2 days still sends it. If it does, add a condition rule (Create New Condition Rule on the notification) for the approval step still awaiting action.
- 2026-11-04: **Access Review narrowed to vacant positions** (product owner: "only keep for vacant positions, so if role assignment incumbent has left"). Rows = shell-role assignments whose position has `cf_PositionIsFilled = false` in `allPositions` (matched on the position ID at the start of the descriptor). Smoke check `AccessReview.vacant` runs the page's two queries: 829 positions, 185 vacant, 8 shell-role assignments, 0 on vacant positions (so the page is correctly empty today). The checklist moved to its own page (Review All Positions, `confirmAccessReview`); first live OK failed with "Unknown Variable found: rv.posWid": a grid's row variable isn't available when the outbound body is built at OK, so row values now ride in the row's own cells (text `valuesOut` with `self.value`, hidden tags in a fieldSet) and the tick box binds only constants. That fix isn't tested live yet (needs a vacant position holding a shell role).
- 2026-11-04: **Unused business-object fields removed** (product owner): COMSApplication `idPrefix`, `createdBy`, `workdayOrgId`; COMSAssignableRole `enabledForCompany`, `enabledForCompanyHierarchy`, `positionRestrictions`, `workdayPositionId`, `positionIsFilled`, `organizationRoleAssignments`. No page, orchestration, report or test used them, and `datacheck` (DataCheck.unusedFields) found no value in any of the 15 application and 43 request records. Test data added for the Access Review: P-00030 Senior IT Analyst (Unfilled) on X:BPMS(ODMT):ROLE:ADVISORS, STAFF and DEPTSTAFF (one REVIEW on ADVISORS); remove with Manage when no longer needed.
- 2026-11-04: **RBAC Hub: Pending Requests by Age** (`PendingAgeChart`, builder `tools/build_pending_age.py`, script `comsPendingAge.script`): requests Pending ISC Review grouped by business days waited (0-1, 2-3, 4-5, over 5; same count as the ISC Queue's Waiting column), stacked assignable vs AAA, from the hub's existing request pages. In the actions row beside Role Requests; that row is now `masonry` (a 4th card in a grid row wraps on narrower screens). App Activity lost its Audit Log footer link (the Audit Log card has one). Live check: 3 pending, all 2-3 days (2 assignable, 1 AAA), matching the ISC Queue card.
- 2026-11-04: **Speed pass** (timed in the tenant: server page time, warm median of 7 loads; per-call timings from the `timing` e2e suite).
  - Audit Log 2.1-2.4 s → 0.47 s (`tools/audit_speed.py`): dropped the three lookup lists (all shell orgs 609 rows ~560 ms, shell roles, AAA roles) that only linked old records without stored WIDs, after backfilling those 2 records (`repair --apply --backfill-wids`); Graph pages 1-4 skipped with `exclude` while page 0's total is under their offset.
  - Insights 4.1-7.3 s → 0.70 s: Applications at a Glance (per-app counts over ~600 orgs) moved to its own page `comsInsightsApps` (~1.0 s), linked from Insights.
  - Assignable Role Manager 1.2 s → 0.73 s (`tools/arm_speed.py`): dropped `allPositions` (unused, 0 rows) and `positions` (Staffing jobs, only for names of old requests; REST default capped it at 20).
  - Shell Org Manager 1.4-1.8 s → 1.5 s (`tools/som_speed.py`): the separate patterns query is gone (patterns come from the shell-org list, which already holds them); the time is page script and the 188 KB of rows, not data calls. Server-side app filtering isn't safe (some filters match by name prefix).
  - Kept as is (measured, no gain): role requests stay on REST (count + 3 pages ~300 ms steady; the same read through Graph took 246-2043 ms). Audit `timestamp` is TEXT, so Graph can't filter a period on the server (String_Filter has no gt/gte); with 9 audit records it wouldn't help anyway.
  - UI: ISC Queue's Role Name + Workday Assignable Role merged into one Role column with the Workday link (`tools/ui_tweaks.py`); Access Review hides Review All Positions when empty. `pageActionButton` stays "won't do" (docs/UI-PHASE-2-DESIGN.md R3). Grid columns have no documented per-view hide, so Approved By/Date stay in the Pending view.
- 2026-11-04: **Application Patterns setup pages** (product owner, from the architect's brief: pattern formats configurable in the app, not the repo). Builder `tools/build_app_patterns.py`, script `comsAppSetup.script`, domain Manage: COMS Application Setup.
  - `appPatternSetup` (VIEW): every COMSApplication with its format, an example name and status; **Add Application**, **Edit** per row. Opened from an "Application Patterns" pill on the hub's Shell Organizations card and on Shell Org Manager's Quick Actions.
  - `editAppPattern` (EDIT, `?recordId=` to edit, none to add). Reworked the same day (product owner: "This is all that needs to be modified - add pattern and example", plus copy from another pattern):
    - Edit shows the Application ID and Name read-only; only **Pattern Format** and **Example** change, written as on the list (`CP: Subject, Course`, `X:BPMS(AOC):CP:MECH_V:1*`).
    - Add Application: the ID is a dropdown of Workday applications (X: org codes from WQL `customOrganizations`, cut to `X:APP`) that have **no record yet**, plus a required Name. New records are active, orgType = ID, orgSubtype X:SHELL.
    - **Copy from**: a dropdown of the other configured applications; it fills both boxes (`text.setValue` works on this plain EDIT page) and swaps the example's application ID for this one's.
    - A field's rules (regex, hint, blank means any) come from this record's field of that name, else any application's (e.g. Section from Clockwork), else the standard Role Name rule. The schema JSON also stores the full `example`, which the list shows.
    - Checks, live and on OK, recheck the example whenever the ID or format changes: format has one colon, 1+ prefixes (capitals/digits/_, no repeats, `/` between), 1-7 unique field names ≤40 chars; example has no spaces, starts with `<ID>:`, uses one of the prefixes, has one value per field, and each value matches its field's rule (error shows the field's hint).
  - Tested live 2026-11-04: dropdown lists only unconfigured apps; Copy from; field-count, rule (lowercase Section), missing colon and lowercase prefix errors; OK refused with errors; a real save of X:ADM unchanged returned to the list; the Add Pattern form still reads X:ADM. Smoke `Apps.patternFormats` passes on all 15. Audit.runId now skips records pages write (no orchestration run).
  - Later 2026-11-04: **Active** checkbox back on Edit (where to reactivate). Inactive applications take no new patterns: hidden from the Add Pattern picker, Shell Org Manager hides its Add Pattern button, and newSchemaPattern opened directly shows "Application Inactive" with no OK. X:CLW had been Inactive only because it was created by hand before the flag was used; reactivated through the page. Back links on Application Patterns and Add/Edit: Shell Org Manager (plus Application Patterns on Add/Edit). Add Application shows a note for a missing application: it needs an organization type named after it and a Create Custom Organization with code = the ID and subtype X:META in Workday (Add Shell Org can't make it: it only adds `<existing app>:<code>` orgs).
  - The format box is a standard-width text box, so long formats (X:ADM's four prefixes) are cut off until clicked; Workday doesn't let a text box's width be set.
- 2026-11-04 (evening): **Application Patterns Fields grid restored** (product owner: "The full grid makes sense, all the rules need to come from that, ensure there is still a copy format"). editAppPattern: Prefixes + live Example Pattern Name + Fields grid (up to 7 rows: Label, Format regex, Hint, Example, Blank means any); every field rule comes from the grid. **Copy from** fills Prefixes and calls `fieldsGrid.setRows(...)` (developer.workday.com grid method; confirmed live: the grid took X:BPMS(AOC)'s 2 rows). Kept from the text-box version: Application ID dropdown of unconfigured applications, the missing-application note, Active, back links. Tested live: Add page refuses OK without ID/Name; X:ADM Edit loads its row and saves unchanged.
- Kept `:PATTERN:` in Clockwork names (395 existing X:CLW:PATTERN:... orgs; product owner: "never mind").
- 2026-11-04: **Sub-orchestrations** (tools/extract_subflows.py, last build step; `--restore` first so in-place patch steps still find their steps; full parents kept in tools/subflow_src/):
  - `IORC_0037_XFD_SEC_Sub_Process_Bulk_Role_Row` ← IORC_0037_XFD_SEC_Bulk_Role_Changes_From_CSV + IORC_0037_XFD_SEC_Bulk_Role_Changes_From_Grid (per-row ActionBranch; 24 inputs incl. sourceLabel). Test `bulkvalidate`: TEST batch through IORC_0037_XFD_SEC_Bulk_Role_Changes_From_Grid VALIDATE → Validated, row INVALID/VALID, no audit.
  - `IORC_0037_XFD_SEC_Sub_Create_Shell_Organization` ← IORC_0037_XFD_SEC_Create_Application_Shell_Org + IORC_0037_XFD_SEC_Create_Pattern_Shell_Org (Organization_Add_Update, accepted check, log + audit; 11 inputs: orgName, orgCode, orgSubtype, orgType, objectType, objectLabel, ...). Parents keep their inputs, application lookup and the pattern name check.
  - `IORC_0037_XFD_SEC_Sub_Start_Request_Review` ← IORC_0037_XFD_SEC_Start_Role_Request_Review + IORC_0037_XFD_SEC_Start_Admin_Request_Review (everything after GetInputParams; the parents remain only for their two security domains; audit wording via requestLabel/showOrg/showEffective).
  - Test `subflows`: launches each parent with input only Workday rejects (impossible effective date, unknown request) and requires the error to name the sub-orchestration's step; nothing is created. The success path of the review start (event initiated as the requester) is covered by the `full` write suite, not run yet (it leaves TEST orgs and requests).


## Shared audit-record step (2026-11-05)

- `IORC_0037_XFD_SEC_Sub_Write_Audit_Record.suborchestration` holds the one comsAuditLogs template. Callers: IORC_0037_XFD_SEC_Assign_Remove_Role_Positions, IORC_0037_XFD_SEC_Change_Shell_Org_Status and the IORC_0037_XFD_SEC_Sub_Process_Bulk_Role_Row, IORC_0037_XFD_SEC_Sub_Create_Shell_Organization and IORC_0037_XFD_SEC_Sub_Start_Request_Review sub-orchestrations. IORC_0037_XFD_SEC_Close_Denied_Role_Request (BP-triggered) keeps its own step.
- Built by `tools/extract_subflows.py` (`share_audit`, runs last; `--restore` brings back the full parents from `tools/subflow_src/`). Static checks: `subflow` (ids and inputs) and `templateIf` (`{{#if}}` needs a Boolean).
- Verified live 2026-11-05 after deploy b2ce8b6: App Hub holds the 4 sub-orchestrations identical to the repo; suites subflows, pattern-guard, eventlinks (top-level caller), bulkvalidate and the new **bulkapply** (bulk edit adds then removes P-00001 on the test role: the nested call IORC_0037_XFD_SEC_Sub_Process_Bulk_Role_Row → IORC_0037_XFD_SEC_Sub_Write_Audit_Record) all pass.
- Not run live: the success paths of IORC_0037_XFD_SEC_Sub_Create_Shell_Organization and IORC_0037_XFD_SEC_Sub_Start_Request_Review, and IORC_0037_XFD_SEC_Change_Shell_Org_Status, because each leaves permanent data (new org, BP-linked request, org status events). Planned with the post-demo cleanup.

## Application Patterns pages: layout review (2026-11-05)

- Edit/Add: Application section holds ID, Name and Active (then the X:META setup note on Add); Pattern Format holds Copy from, Prefixes, the fields grid, then the Example Pattern Name it produces. Grid column "Blank = any (*)". The help line above the grid is "Field rules"; field errors show under it.
- Both pages follow the long-page standard (About text over 350 characters): About box starts closed (`tools/collapse_about.py`), one-line summary under the title (`tools/ux_improvements.py --tiles`).
- Checked live after deploy: list page; X:CLW edit (preview updates; an example that doesn't match its format is refused at OK with "Field 3: the example ABC does not match the format ..." and the error clears once fixed; Cancel saves nothing); Add Application (3 required-field errors on an empty OK); X:ADM saved unchanged returns to the list; Add Shell Org Pattern for X:CLW reads the format. Smoke: 15 formats valid.
- The list's Edit header sits a little lower than the sortable headers, as on the other list grids with a button column (Access Review, Insights).

## Maintain Application Pattern (2026-11-05)

- `appPatternSetup` renamed **Maintain Application Pattern** (title, back links, hub and Shell Org Manager Quick Actions pills, the inactive-app message on Add Pattern).
- **Related action on each application record:** model task `MaintainApplicationPattern` (businessObject COMSApplication, domain Manage: COMS Application Setup, routePath `/editAppPattern/{taskObjectId}`); AMD task `editAppPatternRecord` (`/editAppPattern/{taskObjectId}`; with `{recordId}` App Builder marked the Page Route invalid) opens `editAppPattern`, which reads `queryParams.recordId ?? queryParams.taskObjectId` (grid Edit/ID links pass `recordId`); flow `editAppPatternRecordFlow` returns to the list. Confirmed live: Audit Log row → related actions → COMS Application → Maintain Application Pattern opened X:ADM's format; after the route rename, X:CLW from the related action and X:BALT from the grid's Edit button (2026-11-05).
- **Audit Log:** Change Type pill "Application Pattern" (built in `tools/audit_filters_more.py`, which overwrites `build_filter_pills.py`'s card); its rows link the Organization cell to the application's organization since 2026-11-06 (before: the application record; see "Audit Log: Application Pattern rows link to the organization" below; `tools/app_pattern_audit.py`). The list page has **View Change History** (Audit Log filtered to Application Pattern).
  - Lookup lesson (live): inside a grid cell, both `.filter(a => { a.appId == logEntry.x })` and `list:filter(list, 'appId', logEntry.x)` found nothing (15 records loaded, 0 matches); `list.map(a => { a.appId }).indexOf(logEntry.coName)` + `.get(i)` works.
- **Grid:** `appPatternsGrid` uses `tools/app_grid.py` columns (Application ID link, Name, Pattern Format) like Shell Org Manager / Add Pattern / Bulk Edit, plus Example, Status (✓ Active / ○ Inactive richText, Excel value set) and Edit; in `grid_style.py` SHORT_LISTS (no sorting, headers aligned). Long IDs (X:BPMS(ADHC)) are cut off in the first column; widths can't be set.
- **Security (tenant, administrator):** the pages, the related action and the COMSApplication records are all on **Manage: COMS Application Setup**; Add Shell Org Pattern is on Manage: COMS Shell Organizations but reads COMSApplication. Policy: pattern maintainers View + Modify (pages and task) and Get + Put (records); pattern adders Get only (Add Pattern reads the formats; no access to the maintain pages, no writes). Then Activate Pending Security Policy Changes. Get-only behaviour not yet checked with a second user **(unverified)**.
- Full write suite 2026-11-05 (run 42057373245): 46/46, including the success paths of IORC_0037_XFD_SEC_Sub_Create_Shell_Organization, IORC_0037_XFD_SEC_Change_Shell_Org_Status, IORC_0037_XFD_SEC_Sub_Start_Request_Review and IORC_0037_XFD_SEC_Close_Denied_Role_Request through the shared IORC_0037_XFD_SEC_Sub_Write_Audit_Record step.
- Cleanup 2026-11-05 (product owner: keep only demo data): kept the 3 demo setup records, the CPSC_V:110 rehearsal orgs, P-00030 on STAFF/DEPTSTAFF (Access Review demo data), the 4 Application Pattern update records and the two 10-30 pending requests (KEYCLOAK COORDINATOR, AOC administrator).

## Recommendation: Workday prompt values in the instanceList prompts (2026-11-05; outcome: not adopted)

Source: developer.workday.com "Input Prompt Values for Mutations", "Concept: instanceList", "Concept: Multilevel Lists". General notes are in CLAUDE.md (instanceList → Prompt values from Workday).

Current typed-search prompts (all `searchEndPoint`/`onSearch` + WQL `contains`, quotes stripped):

| Page | Prompt | Source | Keeps |
|---|---|---|---|
| adminProvisioning, assignableRoleManager | `fuhPicker` (Functional Unit Hierarchy) | `customOrganizations` of one type, `code contains` | WID + descriptor |
| adminProvisioning, assignableRoleManager | `academicUnitPicker` | `academicUnits` (active), `academicUnitName contains` | WID + descriptor |
| adminProvisioning, assignableRoleManager, editRoleAssignment | `positionsList` / `positionsToAddInstanceList` | `allPositions`, `cf_PositionText contains` | WIDs + names, filled flag shown |
| bulkRoleGrid (grid) | `positionAddList` (`onSearch`) | same position WQL | WID + name |

1. **Positions: keep WQL.** The pickers show the Position ID and whether the position is filled, and filter to positions with a supervisory organization; prompt values give only id + descriptor and a different (security-trimmed) set. The Assign_Roles call also needs Position IDs, not WIDs. Revisit only if users find matches the current `contains` misses.
2. **FUH and Academic Unit: candidate for one multilevel prompt.** The two pickers are "one or the other" (each `onChange` errors if both are filled). A single instanceList with root values "Functional Unit Hierarchies" and "Academic Units" and `dynamicMonikerLevels` returning the matching list would remove that cross-field error and the stale-error risk. The level data can stay WQL; whether it should come from prompt values depends on step 3.
3. **First step before any build: a read-only probe** (e2e `probe`, developer token): introspect `Mutation_Prompts` and list mutation ID fields for organizations, academic units, positions and roles, then run one `search` query to compare its matches with the WQL `contains` results. Introspection works with a normal user token (CLAUDE.md, Graph notes).
4. **Bonus if prompt `search` is adopted:** the search text is a GraphQL variable, not text concatenated into WQL, so the quote-stripping (and its static check) would no longer be needed for that prompt.

## Add New Shell Organization: X:META and naming (2026-11-05, product owner)

- Requests: X:META may leave Application blank (a new application), code then starts with X:; with an application the name starts with its ID; for X:META under an application the code goes in brackets, like X:LLIS(CPE).
- Rules (one place: `presentation/scripts/comsShellOrg.script`, used by the preview and OK; page built by `tools/new_shell_org_meta.py`):
  - Subtype first. **X:SHELL**: application required, name `APP:CODE` (typing the full `APP:CODE` also works; another X: prefix is refused).
  - **X:META + application**: `APP(CODE)`; a bracketed application uses its base (X:BPMS(AOC) + NEW → X:BPMS(NEW)). NEW, (NEW) or the full name may be typed; upper case, no `:` or brackets inside.
  - **X:META, no application**: X: plus one part (X:NEWAPP), upper case, no spaces.
  - **Changed 2026-11-06 (product owner):** the new application code can be anything and is used exactly as typed (only no spaces). The server check CheckOrgName skips its X: checks when the name is the type itself. An organization created without X: doesn't show in the app's lists (they all filter on `code contains 'X:'`), and its organization type of the same name must exist in Workday first.
  - For X:META the name is also the **organization type** sent to Workday: every application-level org has a type of the same name (probe 2026-11-05: X:LLIS → X:LLIS, X:LLIS(CPE) → X:LLIS(CPE), every X:BPMS(...)). That type must exist first; otherwise Workday rejects and the page says to check the type.
  - Launch parameters: orgType, organizationName, organizationCode (part after the application, or the full name for X:META), orgSubtype; comsAppId is no longer sent (unused).
- Server: IORC_0037_XFD_SEC_Create_Application_Shell_Org's **CheckOrgName** (built by `tools/patch_pattern_orchestrations.py`) re-checks type = X: plus one part, name = type or `type:`…, a new-application/bracket name (= type) only as X:META, no spaces, no second X: after the application.
- Tests: e2e `org-guard` (bad input stops at CheckOrgName; the page's own parameter sets, mirrored from the page and script, reach Workday with the name intact; impossible date so nothing is created; application pick-list query returns all 613 X: orgs without a limit). e2e `gateway` probes which launches the API gateway refuses.
- Application ID lists (Add Shell Org, Maintain Application Pattern → Add Application, AAA and role pages) all come from the `customOrganizations` WQL over topLevelOrganizations `code contains 'X:'`, so a new X:NEWAPP or X:LLIS(NEW) org appears in them once Workday has it (Add Application only lists codes without a record).
- Gateway: one test value set (`X:BPMS(AOC):TEST:GUARDPAGE`) got HTML 403; the same application with another code, other bracketed applications and bracketed X:META names went through. Brackets aren't the trigger; a rare user value could still be refused by the gateway's content filter.
- Browser: Next on this wizard step doesn't run OK's checks; OK does. After Back, the preview shows its page-load text until a field changes (wizard limitation).

### Outcome of the prompt values check (2026-11-05, e2e `prompts`, read-only)

- The Graph `prompts` query exists for only 5 mutations in ubc_wcpdev2: createReferenceLetterForWorker, referACandidate, startPerformanceReview, submitAccountingJournal, submitSupplier. None covers positions, custom organizations (FUH), academic units or roles, so there is no Workday prompt source for any of the app's 8 prompts.
- REST `values` endpoints give a browse tree (e.g. staffing `values/jobChangesGroup/supervisoryOrganization/`: My Favorites, ...), no typed search, and not the organizations the app uses.
- Impact check: Edit Role Assignment and Bulk Edit keep the Position ID (Assign_Roles needs it, a WID is rejected); prompt values return WIDs only, so they would need an extra lookup there anyway.
- Baseline (median of 3): FUH search 207 ms, Academic Unit search 170 ms, Position search 1,083 ms (100-row cap). Nothing changed in the app; the current WQL searches stay.
- Still open, independent of prompt values: merging the FUH and Academic Unit pickers into one multilevel list (removes the "not both" error), and the 1.1 s position search.

## 2026-11-05: Enabled For choice and position search limit (product owner: "Yes continue")

- **Enabled For** (Submit Assignable Role Request, AAA Role Request; `tools/enabled_for_choice.py`, `--off` rolls back): a dropdown (Functional Unit Hierarchy / Academic Unit; blank = whole university) shows only the matching picker; switching clears the other (`setValue([])` on an instanceList clears it, live 2026-11-05) and resets Applies To and the AAA role name. The read-only result field is now labelled **Applies To**. Saved fields are unchanged. OK refuses a type with nothing picked. Live-checked on AAA Role Request: switch shows/hides, a picked Academic Unit (Department of Mathematics) cleared on switching.
- **Position search** (`tools/pos_search_limit.py`, `--off` rolls back; e2e `possearch`, median of 5): every position search takes ~1 s on the server whatever the limit or columns (the text scan). Without a limit broad terms returned everything ("a": 804 rows, 247 KB, 1.2 s; "P-00": 783 rows, 240 KB, 1.4 s); with `limit=50`: ~1.0 s, 15 KB. Dropping cf_PositionIsFilled gained nothing. Now the first 50 matches on all four pages, with a hint to type more.

## Research: browsing positions by supervisory organization (2026-11-05, e2e `postree`, read-only; nothing built)

Asked: instead of an empty position picker until you type, let users drill down (supervisory org → position).
- Data: 829 positions sit in 129 supervisory orgs; per org median 5, 90th pct 13, max 41 (IT Services Group).
  Positions in one org load in ~0.33 s (WQL `allPositions WHERE supervisoryOrganization in ('<wid>')`).
- Workday's own tree, `GET staffing/v6/values/jobChangesGroup/supervisoryOrganization/` (75 ms), has roots
  My Favorites, My Organizations, Supervisory Organizations by Manager (108 managers, deeper levels),
  by Manager Hierarchy, Supervisory Organization, Active Supervisory Organizations by Hierarchy. Trimmed to the user's security.
- Widget: multilevel instanceList (`dynamicMonikerLevels`, developer.workday.com "Concept: Multilevel Lists"), last
  level = the positions WQL. Unverified: multilevel together with `multiSelect` and `searchEndPoint`, inside a grid
  (Bulk Edit), and REST tree hrefs called from a page endpoint. Pilot candidate: Edit Role Assignment, as a build step with `--off`.

### Pilot built: Edit Role Assignment, Positions to Add (2026-11-05, `tools/pos_tree.py`, `--off` rolls back)
- Clicking the picker shows My Favorites, My Organizations, Supervisory Organizations by Manager (manager -> orgs) and
  Supervisory Organization (A-Z, 139 orgs over two REST pages). An organization opens to its positions (same Position ID
  + label as a search result, so OK / AssignRole / audit are unchanged). Typing still searches (first 50).
- Live check: by Manager -> Alain DuBois -> Global Support - Canada Group -> 13 positions; ticked several; a position
  found by typing (P-00010) showed already ticked inside its org (My Organizations -> HR Services Department), and one
  picked by search plus one picked by browsing both ended up selected (2 items). No submit was made (test role/org).
- Not yet done: Submit Assignable Role Request and AAA Role Request (same change: add them to PAGES), Bulk Edit (grid
  cell, untested), the two "... by Hierarchy" folders (nest to any depth).

### Rolled out to every picker (2026-11-05)
- **Positions** (`tools/pos_tree.py`): Edit Role Assignment, Bulk Edit (grid cell, single select), Submit Assignable
  Role Request and AAA Role Request. The leaf id follows what each page already saves: Position ID on Edit Role
  Assignment and Bulk Edit, WID on the two request pages. Live: grid cell browse -> My Organizations -> HR Services
  Department -> P-00008, row counter "1 addition ready"; request page leaves carried WIDs.
- **Functional Unit Hierarchy / Academic Unit** (`tools/unit_tree.py`, both request pages). There is no hierarchy in
  this tenant (e2e `orgtree`: all 837 FUH orgs at level 1, no superior/included orgs; all 157 Academic Units top
  nodes, academicUnitHierarchies empty), so the folders are the types: FUH subtype (01 Company ... 07 Department
  (363) ... 11 Other) and Academic Unit subtype (Campus/Senate, College, Department, Faculty, ...), with counts. A
  type with more than 40 entries opens to an A-Z level first. One eager WQL each (fuhTreeAll 0.37 s / 191 KB,
  auTreeAll 0.18 s / 38 KB, in parallel with the page's other loads). Typed search unchanged (FUH by code, AU by name).
  Live: FUH 08 Sub-Department -> D -> Dental Clinic; AU Faculty -> Faculty of Arts.
- The AU list (inactive = false) still includes "Faculty of Arts and Sciences (inactive as of 1/7/2020)": the
  record isn't flagged inactive in Workday. Same as the typed search.
- If the production tenant has real FUH / Academic Unit hierarchies, the tree should follow them instead
  (superiorOrganization / academicUnitHierarchies.directSubordinates); re-run `orgtree` there first.

### Tests and negative tests of the edited pages (2026-11-05)
- **Static:** new `Static.treePickers` (every browse picker saves the same id as its typed search, reads real
  endpoints, invokes only deferred ones; every position picker has a tree; mutation-tested: a WID/Position ID mix-up
  and a misspelt list both fail) and `Static.clearOnChange` (below). 10 passed.
- **Live suites:** smoke 31/31, org-guard (Add Shell Org) 22/22, timing (fuhTreeAll 0.37 s runs beside the existing
  0.55 s customOrganizations list, so no slower load).
- **Bug fixed (tools/clear_on_change.py):** Edit Role Assignment, OK with no positions then picking one left "Select
  at least one position to add or remove." showing, so OK stayed refused until a reload. Every field an OK check
  flags now clears its error when changed (Positions to Remove clears the shared add-or-remove error too); same fix
  for Custom Organization (Submit Assignable Role Request), Application and Effective Date (AAA Role Request) and
  the Bulk Edit real-run checkbox. Retested live: the error clears the moment a position is picked from the tree.
  Not edited this week, still flagged by the static check: bulkRoleChanges (file uploader), deleteAssignableRole
  and manageShellOrgStatus (confirmation checkboxes).
- **Passed live:** OK with nothing / no date (Workday's required-field errors, then the page's own); Positions
  required error clears on a tree pick; Enabled For switching clears the other picker and back gives an empty
  picker; AAA role name follows a tree pick "(ADHC, Academic Unit)" and drops the scope when the unit is removed;
  Bulk Edit duplicate check fires for a browsed position (P-00011 already holds ADVISORS) and clears when the role
  changes to STAFF.
- **Not run live, on purpose:** OK paths that would pass validation (they create real requests / role changes).
  Workday's own required-field checks run before onSubmit, so the scripted "Enabled For chosen but nothing picked"
  check can only be reached with a complete form.
- **Resolved (product owner: "Use the full ID"):** AAA Role Request built the role name from the application's
  inner code ("...(COMS)") while the existing AAA roles are "...(X:BPMS(COMS))" and "...(X:BPMS(ODMT))", so the
  duplicate check missed them. `tools/aaa_full_app_id.py` (`--off` rolls back) keeps the full ID up to the closing
  bracket on that page only. Live: the list shows full IDs, the name reads "...(X:BPMS(COMS))", and OK is refused as
  a duplicate. e2e `aaaname` 4/4 (list uses full IDs, duplicate check sees both existing roles, no empty ids). The
  one pending request from before keeps its old name "(AOC, Functional Org)".
- Minor: Bulk Edit's change counter counts a row that has the duplicate error ("1 addition ready"); OK is still
  refused while the error shows.

### Regression hour (2026-11-05, 15:04-16:05)
- **Live suites:** smoke 31/31, datacheck 3 pass + 1 warning (58 gaps on old October TESTROLE requests, known),
  org-guard 22/22, graphql 10, eventlinks 6, possearch 2, aaaname 4, timing 2, pattern-guard passed on rerun.
- **Test bug fixed:** pattern-guard threw "pageCases is not defined": an org-guard edit had landed in patternGuard.
- **Bug fixed (Bulk Edit):** onSubmit puts its grid-level errors ("No changes yet", over 50, duplicate row, already
  holds the role, role/org missing) on Effective Date, which only its own onChange cleared. Ticking Remove after a
  "No changes yet" left the error showing and OK refused. `clear_on_change.py` now clears it from Remove, the
  position and role/org cells, and row add/remove (the date is re-checked on OK anyway); it also stopped doubling
  an existing `self.clearError()` (the real-run confirmation checkbox had it twice). Retested live after deploy:
  the error clears on ticking Remove and on Add Row.
- **Passed live in the browser:** Add Shell Org (X:META prompt, lower-case refusal and its clearing, X:SHELL naming);
  Edit Role Assignment on ODMT STAFF (empty OK error, cleared from Positions to Remove); AAA Role Requests and ISC
  Queue views load; FUH typed search (CPDK); AAA full-ID names; Bulk Edit required date -> calendar pick clears it,
  then "No changes yet".

### Follow-ups after the regression hour (2026-11-05, product owner: "proceed")
- **Stuck errors on three more pages** (`clear_on_change.py`): Bulk Role Changes (the CSV uploader clears its
  "Choose the CSV file" error in `onFileAdd`: a fileUploader has no onChange, developer.workday.com "fileUploader"),
  Withdraw Assignable Role and Manage Shell Org Status (confirmation checkboxes). Static.clearOnChange now flags no
  page. App Hub accepted `onFileAdd` with `<uploader>.clearError()`. Live: OK with no file gave "Choose the CSV
  file..."; adding a header-only CSV (set on the page's file input) cleared it. Left without OK, nothing saved.
- **Bulk Edit counter** (`ux_improvements.py` step 5): counts as "ready" only additions that OK would accept (role/org
  and position set, not already held, no repeat); the others show as "N rows to fix". It uses OK's own already-holds
  list, copied from onSubmit at build time. Changing a row's role/org now updates it too. Live after deploy (ODMT):
  ADVISORS + P-00011 (already holds it) gave "1 removal and 0 additions ready, 1 row to fix"; switching the row to
  STAFF gave "1 removal and 1 addition ready". Nothing submitted.
- `origin` now points at github.com/crismwan/ECO-COMS-Extend-App (GitHub had reported the repository moved).
- **Build failure on the way (fixed):** the first counter build failed App Hub with "PMD Scripting syntax error"
  (the copied already-holds list lacked one `)`). Found with CI's new build-log step (deploy.yml runs
  `wdcli app builds logs` after a failed upload). Static.scriptBrackets now fails on unbalanced script brackets.
- **Browse lists and failOnStatusCodes (decided 2026-11-05):** posTreeRoot, fuhTreeAll and auTreeAll stay quiet
  on purpose: they're extras beside the typed search, so a failure leaves an empty tree instead of breaking the
  page. Static.failOnStatusCodes lists them as an exception and fails if one loses bestEffort.
- **CI:** actions/checkout v5 and upload-artifact v6 (both node24, read from their action.yml) and runner pinned
  to ubuntu-24.04, after GitHub's Node 20 and ubuntu-latest → Ubuntu 26 warnings.
- A new session clones the repo with the old lowercase address, so git prints "This repository moved" again;
  pushes still work. `git remote set-url origin https://github.com/crismwan/ECO-COMS-Extend-App.git` silences it.
- **Data check noise removed (2026-11-05):** the 58 Data.gaps warnings all came from 36 closed (Approved/Denied)
  October test requests (TESTROLE / TEST: names) made before denialReason, enabledForOrganizationTypes and
  positionNames existed. They can't be deleted (linked to BP events), so datacheck now counts closed test requests
  (46, including ones without gaps) instead of listing them. Result: 5 passed, 0 warnings; the 3 other requests,
  11 audit records have every displayed field filled.
- **Live demo, 5 Nov edition:** the 3 Nov stops updated plus this week's changes (X:META/X:SHELL naming, browse
  pickers, full AAA role names, Bulk Edit counter), 9 stops, 8:54 of narration in an offline voice (Kokoro; the
  3 Nov voice service isn't reachable from the cloud workspace). Source in `docs/demo/`. A video from page captures
  wasn't possible: loading a rendering library into the Workday page was refused by a safety check.

## Shell Org Manager application bar (2026-11-05, product owner; Option E on the design canvas)

- **Why:** the Application Patterns tab listed only the 15 applications with a pattern record, so 18 of the 33 could never be picked. The bar lists every application, derived as Add Shell Org and AAA Role Request do (an X: org code cut to its application ID, plus pattern records), so a new X: organization appears by itself.
- **Option D** (built first, 2686d7a) used simple cards: "Narrow down" opened family cards, then large application cards; Previous/Next/Show all sat under the card's ⋮ menu. Tested live and replaced the same day: 16 BPMS cards pushed the tabs off the screen and the main actions were hidden.
- **Option E (built, 021d350 + follow-up):** everything is pills. All applications: a family pill card ("BPMS · 16", …) and a "No pattern format yet" card (first 10 of 18). `?family=F`: that family's applications as pills, ● pattern ready / ○ none yet, 10 per card (BPMS = two cards). `?appCode=A`: ‹ previous, next ›, Change application (opens the family with ✓ on A) and ✕ All applications, plus a pattern format card: Set Up Pattern Format (no record), Ready with Add Pattern / Maintain Application Pattern, or Inactive. The old "<app> / ← Back to Applications" heading and the yellow banner are gone.
- **How:** one `cardContainer`, `dynamicCards` over `comsAppIndex.barCards(...)`, which returns `{cardId, params}`; `template.cardId` is `<% barCard.cardId %>`. Pill cards can't hide a pill, so `tools/som_pill_cards.py` generates `SomPills1`…`SomPills10` (n pills each) and the script picks `'SomPills' + n`. Every pill reloads the page with its own `appCode` / `family`.
- **Live tests (2026-11-05):** default, BPMS family, ODMT narrowed (no record → Set Up), Change application (✓ ODMT), X:CLW (Ready, Maintain opens its record), X:SP1(INTEG) (single app: no previous/next), unknown X:NOPE with an unknown family (no error, no format card). Not tried live: the Inactive card (no inactive record in the tenant). Counts: the bar counts an application's shell orgs as `<app>:...` codes, the same rule the narrowed tabs use.

## Naming standard: app and orchestrations renamed (2026-11-06, product owner)

- **App:** `XTND-0037-XFD_SEC-Custom_Organization_Management`. The app ID and reference ID can't change. The console name (developer.workday.com → Apps) is set with the app's **Related Actions → Rename App**; the manifest `name` alone didn't change it (it had read "ecocomsphase_xclw_cm_sync2" while the manifest said ECO-COMS). Both now carry the new name. In-app page titles keep the short product name "ECO-COMS".
- **Orchestrations:** `IORC_0037_XFD_SEC_<Functional_Description>`, sub-orchestrations `IORC_0037_XFD_SEC_Sub_<...>`, the same as the team's IORC-0032 app. **Underscores, not hyphens:** Orchestration Builder's Create New Orchestration keeps Done disabled for `IORC-0037-XFD_SEC-Name_Test` and enables it for `IORC_0037_XFD_SEC_Name_Test` (live 2026-11-06; nothing was created). A 47-character name was accepted.
- Old → new (map in `tools/orch_names.py`; a one-off script did the rename and was removed 2026-11-06):
  AddShellOrg → Create_Application_Shell_Org, AddShellOrgPattern → Create_Pattern_Shell_Org, AssignRolePositions → Assign_Remove_Role_Positions, BulkRoleApply → Bulk_Role_Changes_From_CSV, BulkRoleGridApply → Bulk_Role_Changes_From_Grid, DenyRoleRequest → Close_Denied_Role_Request, IscQueueCardData → ISC_Queue_Card_Data, IscQueueHomeCard → ISC_Queue_Home_Card, ManageShellOrgStatus → Change_Shell_Org_Status, MyRoleRequestsCardData → My_Role_Requests_Card_Data, MyRoleRequestsHomeCard → My_Role_Requests_Home_Card, StartAAARequestReview → Start_Admin_Request_Review, StartRoleRequestReview → Start_Role_Request_Review; subs CreateShellOrganization, ProcessBulkRoleRow, StartRequestReview, WriteAuditRecord → Sub_Create_Shell_Organization, Sub_Process_Bulk_Role_Row, Sub_Start_Request_Review, Sub_Write_Audit_Record.
- **Ids kept:** the builders hash a name into the orchestration id (`extract_subflows.py`, `build_home_cards.py`); they now hash the old name (`orch_names.legacy`), so App Hub sees a rename, not new orchestrations. Upload, build, deploy and the post-deploy tests passed (run 42265452654); the console lists the 13 orchestrations under their new names.
- Two uploads right after the hyphen test in Orchestration Builder were refused with only "Unable to upload app. Error"; the same commit went through a few minutes later. CI now prints App Hub's response when an upload is refused.
- **Tenant setup refers to orchestrations by name.** The launch configuration "ECO-COMS Deny Role Request" (Review COMS Assignable Role Request → Configure Orchestrations, actions Deny and Cancel) stored Orchestration Name `DenyRoleRequest`; it must name `IORC_0037_XFD_SEC_Close_Denied_Role_Request`. A launch configuration has no edit action, so a new one was created (2026-11-06): Configure Orchestrations → Orchestration prompt → Create Orchestration Launch Configuration, name `IORC_0037_XFD_SEC_Close_Denied_Role_Request`, orchestration of the same name, BP type Review COMS Assignable Role Request, no parameters; picked for both Deny and Cancel and saved. The old "ECO-COMS Deny Role Request" configuration is no longer used. **External Cards too:** after the rename both Home cards (Home Cards Workspace → "ECO-COMS: ISC Queue" and "ECO-COMS: My Role Requests", type External) showed an empty Workday Home Card Orchestration. Fixed 2026-11-06 with Edit on each card → pick `IORC_0037_XFD_SEC_ISC_Queue_Home_Card` / `IORC_0037_XFD_SEC_My_Role_Requests_Home_Card` → OK; both still render on Workday Home.
- Static check `orchName`: every orchestration follows the pattern and its file is named after it.

## Audit Log: Application Pattern rows link to the organization (2026-11-06, product owner)

- The Organization cell of an Application Pattern row now shows the application-level organization (code = application ID, e.g. X:ADM) as a Workday instance, so its related actions are the organization's (checked live: X:ADM opens the Custom Organization menu). Until then it linked the COMSApplication record, labelled "X:ADM (application pattern)".
- Lookup: WQL `SELECT workdayID, code FROM topLevelOrganizations WHERE code in ('X:ADM', ...)` over the application IDs that have a record (endpoint `auditAppOrgs`, after `auditApplications`; `in` works on text per developer.workday.com WQL Reference → WHERE). Built by `tools/app_pattern_audit.py`.

## Organizations by subtype, applications by organization type (2026-11-06)

Product owner: organizations and applications can be named anything; the app finds them by subtype only (X:META and X:SHELL, no new subtype).
- Organizations: `topLevelOrganizations WHERE subtype in (<X:META WID>, <X:SHELL WID>)` (allShellOrgs, customOrganizations, appTypes, and the Add Shell Org / Add Pattern readbacks). 614 organizations.
- Application of an organization: its organization type (`type1[0].descriptor`; every one of the 614 has exactly one). Code parsing is only the fallback.
- Roles: `assignableRoles WHERE enabledForOrganizationTypes in (<type WIDs>)`, the WIDs taken from the page's organization list (or the small `appTypes` list). Same 12 roles as the old name filter (live probe 2026-11-06).
- Server checks: the Add Shell Org and Add Pattern orchestrations no longer require X: in the application or type.
- Built by `tools/subtype_apps.py` (a late step in rebuild_all), which fails if any page or script still tells applications apart by an X: prefix.
- The one mis-named test pattern (type X:CLW) now shows under X:CLW; it can be inactivated.
