# Bulk role assignment by file: design proposal

Status: **decided 2026-10-31; built and deployed; validate mode proven live, real run reached Workday (see "Live test results").** See "Decisions" and "What was built" at the end. Written 2026-10-31 from the product owner's idea (UI phase 2, question 9): download the role assignments a person may change, edit the file, upload it, and let ECO-COMS add or remove positions, like an EIB.

Sources: developer.workday.com "Concept: Attachment Objects", "Reference: String Member Functions", "Concept: Orchestration Logic Components in Extend Apps", "Orchestration Runtime Limits", "Limits on Presentation Components" (checked 2026-10-31); this repo's IORC_0037_XFD_SEC_Assign_Remove_Role_Positions orchestration, which already does one add or remove per call and is tested live. Items marked **(verify)** are not confirmed yet.

## What the user does

1. **Download.** Open Shell Org Manager → Manage Role Assignments and click the grid's export icon, or run the report. They get one row per role, organization and position.
2. **Edit.** In Excel, add a column **Action** with `ADD` or `REMOVE` on the rows to change (and new rows for positions to add). Save as **CSV**.
3. **Upload.** A new page, **Bulk Role Changes**, takes the CSV and an effective date, then shows a **dry run**: every row, what would happen, and any errors. Nothing has changed yet.
4. **Submit.** If the dry run is clean, the user clicks OK. The batch either goes to ISC for approval or runs straight away (decision 2).
5. **Track.** A **Batches** grid shows each upload: status, rows done, rows rejected, and a link to the audit records. Each change also writes the usual ASSIGN POSITION / REMOVE POSITION audit record.

### File format (CSV, one header row)

| Column | Example | Rule |
|---|---|---|
| Role | `X:BPMS(ODMT):ROLE:ADVISORS` | must be an existing assignable role the user may manage |
| Organization | `X:BPMS(ODMT) Document Access (varies)` | must be the shell org the role is assigned on |
| Position ID | `P-00009` | must exist; ADD needs it to not hold the role yet, REMOVE needs it to hold it |
| Action | `ADD` / `REMOVE` | rows with an empty Action are ignored, so the exported file can be uploaded as is |

Excel files can't be read: there is no Excel parser in orchestrations, and `.xlsx` isn't an allowed fileUploader type by default. Users save as CSV.

## How it works

```
Bulk Role Changes page (EDIT)
  fileUploader ──► COMSBulkUpload attachment object (the CSV)
  OK ──► COMSBulkBatch record (status Draft) ──► launch BulkRoleValidate (async)
                                                     │ reads the CSV (GET attachment → asCSV)
                                                     │ checks every row, writes the results
                                                     ▼
                                     batch status Validated / Rejected + row results
Review page (VIEW): shows the dry run ──► Submit
                                                     ▼
              (decision 2) ISC approval BP ──► on approve: launch IORC_0037_XFD_SEC_Bulk_Role_Changes_From_CSV (async)
                                                     │ per row: Assign_Roles (as IORC_0037_XFD_SEC_Assign_Remove_Role_Positions does)
                                                     │ per row: audit record
                                                     ▼
                                     batch status Completed / Partly failed
```

### New components

| Component | Purpose | Limit impact |
|---|---|---|
| `COMSBulkUpload` attachment object | holds the uploaded CSV (field `batch` → COMSBulkBatch) | 1 of 5 attachment objects |
| `COMSBulkBatch` business object | one record per upload: status, effective date, uploaded by, counts, error summary, review event | 1 of 20 business objects |
| `COMSBulkRow` business object | one record per CSV row: role, org, position, action, result, message | 1 of 20 |
| `BulkRoleValidate` orchestration (FlowAsync) | parse + check, no Workday changes | |
| `IORC_0037_XFD_SEC_Bulk_Role_Changes_From_CSV` orchestration (FlowAsync, or BP-triggered) | make the changes | |
| `bulkRoleChanges` (EDIT), `bulkRoleBatch` (VIEW) pages | upload, review, track | 2 of 75 pages, 2 of 20 tasks |
| Optional: a BP "Review COMS Bulk Role Change" | ISC approval of a batch | 1 of 5 business processes |

### Why asynchronous

A page that launches a synchronous orchestration gives it 25 seconds. One Assign_Roles call takes 1–3 seconds, so a synchronous run would stop after roughly 10 rows, part-way through, with no error. Asynchronous orchestrations can run up to 60 minutes in production. The page saves the batch and returns at once; the batch page shows progress.

### Checks before anything changes (the dry run)

For each row:

- Action is ADD or REMOVE (other values are skipped).
- The role exists and is an `X:` role; the organization matches the role's assignment.
- The person uploading is allowed to manage that application's roles (same rule as the Manage Role Assignments page; **(verify)** how to check this inside an orchestration, probably by the security domain on the launch plus a check that the org code is in their application).
- The position exists; ADD: not already assigned; REMOVE: currently assigned.
- No duplicate rows; at most **200 rows** per batch (decision 4).

A batch with any rejected row can't be submitted; the user fixes the file and uploads again.

### Applying

- One Assign_Roles call per row, the same SOAP request IORC_0037_XFD_SEC_Assign_Remove_Role_Positions sends (`Position_ID` to add, the assignee WID to remove), so the behaviour is already proven.
- A failed row is recorded with Workday's message and the run continues (decision 3). Rows that succeeded stay done: Workday role changes can't be rolled back.
- Every change writes its own audit record, so the Audit Log and its filters work unchanged. The batch record links to them.
- Throttling: a short delay between calls, and a retry with back-off on HTTP 429.

## Effort and risk

- About **1–2 weeks** including tests: two orchestrations, three model components, two pages, tests for the parser and for a 3-row batch (add, remove, rejected), and docs.
- **Risk:** this changes security roles in bulk. Mitigations: the dry run, the 200-row cap, ISC approval (if chosen), one audit record per change, and the existing orchestration guards (mode, required IDs, X: prefix).
- **Unverified pieces to prove first** (a half-day spike before committing): reading an uploaded attachment's content in an orchestration with `asCSV()`; FlowAsync launched from a page; how the orchestration checks the uploader's application rights.

## Decisions needed

1. **Who may use it?** Everyone who can use Manage Role Assignments, or only ISC/admins?
2. **Approval:** should every batch go through ISC (a new business process, like role requests), or run straight after a clean dry run? Recommended: ISC approval for batches over a threshold (e.g. more than 10 rows), straight through below it.
3. **Failures:** keep going and report failed rows (recommended), or stop at the first failure?
4. **Batch size cap:** 200 rows OK?
5. **File:** is the 4-column CSV above enough, or do you need other columns (for example a comment per row, or an effective date per row)?
6. **Download:** is the grid's Excel export enough as the starting file, or do you want a dedicated report with exactly these 4 columns?

## Decisions (product owner, 2026-10-31)

1. **Who:** anyone with access to the page (security domain Manage: COMS Shell Organizations, the same as Manage Role Assignments).
2. **Approval:** no ISC approval of batches.
3. **Failures:** keep going; a rejected row is recorded as FAILED with Workday's message.
4. **Cap:** 200 rows per file.
5. **Columns:** everything the Assign_Roles call needs, so ADD and REMOVE rows can be mixed in one file.
6. **Starting file:** the grid export is enough.
7. **Validate vs real run** (added 12:17): the upload page has both. Validate only checks every row and changes nothing; a real run applies the rows.

## What was built (first version)

| Piece | What it does |
|---|---|
| `model/COMSBulkUpload.attachment` | The uploaded CSV plus batchRef, runMode, status, effectiveDate, uploader, timestamps and a status message |
| `model/COMSBulkRowResult.businessobject` | One record per processed row: action, role, organization, position, result (VALID / INVALID / DONE / FAILED) and message |
| `orchestration/IORC_0037_XFD_SEC_Bulk_Role_Changes_From_CSV.orchestration` | **Asynchronous** (`.maya.FlowAsync`, start `StartAsync`, end `EndEmptyMaya`, shapes copied from Orchestration Builder's own source). Finds the upload by batchRef, marks it Running, reads the file (`GET` the attachment without an Accept header → `asCSV().rows()`), rejects files over 200 rows, then per row: VALIDATE → records VALID/INVALID; APPLY → calls Assign_Roles (the same SOAP as IORC_0037_XFD_SEC_Assign_Remove_Role_Positions), records DONE/FAILED, and writes an ASSIGN/REMOVE POSITION audit record for each success. Marks the upload Validated or Completed. Secured by Manage: COMS Shell Organizations. Generated by `tools/build_bulk_orchestration.py` from the repo's own node prototypes. |
| `bulkRoleTemplate` (VIEW) | One row per role × organization × position with the 8 columns below and Excel export |
| `bulkRoleChanges` (EDIT) | CSV upload, effective date (weekday, this year or next), **Real run** checkbox (unticked = validate only) plus a confirmation tick for real runs. OK uploads the file, launches the orchestration and goes to the results page. |
| `bulkRoleResults` (VIEW) | The user's uploads (newest first, status) and the row results of the selected one, with counts and Excel export |
| Home | A "Bulk Role Changes" section: Download Template, Upload File, View Results |

### File columns (in this order)

`Action` (ADD / REMOVE / empty) · `Role` · `Role WID` · `Organization` · `Organization WID` · `Position` · `Position ID` (needed for ADD) · `Assignee WID` (needed for REMOVE). Rows with an empty Action, and the header row, are ignored.

### Added after the first live run (2026-10-31)

- **Position lookup.** Each ADD row's Position ID is looked up in `allPositions` (the WQL the single-change page uses). An unknown ID is INVALID ("Position ID … was not found in Workday") in both validate and real runs, so it never reaches Assign_Roles. An unfilled position is VALID but flagged in the message.
- **Apply a validated upload** (`bulkRoleApply`, the **Apply** button on the results page): runs the stored file for real with the effective date chosen at validation. Allowed only when the status is Validated and no row is INVALID. It marks the upload Queued / APPLY and launches the orchestration; the results page then shows only the rows of the latest run.
- **Refresh** on the results page, which also defaults to an upload that is still Uploaded, Queued or Running.

### Live test results (2026-10-31)

Confirmed on ubc_wcpdev2:

- Upload with metadata set in `onMultiPartSend`; `csv` is an allowed file type.
- Asynchronous launch from an outbound endpoint; `data("start","queryParams").getParam(...)` works in a FlowAsync.
- `?batchRef=` on the indexed field filters the collection.
- `GET` on the attachment (no Accept header) → `asCSV().rows()`; the header row and rows with an empty Action are skipped.
- Validate run: VALID / VALID / INVALID as expected, status Validated.
- Real run: Assign_Roles was called per row and each rejection was recorded as FAILED with Workday's message, status Completed. The deliberate bad REMOVE (an all-zero WID) failed as intended. The ADD of P-00012 failed with "The provided Role Assignee is not valid as an Event Target Role Assignee"; the role was unchanged. The position lookup above was added in response.
- Validate run after the lookup (BULK202610312008303aa555): P-00012 INVALID "not found in Workday" (it doesn't exist; that was the cause), P-00010 VALID, P-99999 INVALID.
- The Apply page loads a stored upload with its status, effective date and VALID/INVALID counts (1 / 2 here). OK was not clicked.

- Real runs that succeed (2026-10-31, effective 2026-10-30, role X:BPMS(ODMT):ROLE:ADVISORS):
  - **Apply button path:** validated a REMOVE of P-00010 (BULK202610312106013aa555), then applied it from the Apply page. Row DONE, upload Completed, P-00010 gone from the role in Workday, and a REMOVE POSITION audit record ("Bulk upload BULK202610312106013aa555: removed position P-00010 ...") at 21:09:07Z. The Apply page refused OK without the confirmation tick.
  - **Direct real run:** uploaded an ADD of P-00010 with Real run ticked (BULK202610312111053aa555). Row DONE, P-00010 back on the role; the role ended exactly as it started (P-00009, P-00010, P-00011, P-00139, P-00759).
  - The Position cell was written the way Excel saves it, quoted with a comma inside (`"P-00010 Director, Payroll Operations - Beth Liu"`), with CRLF line ends: `asCSV()` handled both.
- Bug found and fixed: a validation error on the upload and Apply pages stayed after the user fixed the cause, blocking OK until a reload. Both pages now clear their errors at the start of each submit, and the confirmation ticks clear theirs when changed.
