# ECO-COMS UI Phase 2: build-ready design

Source: *ECO-COMS UI Recommendations* (PDF, 23 pages, 28 Oct 2026). Every recommendation in it was checked against the repo as it stood on **31 Oct 2026, about 17:10 UTC**.

**Snapshot warning:** another session was editing the repo while this was written. Between 17:07 and 17:09 UTC, `deleteAssignableRole.pmd` became a "Withdraw" page, `newShellOrgConfirm.pmd` and `newShellOrgPatternConfirm.pmd` were deleted (29 pages now, not 31), `KNOWN_ISSUES` in `test/run-tests.js` was emptied, and `docs/USER-GUIDE.md` and `docs/ADMIN-RUNBOOK.md` appeared. Re-check those files before you build.

Platform constraints come from `CLAUDE.md` and `docs/ECO-COMS-NOTES.md`. Anything marked **VERIFY ON developer.workday.com** is syntax or behaviour that neither those files nor the repo settle. Look it up (search bar on developer.workday.com) or ask before building it.

## Summary

Status key: **Done**, **Partly** (partly done), **Not done**, **Won't do** (conflicts with a platform limit or overtaken by the BP design), **New** (a problem found during this review that the PDF doesn't mention).

| ID | Recommendation | Pages | Status | Plan | Pri | Effort |
|---|---|---|---|---|---|---|
| N1 | REST collections capped at 20 rows | auditLogViewer, iscRoleRequestsView, assignableRoleManager(+View), adminProvisioning(+View) | **Partly done** (`limit=100` added on all 8 reads, 2026-10-31) | remaining: offset so the newest rows load past 100; show "N of total" | **P1** | S |
| N2 | Second richText in a fieldSet is silently dropped | shellOrgManager (2), adminProvisioning, assignableRoleManager | **New** | convert the empty-state banners to `text`; move notes to their own fieldSet | **P1** | S |
| N3 | newShellOrg promises weekday-only dates but doesn't check | newShellOrg | **New** | include `comsValidations.script`, check `isWeekday` in onSubmit | **P1** | S |
| N4 | Orphan pages, cards and includes | landingPage, iscErrorPage, 6 cards, comsCardGenerator include | **New** | product owner decides keep or delete; add a static warning | P2 | S |
| R1 | guide tooltips on complex fields | 9 pages | **Partly** | guides added on dropdown/instanceList fields; live check of guides on text/date; banners where guides can't render | **P1** | S |
| R2 | checkBox acknowledgement on irreversible actions | manageShellOrgStatus, deleteAssignableRole | **Done** | keep; test it | — | — |
| R3 | pageActionButton for primary actions | success pages | **Won't do** | keep PRIMARY buttons (pageActionButton is edit-only, script-only, gray) | — | — |
| R4 | External links on home hub | home | **Done** | change URLs only if the product owner wants (Q3) | — | — |
| R5 | Mark secondary tab endpoints `deferred` | shellOrgManager | **Won't do** | deferred WQL tab grids never fetch | — | — |
| R6 | Better error page guidance (403 cause, 404 links) | errorPage, iscErrorPage | **Partly** | 404 quick-link buttons, helpdesk pointer in text | **P1** | S |
| R7 | imageCard on error pages | errorPage | Not done | optional | P3 | S |
| R8 | editWizard for newShellOrg (3 steps) | newShellOrg | **Done (adapted)** | keep 1 step + Review & Submit; steps can't share data | — | — |
| R9 | editWizard for newShellOrgPattern | newShellOrgPattern | **Done (adapted)** | as R8 | — | — |
| R10 | Confirm page / "creates a live org" note | newShellOrg | **Partly** | confirm pages deleted; add an amber notice to newShellOrg | **P1** | S |
| R11 | editWizard + checkBox for delete | deleteAssignableRole | **Done (in progress)** | now a Withdraw page (cancels the review event); test it, settle vocabulary (Q5) | **P1** | S |
| R12 | radioGroup Approve/Deny | assignableRoleManagerMaintain | Not done | optional; the page is legacy-only now | P3 | S |
| R13 | Decision notes textArea | assignableRoleManagerMaintain | **Done** | `denialReason` textArea → `denialReason` field + audit details | — | — |
| R14 | Requester name and date on maintain page | assignableRoleManagerMaintain | Not done | two `text` fields | P2 | S |
| R15 | guide explaining approval | assignableRoleManagerMaintain | **Done** | `guideMaintainAction`, `guideWorkdayRole` | — | — |
| R16 | Receipt simpleCard on success pages | newShellOrgSuccess, newShellOrgPatternSuccess | **Partly** | cards exist but aren't used; feed them from the user's newest ADD audit | P2 | M |
| R17 | Creation timestamp on success page | same | Not done | part of R16 | P2 | (R16) |
| R18 | Styled warning + guide on manageShellOrgStatus | manageShellOrgStatus | **Done** | keep | — | — |
| R19 | Home count cards (pending ISC, active orgs, audit 24 h) | hubLanding (hub's initial task) | Not done | a cardContainer with 3 count cards | P2 | M |
| R20 | Home pillCard quick actions | hubLanding | **Partly** | hubLanding buttons cover it; QuickLinksCard unused | — | — |
| R21 | Home chartCard | hubLanding | Not done | reuse `ShellOrgStatusChart` | P3 | S |
| R22 | Counts above Shell Org Manager grids | shellOrgManager | **Partly** | Summary tab has counts; put counts in grid labels | **P1** | S |
| R23 | Role assignment donut | shellOrgManager | Not done | new card, slices per application | P3 | M |
| R24 | Explanations on Shell Org Manager tabs and columns | shellOrgManager | Not done | one "About" richText per tab (column guides aren't documented) | P2 | S |
| R25 | Summary cards on the ISC queue | iscRoleRequestsView | Not done | 3 `CountCard`s | P2 | M |
| R26 | Status filter on the ISC queue | iscRoleRequestsView | Not done | filter buttons + `queryParams.status` (VIEW page) | **P1** | S–M |
| R27 | Column explanations (AAA, Assignable) on the ISC queue | iscRoleRequestsView | Not done | richText legend | P2 | S |
| R28 | listDetailHub for the ISC queue | iscRoleRequestsView | Not done | not recommended (see section) | P3 | L |
| R29 | Audit log filters (date range, action, application) | auditLogViewer | Not done | presets via buttons (P2); custom From/To through a filter page + flow (P3) | P2 / P3 | M / M–L |
| R30 | Audit action donut | auditLogViewer | Not done | `AuditActionChart.card` | P2 | M |
| R31 | Export action on the audit log | auditLogViewer | **Partly** | the export note exists but `excelExportEnabled` isn't set | P2 | S |
| R32 | FUH landing counts + FUH guide | fuhLandingPage | **Partly** | an about banner exists; the page is a stub (Q8) | P3 | ? |
| R33 | adminProvisioning summary cards, guides, export | adminProvisioning(+View) | Not done | guides (R1), count cards on View | P2 | S |
| R34 | assignableRoleManager listDetailHub, guides, chart | assignableRoleManager(+View) | Not done | guides (R1) only | P2 | S |
| R35 | fileUploader + attachmentList on requests | request pages | Not done | needs an attachment object + multipart; only if wanted (Q9) | P3 | L |
| R36 | dynamicSection for filtering | shellOrgManager | **Won't do** | edit-page only; Shell Org Manager is VIEW | — | — |
| R37 | Other Part 2 components (number, multiSelectCalendar, loop, currency, video, labeledImage, SSO, inline editButtonBar) | — | **Won't do** | no fit (table at the end) | — | — |

### Build order

**P1: correctness and cheap wins (about 2 days).** Build N1 first: every filter, count and card below reads these collections.

1. N1 row limits (S–M)
2. N2 dropped banners (S)
3. N3 weekday rule (S)
4. R10 live-org notice (S)
5. R1 guides on dropdown/instanceList fields, and the live check on text/date guides (S)
6. R11 finish and test Withdraw (S)
7. R26 ISC queue status filter (S–M)
8. R22 grid count labels (S)
9. R6 error-page guidance (S)

**P2: dashboards and context (about 3–4 days).**

1. `CountCard.card`
2. R19 home cards
3. R25 ISC queue cards
4. R33 Admin Provisioning cards
5. R29a audit preset filters, R31 export, then R30 audit donut
6. R16/R17 receipts
7. R14 requester on the maintain page
8. R24/R27 explanation banners
9. N4 orphan cleanup

**P3: optional or larger.**

1. R29b custom date range page + flow
2. N1b audit beyond 100 rows (WQL)
3. R23 role donut
4. R21 home chart
5. R12 radioGroup
6. R7 imageCard
7. R32 FUH page
8. R35 attachments
9. R28 listDetailHub (recommend against)

---

## Findings not in the PDF (build these first)

### N1. REST collections are capped at 20 rows (P1, S–M)

> **Update 2026-10-31:** `?limit=100` is now on all eight business-object collection reads (commit "Close edge cases and tidy pages"). What remains is the part below for more than 100 rows (offset / newest first) and the "N of total" display.

**What I found.** These inbound endpoints call a business-object collection with no `limit`, so Workday returns 20 rows (CLAUDE.md "REST collections default to 20 rows"):

- `auditLogViewer.pmd` → `auditLogs` `/comsAuditLogs`
- `iscRoleRequestsView.pmd` → `comsAssignableRoles`
- `assignableRoleManagerView.pmd`, `adminProvisioningView.pmd`, `assignableRoleManager.pmd`, `adminProvisioning.pmd` → `comsAssignableRoles`
- `newShellOrg.pmd` → `comsApplications` (small, low risk)

`deleteAssignableRole.pmd` already uses `?limit=100`. Each full test run writes about 9 audit records, there are 20+ runs, and TESTROLE1031–1038 plus the CI requests exist. So the audit viewer and the ISC queue are almost certainly missing records today. Every filter, count and card in this design would be wrong without this fix.

**Design.**

- Change each URL to `?limit=100` (the REST maximum) and add `"failOnStatusCodes": [400, 403, 404, 500]`. For pages where a 403 is normal for some users (hubLanding, R19), see that section.
- **Order of rows (VERIFY live):** it isn't known whether the collection returns oldest or newest first. If oldest first, `limit=100` shows the *oldest* 100. The fix is a count endpoint plus an offset. Inbound endpoints can reference earlier endpoints in their URL (ECO-COMS-NOTES "ISC review business process"):

```json
{ "name": "auditLogCount", "baseUrlType": "BUSINESS-OBJECT", "url": "/comsAuditLogs?limit=1",
  "authType": "sso", "failOnStatusCodes": [400, 403, 404, 500] },
{ "name": "auditLogs", "baseUrlType": "BUSINESS-OBJECT", "authType": "sso", "isCollection": true,
  "url": "<% '/comsAuditLogs?limit=100&offset=' + ((auditLogCount.total ?? 0) > 100 ? (auditLogCount.total - 100) : 0) %>",
  "failOnStatusCodes": [400, 403, 404, 500] }
```

  `offset` on the BO REST API: **VERIFY ON developer.workday.com**. Apply the same pattern to `comsAssignableRoles`.
- Add a visible count so a cap is never silent again. Put a `text` widget `auditCountText` in the viewer's `aboutFieldSet`:
  `"value": "<% 'Showing ' + size(<filtered rows>) + ' of ' + (auditLogCount.total ?? 0) + ' records' %>"`.
  On the ISC queue, add `requestCountText` in `actionsInfoFieldSet`.
- **N1b (P3):** past 100 audit records, move the viewer to WQL on the audit data source, which allows 10,000 rows per page. The WQL data source name for an Extend business object (report label "COMS Audit Logs", or "All Audit Logs" for the report) is **VERIFY ON developer.workday.com**. Use a `.wqlquery` component with `parameters` for the filters (CLAUDE.md "WQL injection risk").

**Risks.** About 100 rows of audit data is fine for the 5 s script CPU limit. The viewer already builds its lookups once (the memory-limit fix), so keep that.

**Tests.**

- Static: a new check `restLimit`. It errors when a `BUSINESS-OBJECT` inbound endpoint with `isCollection` has a URL without `limit=`.
- Smoke: `Audit.volume` and `Requests.volume` read `?limit=1` `.total` and **warn** when it's over 100, because the page can't show everything.
- Manual: the viewer's "Showing N of M" equals the smoke total when M ≤ 100, and the newest record is at the top.

### N2. A second richText in one fieldSet is silently dropped (P1, S)

**What I found.** CLAUDE.md "richText — multiple banners in one fieldSet" says only the first renders. A scan of the current pages found:

| Page | fieldSet | Dropped widget | Effect |
|---|---|---|---|
| shellOrgManager | `patternsFieldSet` | `emptyStateMsg` | "No shell org patterns found" never shows |
| shellOrgManager | `roleAssignmentsFieldSet` | `rolesEmptyMsg` | "No shell role assignments found" never shows |
| adminProvisioning | `newRoleFieldSet` | `activeNote` | note under the form never shows |
| assignableRoleManager | `addNewRoleSection` | `activeNote` | same |

**Design.**

- Empty states: replace each richText with a `text` widget that has `visible`, in the same fieldSet. That is the confirmed pattern for conditional messages: `patternsEmptyText`, `rolesEmptyText`, `"enabled": false`, with the same `visible` expression and plain-text `value`.
- `activeNote`: move it into its own `layoutSection` `activeNoteSection` > `fieldSet` `activeNoteFieldSet` (`"title": "Before you submit"`), placed straight after the form section. Keep the id `activeNote`.

**Tests.**

- Static: new **error** `richTextPair` when a fieldSet has two or more richText children.
- Manual: open an application with no patterns in Shell Org Manager and see the empty message. See the note on both request forms.

### N3. newShellOrg doesn't enforce the weekday rule its guide promises (P1, S)

**What I found.** `guideEffectiveDate` on `newShellOrg.pmd` says weekends "will be rejected". The page's `onSubmit` only checks the year (hard-coded 2026–2027), and the page doesn't include `comsValidations.script`. `newShellOrgPattern.pmd` does check `comsValidations.isWeekday`.

**Design.**

- Add `"include": ["comsValidations.script"]` at the page root, not inside `presentation` (the static check `protectedKey` enforces that).
- In `onSubmit`, inside the `else` branch for `effectiveDate`, add:
  `if (!comsValidations.isWeekday(effectiveDate.value)) { effectiveDate.setError(comsValidations.errorWeekday()); valid = false; }`
- Replace the hard-coded year check with `comsValidations.isCurrentOrFutureYear` / `errorYear()` to match the pattern page. Then update the guide text: "this year or next" instead of "2026 or 2027" (Q4).
- Mirror the check in `effectiveDate.onChange` the way newShellOrgPattern does.

**Tests.**

- Static: when a page's date guide text contains "weekday", the page must reference `isWeekday`.
- Manual: a Saturday shows an error on Next; Monday passes.

### N4. Orphan components (P2, S)

Nothing navigates to these:

- `landingPage.pmd`: an old card dashboard. Not in the hub; nothing links to it.
- `iscErrorPage.pmd`: not in `errorPageConfigurations` and not linked. The SMD can map a status code to only one page.
- Cards: `AppContextCard`, `StatusGuideCard`, `QuickLinksCard` (unused). `ShellOrgReceiptCard` and `ShellOrgPatternReceiptCard` are unused until R16.
- `shellOrgManager.pmd` includes `comsCardGenerator.script` but never calls it.

**Design.** The product owner decides (Q7). Default: delete `landingPage`, `iscErrorPage`, `AppContextCard`, `StatusGuideCard`, `QuickLinksCard` and the unused include. Each deleted page also drops its AMD task. Pages count toward the 75-page limit and every file is upload weight.

**Tests.** Static warning `orphan`:

- an AMD task that no page, card, hub, flow, wizard, SMD error mapping or BP route references, other than `home`
- a card that no page uses

---

## Recommendations from the PDF

### R1. guide tooltips on complex fields (P1, S)

**Status: Partly.** Guides exist on:

- newShellOrg: `organizationCode` (text), `effectiveDate` (date)
- newShellOrgPattern: `attribute1/2/3/5` (text), `effectiveDate` (date)
- manageShellOrgStatus: `currentStatusDisplay` (readOnlyText)
- assignableRoleManagerMaintain: `maintainAction` (dropdown), `workdayRoleDropdown` (instanceList), `denialReason` (textArea)

There are none on shellOrgManager, iscRoleRequestsView, assignableRoleManager or adminProvisioning.

**Platform limit.** CLAUDE.md "guide attribute — rendering behavior": guides on `text`/`date`/`number` in `side_align_left` fieldSets deploy but render no icon. Guides render on `dropdown`, `instanceList`, `textArea` and `fileUploader`. No page in this repo sets `labelPosition`, so whether the default layout renders text/date guides is unknown. **Live check needed:** open newShellOrg and look for the "?" beside Organization Code.

The PDF's claim that guides work on text, currency, dropdown, date and number fields is contradicted by CLAUDE.md. The PDF's `_comment_linkText` / `_comment_linkUrl` are underscore attributes, which the static suite rejects. Guide link attributes: **VERIFY ON developer.workday.com**.

**Design.** Keep the existing guides; they're harmless. Add guides only on widget types known to render. Every guide uses `{ "type": "guide", "id": "<name>Guide", "title": ..., "text": ... }` (ids end in the type, as the naming rule requires).

| Page | Widget (type) | New guide id | Text (draft, product owner to confirm) |
|---|---|---|---|
| assignableRoleManager | `selectedShellOrgId` (instanceList) | `customOrgGuide` | The shell organization the new role is scoped to. The role name is built from this organization's code. |
| assignableRoleManager | `delegatedRoles` (instanceList) | `delegatedRolesGuide` | Existing roles in this application that the new role may assign. Only roles under the same application code are valid. |
| assignableRoleManager, adminProvisioning | `fuhPicker` (instanceList) | `fuhPickerGuide` | Pick a Functional Unit Hierarchy to limit where the role applies. Leave empty for the whole university (Academic Unit – University of British Columbia). |
| assignableRoleManager, adminProvisioning | `academicUnitPicker` (instanceList) | `academicUnitPickerGuide` | Pick an Academic Unit instead of an FUH. Pick one or the other, not both. |
| assignableRoleManager, adminProvisioning | `positionsList` (instanceList) | `positionsListGuide` | Positions that will hold the role once it's approved and created. Search by name or position ID (P-00010). |
| adminProvisioning | `applicationDropdown` (dropdown) | `applicationDropdownGuide` | The application whose AAA (Organizations and Roles Assignment Administrator) role you're requesting. |

For text/date fields whose guide doesn't render, the same sentence goes in `helpText`. `organizationCode` already has helpText. For the rest, use a richText ⓘ banner, at most one per fieldSet (N2).

Shell Org Manager and the ISC queue need explanations on column headers. Guides on grid `column` objects aren't documented (**VERIFY ON developer.workday.com**), so those use banners (R24, R27).

**Tests.**

- Static: the warning `guideNoRender` lists guides on text/date/number/readOnlyText. Every guide id is unique per page and ends in `Guide` (old ids like `guideOrgCode` can stay or be renamed).
- Manual: for each page, a screenshot shows the icons render.

### R2. checkBox acknowledgement (Done)

- `manageShellOrgStatus.pmd` `confirmStatusChange` (checkBox, required), and `onSubmit` blocks when it's unticked.
- `deleteAssignableRole.pmd` `confirmDeleteCheckBox`, enforced in `onSubmit`.

The PDF's "Submit enabled only after ticking" can't be done: OK is a framework button. The onSubmit block is the equivalent.

Manual checklist: submit unticked and see the field error.

### R3. pageActionButton (Won't do)

The PDF's own Part 5 says pageActionButton is for edit pages with PMD scripting only, always gray, and doesn't navigate ("use button with taskReference instead"). The success pages are VIEW pages whose primary action is navigation. The example `clipboard.write(...)` isn't on the built-in function list in CLAUDE.md. Keep `"action": "PRIMARY"` buttons.

### R4. External links on home (Done)

`home.pmd` has `additionalLinks` "Resources" with Submit a Helpdesk Ticket (ServiceNow) and RBAC Rolename by Application (Confluence). UPDATE_NOTES.txt records that an earlier "Quick Actions" additionalLinks block was removed at the user's request, so add more only if asked (Q3).

### R5. Deferred tab endpoints in Shell Org Manager (Won't do)

CLAUDE.md "Deferred endpoints — WQL tab grids NEVER fetch": a `deferred` WQL endpoint feeding a grid `rows` binding never loads. Also, all three endpoints (`shellOrgPatterns`, `shellRoles`, `allShellOrgs`) feed the Summary tab, which is the first tab. If the page is slow, the fix is narrower WQL, not deferral.

### R6. Error page guidance (P1, S)

**Status: Partly.** `errorPage.pmd` has per-code `text` messages (401/403/404/default) and Home + Shell Org Manager LINK buttons. The SMD maps 400/401/403/404/408/500/503 to it. `iscErrorPage` is orphaned (N4).

**Design (errorPage).**

- `errorSummary403` value: append "If you need access, raise a ticket from the ECO-COMS home page: Resources → Submit a Helpdesk Ticket." Buttons can only use `taskReference` or `workdayTaskReference`, not external URLs. Whether richText `<a href>` links work is **VERIFY**.
- In `navSection`, add LINK buttons shown only for 404 (`"visible": "<% queryParams.errorCode == '404' %>"`, the same pattern as deleteAssignableRole's nav buttons):
  - `auditLogButton` → `auditLogViewer`
  - `iscRequestsButton` → `iscRoleRequestsHub`
  - `roleRequestsButton` → `assignableRoleManagerView`
  - `aaaRequestsButton` → `adminProvisioningView`
- Note: users without the target page's security domain are redirected (CLAUDE.md "Security domain enforcement"). That's acceptable.

**Tests.**

- Static: the existing `queryParams` and taskRef checks cover it.
- Manual: open `/errorPage?errorCode=404` and `?errorCode=403`.

### R7. imageCard on error pages (P3, S)

`imageCard` is one of the documented card body types, but its attributes aren't in CLAUDE.md or the repo: **VERIFY ON developer.workday.com**. An image also needs an asset. `presentation/assets` exists, but how a card references an asset is unknown. Low value; the `ubcLogo.pod` richText text logo can go on the error page instead (`{ "type": "pod", "podId": "ubcLogo" }` in a layoutSection; pods are already used in footers).

### R8 / R9. editWizard for the create forms (Done, adapted)

`createShellOrgWizard.pmd` and `createShellOrgPatternWizard.pmd` wrap newShellOrg and newShellOrgPattern as one step each, with `summarySettings` "Review & Submit" and a `conclusion` to the success page. hubLanding and shellOrgManager link to the wizards.

The PDF's 3-step split doesn't fit the platform:

- **Steps can't share data** (CLAUDE.md editWizard): the name preview and the duplicate check need the application and the code on the same page.
- The run-and-verify `onSubmit` needs every value.

Keep one step. Known gap: the Review step shows the page-load value of the `readOnlyText` preview, not the `setValue`'d one (CLAUDE.md open question). Workaround if wanted: hide `orgNamePreview` on Review. How to tell Review from the step is **VERIFY**, so leave it unless the product owner objects.

### R10. Confirmation step / "creates a live org" note (P1, S)

**Status: Partly.** The confirm pages are deleted, so the warning belongs on newShellOrg (and newShellOrgPattern).

**Design.** A new `layoutSection` `liveOrgNoticeSection` goes between `aboutSection` and `formSection`. It holds a `fieldSet` `liveOrgNoticeFieldSet` with `"title": "Before you submit"`, containing one richText:

```json
{ "type": "richText", "id": "liveOrgNoticeRichText", "enabled": false,
  "value": "<span style=\"color:#B45309;font-size:11px;font-weight:700\">⚠ </span><span style=\"color:#374151;font-size:11px\">Submitting creates a live Custom Organization in Workday. It can't be deleted afterwards, only inactivated from Shell Org Manager.</span>" }
```

Use the same on newShellOrgPattern with `livePatternNoticeRichText`.

**Tests.**

- Static: `richTextPair` (N2) stays clean.
- Manual: the notice shows on the wizard step and not on Review (Review shows fields only).

### R11. Delete → Withdraw (Done, in progress)

**Status.** As of 17:09 UTC the page:

- is titled "Withdraw Assignable Role Request"
- has standard OK/Cancel (`standardEditButtonsHidden` removed) and `cancelOverride` → home
- lets you withdraw only your own Pending request (onSubmit check)
- POSTs `workday-bp events/<reviewEventWid>/cancel` when the request has a review event
- DELETEs the record (plus a DELETE audit) only when there's no review event

That matches CLAUDE.md ("A record linked to a BP event can't be deleted"; DenyRoleRequest is paired with Cancel). An editWizard isn't needed: step 1 navigates with `queryParams`, and wizard steps can't pass data.

**To finish.**

1. The requester must be allowed to **Cancel** on the BP security policy. Today only HR Administrator has Cancel (ECO-COMS-NOTES). The person changes the policy; the assistant doesn't (Q6).
2. **Vocabulary:** a withdrawn request becomes `Denied` with a `DENY` audit written by DenyRoleRequest, which reads as "denied by ISC" (Q5). Option: add `WITHDRAW` to the fixed vocabulary, and have DenyRoleRequest write it when the event was cancelled rather than denied. How an orchestration tells cancel from deny is **VERIFY** ("Reference: Business Process Global Functions").
3. The `cancel` body is `{ "comment": "..." }` (developer.workday.com "Events REST APIs", per CLAUDE.md). Confirm the page sends it.

**Tests.**

- Static: no `KNOWN_ISSUES` entry left.
- Full suite, a new test `Withdraw.ownPending`, run as the requester:
  1. create a TEST request and start its review
  2. cancel the event the way the page does
  3. within 3 min, expect `status: Denied`, `active: false` and one audit record (DENY, or WITHDRAW if adopted)
  4. a second request with no event is DELETEd and has a DELETE audit
- Manual: as a non-requester, the page refuses with "not one of your pending requests".

### R12. radioGroup for Approve/Deny (P3, S, optional)

The decision now happens in the Workday inbox (BP step 2). `assignableRoleManagerMaintain` is only reached from the ISC queue's "Maintain" button, shown only when `reviewEventWid` is empty (legacy requests).

`radioGroup` isn't in CLAUDE.md or the repo, so the PDF's attributes (`hideDisplayOption`, `getSelectedEntries()`) are **VERIFY ON developer.workday.com**.

If built: replace `maintainAction` (dropdown) with `maintainActionRadioGroup`, keep the hidden `selectedAction`, and keep the exclude logic on the outbound endpoints. Better option: retire the page once no request lacks a review event (Q2).

### R13 / R15. Decision notes and approval guide (Done)

- `denialReason` (textArea) is bound to `denyRole.denialReason` (a TEXT field on COMSAssignableRole) and included in the DENY audit `details`.
- `guideMaintainAction` and `guideWorkdayRole` exist.
- Gap on the BP path: the Deny comment typed in the Workday inbox isn't copied to `denialReason`. Reading event comments in DenyRoleRequest is **VERIFY** (Q2).

### R14. Requester and request date on the maintain page (P2, S)

Add two widgets to `roleDetailSection` (fieldSet), after `roleNameText`:

```json
{ "type": "text", "id": "requestedByText", "label": "Requested By", "enabled": false,
  "value": "<% (!empty(selectedRole.requestedBy)) ? (selectedRole.requestedBy.descriptor ?? '') : '' %>" },
{ "type": "text", "id": "requestedDateText", "label": "Requested Date", "enabled": false,
  "value": "<% selectedRole.requestedDate ?? '' %>" }
```

The `!empty()` guard follows CLAUDE.md "Widget .value property access on null".

Manual test: open Maintain on a legacy request.

### R16 / R17. Receipt card + timestamp on the success pages (P2, M)

**Status: Partly.** `ShellOrgReceiptCard` and `ShellOrgPatternReceiptCard` exist (one parameter each, double-quoted literals, valid) but no page uses them. `manageShellOrgStatusSuccess` already shows `ShellOrgStatusReceiptCard` through flowVariables.

**Problem.** The wizard's conclusion page gets no data. editWizard can't use flows, so there are no flowVariables. Whether `conclusion.task.parameters` can reference step widget values is **VERIFY**. If it can, pass `organizationName` that way and skip the lookup below.

**Design (default: read back the user's newest ADD audit).** The orchestration writes it only after Workday accepts the change, and BO REST reads are immediate (ECO-COMS-NOTES).

- Endpoints on `newShellOrgSuccess`:
  - `selectedWorker` (COMMON `/workers/me`)
  - `auditLogCount` and `recentAuditLogs`, using the N1 offset pattern
  - all with `failOnStatusCodes`
- Below the success fieldSet, a new `layoutSection` `receiptCardSection` holding a `cardContainer` `receiptCardContainer` (the same structure as manageShellOrgStatusSuccess):

```json
{ "type": "card", "cardId": "ShellOrgReceiptCard",
  "render": "<% size((recentAuditLogs.data ?? []).filter(a => { a.objectType == 'Shell Org' && a.action == 'ADD' && (a.changedByWid ?? '') == (selectedWorker.id ?? '') })) > 0 %>",
  "parameters": "<% let mine = list:sort((recentAuditLogs.data ?? []).filter(a => { a.objectType == 'Shell Org' && a.action == 'ADD' && (a.changedByWid ?? '') == (selectedWorker.id ?? '') }), 'timestamp', false); { 'organizationName': mine[0].coName + ' | Effective ' + (mine[0].effectiveDate ?? '') + ' | Created ' + (mine[0].timestamp ?? '') + ' UTC' } %>" }
```

  The card adds nothing new, so it doesn't break the "no single quotes in .card" rule. Whether `render` short-circuits before `parameters` runs on an empty list is **VERIFY**. If not, guard `mine[0]` with `size(mine) > 0 ? ... : {'organizationName': ''}`.
- Same on `newShellOrgPatternSuccess` with `ShellOrgPatternReceiptCard`, `objectType == 'Shell Org Pattern'` and the parameter `patternName`.
- Replace the success page `copyHint` text "Check the Audit Log in Shell Org Manager…" (the audit log isn't in Shell Org Manager) with "A copy of this record is in the Audit Log."

**Risks.** Two creates in a row by the same person show the newest one, which is correct. A slow orchestration means the card shows the previous create; the timestamp makes that visible.

**Tests.**

- Static: the card is now used (N4 orphan warning gone).
- Full suite: after `AddShellOrg`, the newest own ADD audit has `coName` = the run's org (this is already checked through `launchAndVerify`; also assert `effectiveDate`).
- Manual checklist step 1: the receipt shows name, effective date and time.

### R18. Status change warning and guide (Done)

`warningFieldSet` "Status Change Warning", the amber/blue `warningMsg`, `impactFieldSet`, the `guideCurrentStatus` guide (on a readOnlyText, so it may not render; R1 live check), the checkBox, and the run-and-verify submit are all in place.

The PDF calls inactivation "irreversible", but Reactivate exists and was tested live. Keep the current wording.

### R19. Home count cards (P2, M)

`home` is a hub whose right pane is `hubLanding` (VIEW). Cards go on hubLanding; a hub body can hold only the hub. The PDF's "comsShellOrgs endpoint" and "?summary=true orchestration" don't exist and aren't needed: counts come from data the app already reads.

**Design.**

- **Cards:** reuse the nav cards so each count card keeps its footer link. In `PendingIscCard`, `ShellOrgCard` and `AuditLogCard`, add `"parameters": ["countText"]` and set `body.value` to `"<% countText ?? \"PENDING REQUESTS\" %>"`, keeping each card's current text as the fallback (landingPage, if kept, passes nothing).
- **Endpoints on hubLanding** (it has none today):
  - `pendingRequests`: BUSINESS-OBJECT `/comsAssignableRoles?limit=100` (N1)
  - `shellOrgCounts`: WQL `queryId: allShellOrgs` (the proven component)
  - `auditLogCount` + `recentAuditLogs` (N1 offset pattern)
- **Layout:** a new first `layoutSection` `dashboardSection` holding a `cardContainer` `dashboardCardContainer`, `"layout": "grid"`, with `cards`:
  - `PendingIscCard`: `"<% { 'countText': '' + size((pendingRequests.data ?? []).filter(r => { r.status == 'Pending ISC Review' })) + ' pending' } %>"`
  - `ShellOrgCard`: `'' + size((shellOrgCounts.data ?? []).filter(o => { o.code.startsWith('X:') && !o.code.contains(':PATTERN') && o.cf_active1 == true })) + ' active'` (the same filter as `summaryActiveCount`)
  - `AuditLogCard`: `'' + size(comsAuditFilters.filterLogs(recentAuditLogs.data ?? [], '1d', '', '', '')) + ' changes in 24 h'` (the script is in R29)
- **Security:** hubLanding is secured by `ManageCOMSShellOrgs`. Requests need the assignable-role domains and audit needs `ViewCOMSAuditLog`, so some users get a 403.
  - Mark those endpoints `"bestEffort": "true"`, leave 403 out of their `failOnStatusCodes`, and give each card `render` on data presence.
  - How a failed bestEffort endpoint looks to a script (`.data` null vs `[]`) is **VERIFY**; test with a user who lacks the domain.
- **Performance:** the WQL returns about 600 orgs. Option A (later): a WQL `limit=1` count with a `WHERE` on `cf_active1`, but WQL `AND` / `NOT contains` syntax is **VERIFY**. Option B (model change): `enableIndex` on COMSAssignableRole `status`, then `?status=...&limit=1` `.total`. Indexed fields generate query parameters (CLAUDE.md), but the parameter name and value format are **VERIFY**.

**Tests.**

- Static: `cardParams` (countText used), `cardQuotes` (fallback uses `\"`).
- Smoke: a new `Dashboard.counts` computes the same three numbers from the API and logs them, so the manual check has something to compare against.
- Manual: the hub shows the three numbers and they match the smoke log. As a user without `ViewCOMSAuditLog`, the hub still loads.

### R20. Home pillCard quick actions (Partly, no change)

hubLanding already has per-area buttons (Add Shell Org, Add Pattern, Open Manager, Submit New Request, View Requests, Submit AAA Role, View Pending ISC Requests, View Audit Log). `QuickLinksCard` (pillCard) is unused, which is N4. Adding pills would duplicate the buttons, and UPDATE_NOTES.txt records the user removing duplicate navigation before.

### R21. Home chartCard (P3, S)

Add `ShellOrgStatusChart` to `dashboardCardContainer`. Its parameters are already computed on shellOrgManager; copy that `parameters` expression and use `shellOrgCounts`. Only do this if the product owner wants a chart on the landing pane (Q1).

### R22. Counts above Shell Org Manager grids (P1, S)

**Status: Partly.** The Summary tab has `summaryActiveCount`, `summaryInactiveCount`, `summaryPatternCount` and the `ShellOrgStatusChart` donut.

**Design.** Put the count in each grid's `label` (already a stringScript on these grids):

- `allShellOrgsGrid`: `"<% 'Shell Organizations (' + size(allShellOrgs.data.filter(o => { o.code.startsWith('X:') && !o.code.contains(':PATTERN') })) + ')' %>"`
- `filteredShellOrgsGrid`, `patternsGrid`, `appsGrid`, `roleAssignmentsGrid`: the same, using each grid's existing `rows` expression inside `size(...)`.

The label max is 255 characters, which is fine.

Manual test: the label count equals the grid's item count.

### R23. Role assignment donut (P3, M)

New card `RoleAssignmentChart.card`, parameters `["slices", "totalText"]`:

- `"data": "<% slices ?? [] %>"`, `dataVariableName: "slice"`
- `sliceSizeDataSet.value: "<% slice[\"count\"] %>"`, `sliceColorDataSet.value: "<% slice[\"app\"] %>"`
- double quotes only

The PMD builds `slices` (one `{ 'app', 'count' }` per application code) from the `roleAssignmentsGrid` rows expression, on the Summary tab. A list-valued card parameter is allowed (mapScript supports `list`), but driving `donutChart2.data` from a parameter list is **VERIFY**. The existing card builds its list inside the card.

Risk: the role-assignment expression is large (memory limit); compute it once, ideally in a script function.

### R24. Shell Org Manager tab explanations (P2, S)

Guides on columns and tabs aren't documented. Add one "About this tab" `fieldSet` with a single richText at the top of each tab section (`patternsAboutFieldSet`/`patternsAboutRichText`, `shellOrgsAboutFieldSet`/`shellOrgsAboutRichText`; the role tab already has `roleAssignmentsNote`, so extend that text instead).

Draft text, product owner to confirm (Q10):

- *Patterns:* "A pattern is a Custom Organization named `<application>:PATTERN:<subject>:<course>:<section>:<period>`. It scopes a role to a course section."
- *Shell organizations:* "A shell organization is a Custom Organization (type = application code, subtype X:Shell) used as the organization a role is assigned on. Inactivating one doesn't remove its role assignments."
- *Role assignments:* "Each row is one role on one shell organization. Workers in the listed positions hold the role."

### R25. ISC queue summary cards (P2, M)

New generic card `CountCard.card`. This is the proven pattern: a static icon, `<% title %>` as in QuickLinksCard, and `??` with `\"\"` as in the receipt cards:

```json
{ "id": "CountCard", "parameters": ["title", "countText"],
  "header": { "title": "<% title ?? \"\" %>", "icon": "wd-accent-clipboard-checklist" },
  "body": { "type": "simpleCard", "value": "<% countText ?? \"\" %>" } }
```

On `iscRoleRequestsView`, add a new `layoutSection` `summaryCardsSection` after `descSection`, holding a `cardContainer` `iscSummaryCardContainer` with three cards. All three use the view filter (aaa/assignable) on `comsAssignableRoles.data` (N1):

- **Pending:** status `Pending ISC Review`
- **Waiting more than N days:** pending, where `date:after(date:now().minusDays(N), date:parse(r.requestedDate, 'yyyy-MM-dd'))`. N comes from the product owner (Q11). The REST shape of `requestedDate` (string vs Date) is **VERIFY**; pages show it as text today.
- **Approved this month:** `(r.approvedDate ?? '').startsWith(date:now().format('yyyy-MM'))`. Same **VERIFY** on type. The BP path sets `approvedDate` (`reviewRoleRequestAssignableRole.pmd`).

Put the counting in a script function, `comsRequestStats.script` → `countPending(list)`, `countWaiting(list, days)`, `countApprovedThisMonth(list)`, to keep the PMD readable.

**Tests.**

- Static: card checks.
- Smoke: `Requests.volume` (N1).
- Manual: compare the cards to the All Assignable Role Requests report.

### R26. ISC queue status filter (P1, S–M)

**Status: Not done.** The page has only `view=aaa|assignable` (from iscRoleRequestsHub).

**Constraint.** This is a VIEW page, so a dropdown renders read-only (CLAUDE.md "Widget types"). The page must stay VIEW for the `relatedTask` links on Positions and Review Process. So filter with buttons that reload the page with a query parameter.

**Design.**

- A new `layoutSection` `statusFilterSection` after `actionsInfoSection`, holding a `fieldSet` `statusFilterFieldSet` (`"title": "Show"`) with four buttons:
  - `pendingFilterButton`
  - `approvedFilterButton`
  - `deniedFilterButton`
  - `allFilterButton`

  Each is `"action": "AUXILIARY"`, `taskReference` `iscRoleRequestsView`, and `parameterBindings` `{ "view": "<% queryParams.view ?? '' %>", "status": "Approved" }` (status `Pending ISC Review` / `Approved` / `Denied` / `All`). Use `parameterBindings` only (static check `taskReference`).
- Grid `rows`: replace `r.status == 'Pending ISC Review'` with
  `((queryParams.status ?? 'Pending ISC Review') == 'All' || r.status == (queryParams.status ?? 'Pending ISC Review'))`.
- Title, grid label and fieldSet title: swap "Pending" for the selected status, e.g. `(queryParams.status ?? 'Pending ISC Review') == 'All' ? 'All' : (queryParams.status ?? 'Pending')`.
- Add a `text` widget `activeStatusText` in `statusFilterFieldSet` (label "Showing") naming the current filter. Whether a button's `action` can be scripted to highlight the current filter is **VERIFY**, hence the text.
- The Maintain button already hides when there's a review event; on Approved/Denied rows also hide it: `empty(role.reviewEventWid) && role.status == 'Pending ISC Review'`.
- Also send `status` from iscRoleRequestsHub's buttons? Not needed; the default is Pending.

**Tests.**

- Static: the `queryParams` lint, extended to flag bare `status`/`view` in scripts.
- Manual: each button shows only that status; combined with `view=aaa`.

### R27. ISC queue column explanations (P2, S)

In `actionsInfoFieldSet` (one richText today, `maintainActionInfo`), extend that same richText rather than adding a second:

"**AAA role**: an Organizations and Roles Assignment Administrator request from Admin Provisioning. **Assignable role**: a delegated role request from Assignable Role Manager. **Review**: opens the Workday review process; act on it from your Workday inbox."

The product owner confirms the wording (Q10).

### R28. listDetailHub for the ISC queue (P3, L; recommend against)

- `listDetailHub` isn't in CLAUDE.md beyond "a task page can be used in only 1 hub". The PDF's example (`items`, `itemVariableName`, `navigationTemplate`) and its `isCollection: "true"` string are **VERIFY ON developer.workday.com**.
- Hub task pages must be VIEW, and the proposed detail pane (assignableRoleManagerMaintain) is EDIT.
- The real decision now happens in the Workday inbox, and each row's "Review Process" link already opens the event.
- If wanted anyway, the detail pane is a new VIEW page `IscRoleRequestDetail` (PascalCase page id per the naming rule; AMD task id `iscRoleRequestDetail` to match the existing camelCase task ids, see Q12) reading `queryParams.roleId`, and it can't be used in any other hub.

### R29. Audit log filters (P2 presets / P3 custom range)

**Constraint.** auditLogViewer must stay VIEW for its related-action links (ECO-COMS-NOTES), so date pickers and dropdowns there would be read-only.

**R29a: preset buttons (P2, M).**

New script `presentation/scripts/comsAuditFilters.script`. It is pure functions with no widget access, which is allowed for scripts:

```
var parseTs = function(ts) { date:parse(ts, "yyyy-MM-dd'T'HH:mm:ss'Z'"); };
var withinDays = function(ts, days) { empty(ts) ? false : date:after(parseTs(ts), date:now().minusDays(days)); };
var rangeDays = function(range) { range == '1d' ? 1 : (range == '7d' ? 7 : (range == '30d' ? 30 : 0)); };
var appCodeOf = function(name) { name.substringAfter(':').contains(':') ? name.substringBefore(':') + ':' + name.substringAfter(':').substringBefore(':') : name; };
var filterLogs = function(logs, range, changeType, action, app) {
  let days = rangeDays(range ?? '');
  logs.filter(e => { (days == 0 || withinDays(e.timestamp, days)) && (empty(changeType) || e.objectType == changeType) && (empty(action) || e.action == action) && (empty(app) || appCodeOf(e.coName ?? '') == app) });
};
var actionSlices = function(logs) {
  ['ADD', 'INACTIVATE', 'REACTIVATE', 'ASSIGN POSITION', 'REMOVE POSITION', 'REQUEST', 'APPROVE', 'DENY', 'DELETE']
    .map(a => { { 'action': a, 'count': logs.filter(e => { e.action == a }).size() } })
    .filter(s => { s.count > 0 });
};
{ "filterLogs": filterLogs, "withinDays": withinDays, "appCodeOf": appCodeOf, "actionSlices": actionSlices }
```

Notes on the script:

- Timestamps are written as `yyyy-MM-dd'T'HH:mm:ss'Z'` by pages and orchestrations.
- `date:parse(string, format)` and `date:after` are on the built-in list. Their exact behaviour with a literal `'Z'` and UTC is **VERIFY** (test on one record first).
- `appCodeOf` matches newShellOrg's application-code logic. Codes with parentheses (`X:BPMS(ODMT)`) stay as written.

On auditLogViewer:

- Add `"include": ["comsAuditFilters.script"]`.
- In `AuditLogGrid.rows`, change `let logs = auditLogs.data ?? [];` to `let logs = comsAuditFilters.filterLogs(auditLogs.data ?? [], queryParams.range, queryParams.changeType, queryParams.action, queryParams.app);`. Everything after stays.
- A new `layoutSection` `auditFilterSection` after `aboutSection` holds three fieldSets of AUXILIARY buttons. Each button targets `auditLogViewer` and carries the *other* filters forward, for example `range7dButton`:
  `"parameterBindings": { "range": "7d", "changeType": "<% queryParams.changeType ?? '' %>", "action": "<% queryParams.action ?? '' %>", "app": "<% queryParams.app ?? '' %>" }`
  - `auditRangeFieldSet` "Time range": `rangeAllButton`, `range1dButton`, `range7dButton`, `range30dButton`
  - `auditTypeFieldSet` "Change type": `typeAllButton`, `typeShellOrgButton`, `typePatternButton`, `typeStatusButton`, `typeRoleAssignmentButton`, `typeAssignableRoleButton` (values from the fixed `objectType` vocabulary)
  - `auditActionFieldSet` "Action": `actionAllButton`, then one per action that the product owner wants (Q13). All nine would be a lot of buttons.
- In `aboutFieldSet`, add `text` widgets `activeFilterText` ("Showing: last 7 days · Shell Org · all actions") and `auditCountText` (N1).
- Filtering by application: offer it from the Organization column instead, as a LINK button per row? That would add a column, so it waits for R29b.

**R29b: custom From/To + application (P3, M–L).** This reuses the proven flow pattern (manageShellOrgStatus → manageShellOrgStatusSuccess):

- New EDIT page `AuditLogFilter` (task `auditLogFilter`) with:
  - `fromDate` and `toDate` (date)
  - `changeTypeDropdown` and `actionDropdown` (dropdown, `instanceList` literal)
  - `applicationDropdown` (dropdown, `values` from the `allShellOrgs` WQL app codes, the same expression as newShellOrg)
- An `outboundVariable` `auditFilterFlowVars` (`variableScope: flow`) with `fromDate` (`self.value.format('yyyy-MM-dd')` style), `toDate`, `changeType`, `action`, `app`. Guard each dropdown with `!empty()` (CLAUDE.md null guard).
- AMD `flowDefinitions`: `auditLogFilterFlow` = `auditLogFilterStep` (startsFlow, transition `"condition": "true"`) → `auditLogViewerFilteredStep` (`taskId: auditLogViewer`, endsFlow).
- The viewer reads `flowVariables.x ?? queryParams.x`. **VERIFY:**
  - that `flowVariables` is safely empty when the viewer is opened outside the flow
  - that a task can be both a flow step and a normal navigation target
- `filterLogs` gets `fromDate`/`toDate` arguments.
- A "Custom range…" LINK button on the viewer → `auditLogFilter`.

**Tests.**

- Static:
  - the new script is ≤ 100 KB
  - the include is at the page root
  - every viewer button uses `parameterBindings` only
- Full: none (read-only).
- Manual: each preset shows the matching subset; the count text updates; related-action icons still render (VIEW page).

### R30. Audit action donut (P2, M)

New card `AuditActionChart.card`:

```json
{ "id": "AuditActionChart", "parameters": ["slices", "totalText"],
  "header": { "title": "Changes by action", "subtitle": "<% totalText ?? \"\" %>" },
  "body": { "type": "chartCard", "chart": { "type": "donutChart2",
    "data": "<% slices ?? [] %>", "dataVariableName": "slice",
    "sliceSizeDataSet": { "name": "Count", "value": "<% slice[\"count\"] %>" },
    "sliceColorDataSet": { "name": "Action", "value": "<% slice[\"action\"] %>" },
    "showPercentLabels": true, "animateOnLoad": true } } }
```

- On auditLogViewer, put a `cardContainer` `auditChartCardContainer` in a new `layoutSection` `auditChartSection` above the tabs. Parameters:
  `"<% let f = comsAuditFilters.filterLogs(auditLogs.data ?? [], queryParams.range, queryParams.changeType, queryParams.action, queryParams.app); { 'slices': comsAuditFilters.actionSlices(f), 'totalText': '' + size(f) + ' records' } %>"`
- A list parameter driving `donutChart2.data` is **VERIFY** (same as R23). The fallback is a fixed-shape card with one numeric parameter per action, like `ShellOrgStatusChart`.

**Tests.**

- Static: `cardParams`, `cardQuotes`.
- Manual: the slice counts sum to `auditCountText`.

### R31. Export (P2, S)

The `exportNote` says "Use the grid's built-in export action", but no grid in the repo sets `excelExportEnabled`. Add `"excelExportEnabled": true` to `AuditLogGrid`; the row count is far below the ~4,000-row warning. Whether export is on by default without it is **VERIFY**. The pageActionButton "export request" is R3 (won't do).

Manual test: export downloads the filtered rows.

### R32. FUH landing (P3)

`fuhLandingPage.pmd` is a stub: a Home link and an "About FUH Administration" banner. No FUH metrics are defined anywhere, so this waits for the product owner (Q8). Possible counts come from the FUH WQL already used by the request pickers (`fuhSearch` in adminProvisioning).

### R33. Admin Provisioning summary, guides, export (P2, S)

- Guides: see R1 (`applicationDropdownGuide`, picker guides).
- `adminProvisioningView` (VIEW): add `aaaSummaryCardContainer` with `CountCard` × 3 (Pending / Approved / Denied), using the existing AAA filter `r.roleName.startsWith('Organizations and Roles Assignment Administrator')`, after N1.
- Export: not needed; the "All Assignable Role Requests" report exists.

### R34. Assignable Role Manager (P2, S)

Guides only (R1). listDetailHub: see R28. A "role usage" chart has no data source; role usage lives in Workday, not in the app.

### R35. Attachments on requests (P3, L)

The only `fileUploader` was on the deleted newShellOrgConfirm. Building this needs:

- an attachment object (5 per app limit) linked from COMSAssignableRole
- a multipart outbound endpoint (`valueOutBinding` `endpoint:defaultCollectionName`, CLAUDE.md "Multipart with attachments")
- an `attachmentList` on the review pages

`attachmentList` attributes and `multiPartFileLast` are **VERIFY**. Do it only if ISC needs evidence on requests (Q9).

### R36 / R37. dynamicSection and the other Part 2 components (Won't do)

| Component | Why not |
|---|---|
| dynamicSection | edit pages only (PDF Part 5); Shell Org Manager is VIEW; filtering is done with query parameters (R26 pattern) |
| editButton / editButtonBar inline grid edit | org status changes need the run-and-verify page with acknowledgement; inline edit would skip both |
| number | no numeric fields in the model |
| multiSelectCalendar | date ranges handled by R29 |
| loop | instanceList / grid cover current needs |
| currency, video, labeledImage | no data for them |
| SSO | tenant-level, already `sso` in the SMD |
| radioGroup (for manageShellOrgStatus, Part 5) | the action is set by the current status; a choice would allow a mismatch, the class of bug the ManageShellOrgStatus guard prevents |

---

## Test plan additions (summary)

**Static suite** (`staticSuite()` in `test/run-tests.js`):

| Check | Level | For |
|---|---|---|
| `restLimit`: BUSINESS-OBJECT collection endpoint without `limit=` | error | N1 |
| `richTextPair`: two or more richText children in one fieldSet | error | N2 |
| weekday guide text ⇒ page references `isWeekday` | error | N3 |
| `orphan`: unreferenced AMD task or card | warn | N4 |
| `guideNoRender`: guide on text/date/number/readOnlyText | warn | R1 |
| `viewEditable`: dropdown/date/checkBox/textArea on a VIEW page | warn | R26/R29 |
| `pageActionButton` on a VIEW page | error | R3 |

**Smoke suite:**

- `Audit.volume` and `Requests.volume`: totals, warn above 100 (N1)
- `Dashboard.counts`: logs pending / active orgs / audit 24 h for the manual compare (R19)

**Full suite:**

- `Withdraw.ownPending`: withdraw then expect Denied/inactive + audit; legacy delete + DELETE audit (R11)
- the receipt data check after AddShellOrg / AddShellOrgPattern (R16)

**Manual checklist** (`test/README.md`), add:

1. Guide icons render on every page that has them (screenshot).
2. Shell Org Manager empty states and grid counts.
3. ISC queue status buttons and summary cards.
4. Audit viewer presets, count text, donut, export.
5. Success receipts after each wizard.
6. Home cards as a full user and as a user without `ViewCOMSAuditLog`.
7. Withdraw as requester and as another user.
8. Error page `?errorCode=404` / `403`.

---

## Open questions for the product owner

1. **Home dashboard:** which three numbers matter most (pending ISC, active shell orgs, audit changes in 24 h)? Is a chart wanted on the landing pane too (R21)?
2. **Legacy Maintain page:** can `assignableRoleManagerMaintain` be retired once every pending request has a review event? Should the Deny comment from the Workday inbox be copied into the request's Denial Reason?
3. **External links:** keep the two current Resources links, or add UBC Workday documentation / ISC request guidelines? If adding, which URLs? (The earlier Quick Actions block was removed at your request.)
4. **Effective date rule for shell orgs:** fixed 2026–2027, or "this year or next" like patterns? Weekdays only, as the help text says?
5. **Withdraw wording in the audit log:** keep it as DENY, or add a new WITHDRAW action to the vocabulary?
6. **Withdraw permission:** may requesters cancel their own review event? This needs Cancel for the initiator on the BP security policy, a tenant change you make.
7. **Orphans:** OK to delete `landingPage`, `iscErrorPage`, `AppContextCard`, `StatusGuideCard`, `QuickLinksCard` and the unused `comsCardGenerator` include?
8. **FUH Administration:** what should this page do? Which FUH figures or tasks belong there?
9. **Attachments:** do ISC reviewers need supporting documents on requests? If not, drop R35.
10. **Explanation text:** please confirm or correct the draft wording for patterns, shell orgs, role assignments, AAA vs assignable roles, and the guide texts in R1.
11. **ISC queue "waiting" card:** after how many days is a pending request overdue?
12. **Naming:** existing AMD task ids are camelCase (`shellOrgManager`) while the convention says PascalCase page ids. Should new pages follow the convention (`AuditLogFilter`) or match the existing camelCase ids?
13. **Audit filters:** which action buttons are worth showing? All nine may be a lot. Is a custom From/To range (R29b, more work) needed, or are the presets enough?
14. **Audit volume:** do you expect more than 100 audit records in normal use soon? If yes, N1b (WQL) moves up to P2.
