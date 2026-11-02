# ECO-COMS user guide

ECO-COMS (Custom Organization Management System) is a Workday Extend app for role-based access control (RBAC). Use it to:

- create **shell organizations** (Custom Organizations such as `X:CLW:ORG:ANY`) and **shell org patterns** (such as `X:CLW:PATTERN:MATH:MATH_V:303:951:2026W1`) in Workday
- inactivate or reactivate those organizations
- add or remove the positions assigned to a role on a shell organization, one at a time or many at once from a CSV file
- request new **assignable roles** and **AAA** (Organizations and Roles Assignment Administrator) roles, which ISC reviews in a Workday business process
- see every change in the **Audit Log Viewer**

Part 1 is for requesters. Part 2 is for ISC reviewers and approvers.

---

## Part 1: Requesters

### Getting around

Open the app from Workday. The **ECO-COMS** hub opens on the **RBAC Hub** page. The left pane has:

- **RBAC Hub**: the main page. At the top, five cards: **Needs My Attention** (your own requests and bulk uploads), **Shell Org Manager** (active shell organizations), **ISC Queue** (pending and overdue), **Audit Log** (changes in the last 24 hours) and the **Shell Org Overview** donut (active vs inactive). Each card's link opens that area. Below them are three action cards: **Shell Organizations**, **Bulk Role Changes** and **Role Requests**.
  - **Shell Organizations**: **Open Shell Org Manager**, **Add Shell Org**, **Add Pattern**
  - **Bulk Role Changes**: **Upload File**, **Download Template**, **View Results**
  - **Role Requests**: **View My Requests**, **Submit New Request**, **View AAA Requests**, **Submit AAA Role Request** (the ISC Queue has its own card above)
- **FUH Administration**: information about Functional Unit Hierarchy organizations (no actions yet).
- **Resources**: **Submit a Helpdesk Ticket** and **RBAC Rolename by Application** (external links).

Every page has one back link at the top (for example **← Home** or **← Shell Org Manager**). What you see depends on your security domains (see [Troubleshooting](#troubleshooting)).

In Workday's own search the app's tasks are **Shell Org Manager**, **Audit Log Viewer**, **ISC Queue**, **Submit Assignable Role Request**, **Submit AAA Role Request** and **Withdraw Role Request** (renamed 2026-11-01; the old names Assignable Role Manager, Admin Provisioning and All Pending Role Requests ISC no longer match).

All times in the app are **Pacific time**, to the minute, with the zone shown (for example `2026-10-31 18:31 PDT`; `PST` in winter).

### Shell Org Manager

**Open Shell Org Manager** opens **ECO-COMS: Shell Org Manager**. Its sections:

- **Summary**: **Active**, **Inactive** and **Patterns** counts (for the application you picked with **Manage**, or all applications), **Quick Actions** to add an org or a pattern, and the **Shell Org Overview** donut.

Each tab after Summary starts with an **About This Tab** note. Workday shows the number of rows ("n items") next to each grid's title.

- **Application Patterns**: the **Applications** grid. Click **Manage** on an application to see only its patterns and orgs; **← Back to Applications** returns to the full view. The **Shell Org Patterns** grid shows each pattern's name, code and status, with an **Inactivate** / **Activate** button.
- **Application Shell Organizations**: every shell org with its status and a **Manage** button.
- **Manage Role Assignments**: one row per role on one shell org, with its positions and workers, and a **Manage** button.

Only pattern codes that start with `X:` and contain `:PATTERN:` are listed.

### Create a shell organization

1. On the RBAC Hub, click **Add Shell Org**. The **Add New Shell Organization** wizard opens.
2. On **Organization Details**:
   1. **Application**: pick the application the org belongs to.
   2. **Organization Subtype**: **X:META** for an application's meta organization, **X:SHELL** for a shell organization that roles are assigned on.
   3. **Organization Code**: enter the suffix only, without spaces or special characters. **Generated Organization Name** shows the full name, `ApplicationCode:OrganizationCode` (for example `X:CLW:ORG:ANY`).
   4. **Effective Date**: the date the org becomes available: a weekday (Monday to Friday) in this year or next year. A weekend or another year shows an error as soon as you leave the field, and again on **Next**.
3. Click **Next**, check the **Review & Submit** summary, then click **OK**.
4. ECO-COMS creates the org in Workday and checks that it now exists. If it does, **Shell Organization Created** opens with a receipt card (organization name, effective date, and when it was created) plus **Add Another Organization** and **View in Shell Org Manager**. The receipt shows the newest organization *you* created.

The **Before You Submit** note on the form is a reminder that the organization is live straight away and can only be inactivated afterwards, not deleted.

**Field help:** click the **?** in the page banner ("Start guided tours") to show a **?** beside the fields that have help, then click a field's **?** to read it.

The page stops you if the code already exists ("An organization with this code already exists: ...") or if Workday refused the request (see [Troubleshooting](#troubleshooting)).

### Create a shell org pattern (any application except Clockwork)

Every application has its own pattern format: a prefix and its own fields. The format lives on the application's record, so a new application needs a new record, not a new page.

1. Open **Add Pattern (Other Apps)** in Shell Org Manager's **Quick Actions**, or select an application in Shell Org Manager and click **Add Pattern**.
2. Without an application selected, the page lists the applications that have a pattern format (the same 15 as Shell Org Manager's Application Patterns tab). Click **Add Pattern** on a row.
3. The form shows that application's fields, with their names and examples. Some applications have more than one prefix (for example X:ADM: AAP, BBAE, BBAREADER, KEYCLOAK): pick it under **Pattern Prefix**.
4. Fill the fields. Each one is checked as you type, and **Pattern Name Preview** shows the name: `APPLICATION:PREFIX:field:field`. A blank field becomes `*` (any), except fields marked required (e.g. Subject for Assessment Outcomes).

   | Application | Prefix | Fields | Example |
   |---|---|---|---|
   | X:BPMS(AOC) Final Grades Submission | CP | Subject (required, e.g. `MECH_V`), Course (`100`, `100A`, or a start plus `*`, e.g. `1*`) | `X:BPMS(AOC):CP:MECH_V:1*` |
   | X:OAM Online Advising Management | ORG | Organization | `X:OAM:ORG:AA` |
   | X:ADM Admissions | AAP, BBAE, BBAREADER, KEYCLOAK | Role Name | `X:ADM:BBAE:SAUDER` |
   | X:BPMS(ADHC) Ad-Hoc Communication | COMM, PRIV | Role Name | `X:BPMS(ADHC):PRIV:DRC` |
   | X:BALT, X:BPMS(ASMT), X:BPMS(LFSM), X:LLIS(CPE), X:LLIS(EXL), X:SET, X:PHA | ORG | Role Name | `X:BPMS(ASMT):ORG:REGENT` |
   | X:BPMS(CRSS) / X:BPMS(DOCV) / X:BPMS(SDS) | CFG / DOCUMENT / APPLICATION | Role Name | `X:BPMS(CRSS):CFG:MGMNT` |

   Role Name and Organization: capital letters, digits, `_` or `-`, up to 30, optionally ending in `*`.
5. Pick the **Effective Date** (a weekday, this year or next) and click **OK**. The pattern is created in Workday with subtype **X:SHELL**, and **Pattern Created** opens.

X:SET and X:PHA have no organization type in Workday yet, so Workday refuses their patterns until those types exist.

### Create a Clockwork shell org pattern

1. On the RBAC Hub, click **Add Pattern (Clockwork)**. The **Add New Shell Org Pattern** wizard opens. (From the other applications' page, choose X:CLW and click **Open the Clockwork Pattern Form**.)
2. On **Pattern Details**, pick the **Application** first. Fields you fill before choosing an application show "Please select an Application before entering pattern attributes."
3. Fill the pattern attributes. **Pattern Name Preview** updates as you type, and each field is checked as you go.

   | Field | Rule | Examples |
   |---|---|---|
   | **Subject** | Exactly 4 uppercase letters | `MATH`, `CPSC`, `COMM` |
   | **Course** | 4 uppercase letters, optional `_` + letter, a colon, 3 digits, optional letter suffix | `COMM:300`, `COMM:300A`, `COMM_V:300`, `COMM_V:300A` |
   | **Section** | 3 digits. If **Course** ends with a letter: an uppercase letter, `_`, and 3 digits | `201`, `951`; `A_900` |
   | **Course Reference** | No rule. Not part of the generated name | `MATH_V` |
   | **Academic Period** | Current or next year, then `S`, `W1` or `W2` (Summer, Winter Session 1, Winter Session 2) | `2026S`, `2026W1`, `2027W2` |
   | **Effective Date** | A weekday, in the current or next year | |

   The Section tooltip says a `_V` course takes 3 digits and a letter (for example `951L`). The page enforces the rule in the table instead (to confirm which is intended).

   The page says a blank field becomes a wildcard (`*`). The OK check validates every field, so a blank field may be rejected (to confirm).

4. The generated name is `<ApplicationCode>:PATTERN:<Subject>:<Course>:<Section>:<Academic Period>`, for example `X:CLW:PATTERN:MATH:MATH_V:303:951:2026W1`. If that pattern already exists, you see "A Shell Org Pattern with this name already exists: ...".
5. Click **Next**, check **Review & Submit**, then click **OK**. The summary may show the pattern preview as it was when the page loaded. The name that is saved is built from the fields you entered.
6. ECO-COMS creates the pattern in Workday and checks that it exists. If it does, **Pattern Created** opens.

### Inactivate or reactivate an organization

1. Open **Shell Org Manager**.
2. Find the org:
   - a shell org: **Application Shell Organizations** → **Manage** on its row
   - a pattern: **Application Patterns** → **Manage** on the application → **Inactivate** or **Activate** on the pattern
3. The **ECO-COMS: Change Status – <code>** page shows **Current Status** and **New Status**.
4. Read the warning. **Inactivating does not remove role assignments that use this org.** Check in Workday that no active role assignment depends on it before you continue.
5. Enter the **Effective Date**.
6. Tick the confirmation box, then click **OK**.
7. **Status Updated** opens if Workday accepted the change.

**Effective dates in the future.** A change dated in the future is scheduled in Workday. Until that date the org is still active, so Shell Org Manager keeps showing **✓ Active**.

**Why a second change can be rejected.** Workday allows only one pending status change per org. If the org already has a future-dated change, another one fails with "conflicting events (in progress or future events)", and ECO-COMS shows "Workday rejected this status change...". Choose an effective date after the scheduled change, or wait until it has taken effect.

### Add or remove positions on a role

1. In **Shell Org Manager**, open **Manage Role Assignments** and click **Manage** on the role and org row.
2. **ECO-COMS: Manage Role Assignment – <role>** shows the **Current Assignment** (role, org, current positions).
3. Under **Change Positions**:
   - **Positions to Add**: search by position name or ID (for example `P-00010`). You can pick more than one.
   - **Positions to Remove**: pick from the positions currently assigned.
   - **Effective Date**: required.
4. Click **OK**. Each add and each remove runs through the Workday Assign Roles business process. **These changes can't be rescinded.** To undo one, make the opposite change.
5. After OK, **Role Assignment Updated** shows the role, the organization, the positions added and removed, and the effective date, with **View in Shell Org Manager** and **Manage This Role Again**. Each change is in the Audit Log as **Assign position** or **Remove position**.

If any change fails, the page shows "Workday rejected N of M changes...". The changes that succeeded stay in place, so check the role in Workday before you try again.

### Request an assignable role

1. On the RBAC Hub, click **Submit New Request** in the Role Requests card. The **ECO-COMS: Submit Assignable Role Request** page opens. Section **1. Pending ISC Review** lists requests still waiting.
2. In **2. Submit New Assignable Role Request**:
   1. **Custom Organization**: the shell org the role applies to.
   2. The role: either pick an existing role in **Delegated Roles**, or type a new one in **New Delegated Role** in ALL CAPS (for example `COORDINATOR`, 100 characters at most). If the new name already exists, pick it from Delegated Roles instead.
   3. **Generated Workday Role Name** is filled in for you as `<Custom Organization>:ROLE:<role>`, for example `X:ADM:ROLE:COORDINATOR`.
   4. **Effective Date**.
   5. **Positions**: at least one.
   6. **Enabled For**: pick a **Functional Unit Hierarchy** *or* an **Academic Unit**, not both. If you pick neither, Enabled For is "Academic Unit - University of British Columbia".
3. Click **OK**. The request is saved with status **⏳ Pending ISC Review** and the ISC review starts in Workday (see [After you submit](#after-you-submit-the-isc-review)).

To see your requests, use **View My Requests** on the RBAC Hub (**ECO-COMS: My Assignable Role Requests**).

### Request an AAA role

An AAA role (Organizations and Roles Assignment Administrator) decides who can manage shell orgs and submit role requests in ECO-COMS for an application.

1. On the RBAC Hub, click **Submit AAA Role Request** in the Role Requests card. **ECO-COMS: Submit AAA Role Request** opens.
2. In **2. Submit New AAA Role Request**:
   1. **Application**: required.
   2. **Enabled For**: pick a **Functional Unit Hierarchy** *or* an **Academic Unit**, not both, or leave both empty (Enabled For is then "Academic Unit - University of British Columbia").
   3. **Requested AAA Role** is generated for you: `Organizations and Roles Assignment Administrator (<Application>)`, with `, Functional Org` or `, Academic Unit` added when you pick one.
   4. **Effective Date**: required.
   5. **Positions**.
3. Click **OK**. If that AAA role already exists in Workday, the page says so and stops you from submitting a duplicate.

**View AAA Requests** on the RBAC Hub opens **ECO-COMS: AAA Role Requests**, which lists everyone's AAA requests.

The form has no Delegated Roles field. Delegated Roles appears only as a column in the requests grid (to confirm whether AAA requests should capture it).

### Withdraw a pending request

**Withdraw Request** (on the request pages) opens **ECO-COMS: Withdraw Assignable Role Request**, or **Withdraw AAA Role Request** when you come from the AAA pages. Opened from Workday search it's **Withdraw Role Request** and lists both kinds. It lists only **your own** requests that are still **Pending ISC Review**.

1. Click **Select** on the request.
2. Tick **I confirm I want to withdraw this request.**
3. Click **OK**.

ECO-COMS cancels the request's ISC review in Workday. Within a few minutes the request shows **✗ Denied** and a DENY record appears in the Audit Log. A withdrawn review can't be restarted; submit a new request if you still need the role. An older request that never started a review is deleted instead, with a DELETE audit record.

Cancelling a review needs the **Cancel** permission on the business process; the Initiator has it, so requesters can withdraw their own requests. The withdrawal comment is copied into the request's **Denial Reason**, and the DENY audit record names you.

### After you submit: the ISC review

Each request starts a **Review COMS Assignable Role Request** business process in Workday:

| Step | What happens | Who |
|---|---|---|
| 1. Role Details | The request is opened for review | Automatic |
| 2. Approve / Deny | ISC approves or denies | The approval group (not you: you can't approve your own request) |
| 3. Add Assignable Role | To Do: create the Workday assignable role | ISC / HR Administrator |
| 4. Create Role-Based Security Group | To Do: create the security group, named with the full role name | ISC / HR Administrator |
| 5. Link Workday Role | Link the new Workday role to the request | ISC / HR Administrator |

Outcomes:

- **Approved**: after step 5 the request shows **✓ Approved** and you get a Workday notification, "ECO-COMS role request completed".
- **Denied**: ISC denied the request, or the review was **cancelled**. Either way ECO-COMS marks it **✗ Denied** and inactive, usually within a few minutes (Workday allows up to about 15). In Workday the event itself shows "Process Terminated". You get no completion notification. Submit a new request if you still need the role.

### Audit Log Viewer

**Open Audit Log** on the RBAC Hub opens **ECO-COMS: Audit Log Viewer**: one row per change made through ECO-COMS, newest first. A row is written only when Workday accepts the change.

- **Time Period** pills: **All time**, **Last 24 hours**, **Last 7 days**, **Last 30 days**.
- **Change Type** pills: **All types**, **Shell Org**, **Pattern**, **Org Status**, **Role Assignment**, **Assignable Role**. The two filters combine: picking a type keeps the period, and the other way round.
- **Showing** says how many records match, out of the total, and which filters are on.
- **Changes by Action**: a donut of the matching records by action, next to the filters.
- The page loads the newest 500 records. If there are more, **Showing** says so; use the **All Audit Logs** report for older history.

- Columns: **Timestamp**, **Change Type**, **Action**, **Organization**, **Role**, **Position**, **Effective Date**, **Changed By**, **Details**.
- **Change Type**: Shell Org, Shell Org Pattern, Org Status, Role Assignment, Assignable Role.
- **Timestamp**: Pacific time, to the minute.
- **Action**: Add, Inactivate, Reactivate, Assign position, Remove position, Request, Approve, Deny, Delete (the same names as the donut's legend).
- Organizations, roles and positions that exist in Workday are links: hover for related actions. A role that doesn't exist in Workday yet is plain text.
- Use the grid's export icon to download the rows currently shown (after filtering) to Excel.

You need the **View: COMS Audit Log** domain to open this page.

### Finding your way around

- **Home** shows your own work (**Needs My Attention**), the ISC queue, Shell Org Manager, the Audit Log and the active/inactive split of shell organizations, then one action card per area: Shell Organizations, Bulk Role Changes and Role Requests.
- **Filters** are pill buttons; the current choice has a ✓. On the Audit Log choose a time period and change type; on ISC Queue choose the request type and status.
- Every page has one back link at the top. Actions for the page are in an **Actions** card.

### Shell organization details

In Shell Org Manager, **Details** on an organization opens one page with its status in Workday, the roles assigned on it (positions, workers, and **Manage** to change them), and its ECO-COMS change history from the newest 200 Audit Log records. **Change Status** there inactivates or reactivates it. Active organizations are listed before inactive ones.

### Request again

On My Assignable Role Requests, each of your requests has **Retry** (denied requests) or **Reuse** in the New Request column. It opens a new request with the role name filled in and a note showing the earlier request and the reason given. Choose the application, organization, positions and effective date again; the Workday role name is generated when you pick the organization.

### Needs My Attention (Home)

The **Needs My Attention** card on Home sums up your own work: your role requests pending ISC review (split into assignable and AAA when you have AAA requests), approved this month, and denied or withdrawn, plus any bulk upload of yours that is still running or was rejected. **My requests** opens My Assignable Role Requests (your requests, with Withdraw); **AAA requests** and **My bulk uploads** are under the card's ⋯ menu.

### Bulk Role Changes (many positions at once)

Use this to add or remove many positions on shell organization roles at once. It's on Home under **Bulk Role Changes** and needs the same access as Manage Role Assignments. There are two ways in; both run through the same checks and show their results on the same page.

**In the app (Edit in the App)**, like a Get/Put EIB without leaving Workday. Up to 50 changes per submit.

1. Click **Edit in the App** and then **Edit** on an application. **Current Assignments** lists every position that holds a role on that application's shell organizations.
2. Tick **Remove** on the rows to take off.
3. To add, click **+** under **Positions to Add**, pick the **Role and Organization**, then type part of a position's name in **Position** and pick it. A position that already holds that role there is flagged straight away.
4. Pick an **Effective Date** and click OK. Leave **Real run** unticked to validate first. Results opens; when the run shows **Validated** with no INVALID rows, click **Apply**.

**From a file (Excel template)**. Up to 1,000 ADD or REMOVE rows per file; unchanged rows don't count.

1. **Download Template** and click the Excel file under **Excel Template**. It already lists every current role assignment (the "as of" time is on the page and on the sheet) and checks each row as you type: a drop-down for Action, format checks, duplicates, and a **Summary** box that says **Ready** when the file is clean. Its **How to use** sheet has the steps. (You can still export the grid on that page instead; then follow steps 2–3 of the template's How to use sheet by hand.)
2. **Edit the file.** Type **REMOVE** in Action on rows to take off. To add, copy a row of the same role and organization to an empty row, type **ADD**, put the new **Position ID** (for example P-00123) and clear Assignee WID. Leave Action empty on everything else. With the **Role Changes** sheet selected, save as **CSV**.
3. **Upload File** and pick an effective date. Leave **Real run** unticked to **validate only**: every row is checked (including that each ADD Position ID exists in Workday) and nothing changes.
4. On the results page, click **Refresh** until the status is **Validated**. Each row is **VALID** or **INVALID** with a reason. Fix INVALID rows and upload again.
5. When there are no INVALID rows, click **Apply**, tick the confirmation and click OK. Each row is applied in Workday's Assign Roles. Rows show **DONE** or **FAILED** with Workday's message; a failed row doesn't stop the others, and changes that succeed aren't undone. Each DONE row writes an ASSIGN POSITION or REMOVE POSITION record to the Audit Log.

You can also tick **Real run** to validate and apply in one go, but validating first is safer. Runs work in the background, so the results page fills in over a minute or two. **My Uploads** on the results page lists both your file uploads and your grid edits.

**Keeping the template current (administrators).** The Excel template is rebuilt from Workday after every deploy. To publish one by hand (for example in a tenant without the deploy pipeline), use **Upload New Template Version** on the Download Template page; the newest version is the one people get.

---

## Part 2: ISC reviewers and approvers

### Where review work appears

- **Your Workday inbox.** Each step arrives as an inbox item named "Review COMS Assignable Role Request: <role name>". The step help text explains what to check.
- **ECO-COMS → ISC Queue** card → **Open ISC Queue** (needs **Maintain: COMS Assignable Roles**). The page, **ECO-COMS: ISC Queue – Pending Role Requests**, opens on pending requests; use the **Request Type** (All requests, AAA roles, Assignable roles) and **Status** pills to change the view, and the title follows your choice.
  - Three cards at the top: **Pending**, **Overdue** (pending for more than 3 business days) and **Approved this month**.
  - **Status** pills: **Pending** (the default), **Approved**, **Denied**, **All**. **Showing** says how many requests match.
  - Overdue rows show "· overdue" next to their status.
  - Each row has a **Review Process: <role>** link; hover it for the event's related actions. Every request is approved or denied through its review process; the old **Maintain** page has been retired.

### The five steps, in order

Each ECO-COMS step page shows a "Step N of 5" banner.

1. **Role Details** (Step 1 of 5). Read-only summary: Role Name, Application / Organization, Enabled For, Positions, Requested By, Requested Date, Effective Date, Status, Security Group, Notes.
2. **Approve / Deny** (Step 2 of 5). The approval group reviews the details, then clicks **Approve** or **Deny** in the inbox item.
   - Approve sends the request on to the two To Dos and then Link Workday Role.
   - Deny ends the process and marks the request Denied.
3. **To Do: Add Assignable Role.** Create the Workday assignable role for the request (exact Workday task to confirm), then mark the To Do done.
4. **To Do: Create Role Based Security Group.** Run **Create Security Group**:
   - **Type of Tenanted Security Group**: **Role-Based Security Group**
   - **Name**: the **full role name exactly as requested**, for example `X:ADM:ROLE:EXAMPLE`. Don't shorten or reformat it.

   Then mark the To Do done.
5. **Link Workday Role** (Step 5 of 5, action step, ECO-COMS page **Add Workday Assignable Role**):
   1. **Workday Assignable Role**: select the role created in step 3.
   2. **Role-Based Security Group**: check the prefilled name matches the group from step 4.
   3. Click **OK**. The request becomes **Approved**, an APPROVE audit record is written, it leaves the ISC Queue's pending list, and the requester is notified.

### Denying or cancelling

- **Deny** is on the approval step (step 2) while it is awaiting action. It needs the Deny permission on the business process policy; if you don't see it, ask the app admin.
- **Cancel** is on the event (find it with Find Events, or through the **Review Process** link → related actions). Use it when the approval has already completed or the request should be withdrawn at a later step.
- Both have the same result in ECO-COMS: the request is marked **Denied** and inactive and a DENY audit record is written, usually within 2–3 minutes. The comment you type when you deny or cancel is copied into the request's **Denial Reason** and the audit record, and the audit record names you as Changed By. Type a short reason so the requester knows why.

### Self-approval is blocked

The approval step has the routing restriction **Exclude Initiator**. The requester is the initiator, so you never get the approval for a request you submitted yourself. If excluding the requester leaves nobody eligible, Workday marks the step **Not Required** and skips it. The app admin can prevent this with an alternate approval group (not yet tested live).

---

## Troubleshooting

| You see | What it means | What to do |
|---|---|---|
| "Workday rejected this request, so nothing was created. Check the values and try again." | ECO-COMS asked Workday to create the org or pattern, then checked, and it isn't there. | Check the values (code, dates). Try again. If it keeps failing, raise a helpdesk ticket with the name you entered and the time. |
| "Workday rejected this status change, so nothing was changed..." | Workday refused the inactivate or reactivate. The usual cause is a future-dated change already scheduled on the org. | Pick an effective date after the scheduled change, or wait for it to take effect. |
| "Workday rejected N of M changes. Check the role assignment in Workday and try again." | Some position changes failed. The rest went through. | Check the role's current positions, then redo only the missing changes. |
| Bulk row INVALID: "Position ID … was not found in Workday." | The Position ID in the ADD row doesn't match a position. | Check the ID (format P-00123) and upload the file again. |
| Bulk row FAILED: "Workday rejected the change: …" | Workday refused that one row (for example, the position can't hold the role). The other rows still ran. | Fix or remove that row and run a new file with only the rows that are left. |
| "An organization with this code already exists" / "A Shell Org Pattern with this name already exists" | Duplicate name. | Use a different code, or use the existing org. |
| "This AAA role already exists in Workday" | Duplicate AAA request. | Review the existing role instead. |
| "Cannot select both Functional Unit Hierarchy and Academic Unit." | Enabled For takes one or the other. | Clear one of them. |
| A page opens and immediately sends you back to the hub or home page | You don't have the security domain for that page. This is not an error in the page. | Ask for the right domain: **Manage: COMS Shell Organizations** (shell orgs, patterns, status, role assignments), **Manage: COMS Assignable Roles** (role requests), **Manage: COMS Admin Provisioning** (AAA requests), **Maintain: COMS Assignable Roles** (ISC pages and review steps), **View: COMS Audit Log** (audit log). |
| "Access Restricted: ISC Access Required" | The page is for ISC Security Administrators. | Raise an Incident Ticket with ISC Service Delivery if you need access. |
| An org still shows **Active** after you inactivated it | The effective date is in the future. | Nothing to do. It turns inactive on that date. |
| Your request stays **Pending ISC Review** for a long time | It is waiting in an approver's inbox. | Contact ISC. |
