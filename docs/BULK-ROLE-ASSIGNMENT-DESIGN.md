# Bulk role assignment by file: design proposal

Status: **proposal, waiting on the decisions at the end.** Written 2026-10-31 from the product owner's idea (UI phase 2, question 9): download the role assignments a person may change, edit the file, upload it, and let ECO-COMS add or remove positions, like an EIB.

Sources: developer.workday.com "Concept: Attachment Objects", "Reference: String Member Functions", "Concept: Orchestration Logic Components in Extend Apps", "Orchestration Runtime Limits", "Limits on Presentation Components" (checked 2026-10-31); this repo's AssignRolePositions orchestration, which already does one add or remove per call and is tested live. Items marked **(verify)** are not confirmed yet.

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
              (decision 2) ISC approval BP ──► on approve: launch BulkRoleApply (async)
                                                     │ per row: Assign_Roles (as AssignRolePositions does)
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
| `BulkRoleApply` orchestration (FlowAsync, or BP-triggered) | make the changes | |
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

- One Assign_Roles call per row, the same SOAP request AssignRolePositions sends (`Position_ID` to add, the assignee WID to remove), so the behaviour is already proven.
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
