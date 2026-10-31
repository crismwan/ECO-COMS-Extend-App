# ECO-COMS user guide

ECO-COMS (Custom Organization Management System) is a Workday Extend app for role-based access control (RBAC). Use it to:

- create **shell organizations** (Custom Organizations such as `X:CLW:ORG:ANY`) and **shell org patterns** (such as `X:CLW:PATTERN:MATH:MATH_V:303:951:2026W1`) in Workday
- inactivate or reactivate those organizations
- add or remove the positions assigned to a role on a shell organization
- request new **assignable roles** and **AAA (Admin Provisioning)** roles, which ISC reviews in a Workday business process
- see every change in the **Audit Log Viewer**

Part 1 is for requesters. Part 2 is for ISC reviewers and approvers.

---

## Part 1: Requesters

### Getting around

Open the app from Workday. The **ECO-COMS** hub opens on the **RBAC Hub** page. The left pane has:

- **RBAC Hub**: the main page, with three sections:
  - **Shell Organizations**: **Add Shell Org**, **Add Pattern**, **Open Manager** (Shell Org Manager)
  - **Assignable Roles**: **Submit New Request**, **View Requests**
  - **Administration**: **Submit AAA Role**, **View Pending ISC Requests**, **View Audit Log**
- **FUH Administration**: information about Functional Unit Hierarchy organizations (no actions yet).
- **Resources**: **Submit a Helpdesk Ticket** and **RBAC Rolename by Application** (external links).

Most pages have a **← Home** link at the top. What you see depends on your security domains (see [Troubleshooting](#troubleshooting)).

### Shell Org Manager

**Open Manager** opens **ECO-COMS: Shell Org Manager**. Its sections:

- **Summary**: counts of **Active Orgs**, **Inactive Orgs** and **Total Patterns**, plus **Quick Actions** to add an org or a pattern.
- **Application Patterns**: the **Applications** grid. Click **Manage** on an application to see only its patterns and orgs; **← Back to Applications** returns to the full view. The **Shell Org Patterns** grid shows each pattern's name, code and status, with an **Inactivate** / **Activate** button.
- **Application Shell Organizations**: every shell org with its status and a **Manage** button.
- **Manage Role Assignments**: one row per role on one shell org, with its positions and workers, and a **Manage** button.

Only pattern codes that start with `X:` and contain `:PATTERN:` are listed.

### Create a shell organization

1. On the RBAC Hub, click **Add Shell Org**. The **Create New Shell Organization** wizard opens.
2. On **Organization Details**:
   1. **Application**: pick the application the org belongs to.
   2. **Organization Code**: enter the suffix only, without spaces or special characters. **Generated Organization Name** shows the full name, `ApplicationCode:OrganizationCode` (for example `X:CLW:ORG:ANY`).
   3. **Effective Date**: the date the org becomes available. The year must be 2026 or 2027. The field tooltip also asks for a weekday (Monday to Friday). The page itself checks only the year (to confirm whether Workday rejects weekend dates).
3. Click **Next**, check the **Review & Submit** summary, then click **OK**.
4. ECO-COMS creates the org in Workday and checks that it now exists. If it does, **Shell Organization Created** opens with **Add Another Organization** and **View in Shell Org Manager**.

The page stops you if the code already exists ("An organization with this code already exists: ...") or if Workday refused the request (see [Troubleshooting](#troubleshooting)).

### Create a shell org pattern

1. On the RBAC Hub, click **Add Pattern**. The **Add New Shell Org Pattern** wizard opens.
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
3. The **Change Status: <code>** page shows **Current Status** and **New Status**.
4. Read the warning. **Inactivating does not remove role assignments that use this org.** Check in Workday that no active role assignment depends on it before you continue.
5. Enter the **Effective Date**.
6. Tick the confirmation box, then click **OK**.
7. **Status Updated** opens if Workday accepted the change.

**Effective dates in the future.** A change dated in the future is scheduled in Workday. Until that date the org is still active, so Shell Org Manager keeps showing **✓ Active**.

**Why a second change can be rejected.** Workday allows only one pending status change per org. If the org already has a future-dated change, another one fails with "conflicting events (in progress or future events)", and ECO-COMS shows "Workday rejected this status change...". Choose an effective date after the scheduled change, or wait until it has taken effect.

### Add or remove positions on a role

1. In **Shell Org Manager**, open **Manage Role Assignments** and click **Manage** on the role and org row.
2. **Manage Role Assignment: <role>** shows the **Current Assignment** (role, org, current positions).
3. Under **Change Positions**:
   - **Positions to Add**: search by position name or ID (for example `P-00010`). You can pick more than one.
   - **Positions to Remove**: pick from the positions currently assigned.
   - **Effective Date**: required.
4. Click **OK**. Each add and each remove runs through the Workday Assign Roles business process. **These changes can't be rescinded.** To undo one, make the opposite change.
5. After OK you return to the app home page, not to Shell Org Manager.

If any change fails, the page shows "Workday rejected N of M changes...". The changes that succeeded stay in place, so check the role in Workday before you try again.

### Request an assignable role

1. On the RBAC Hub, click **Submit New Request**. The **ECO-COMS: Assignable Role Manager** page opens. Section **1. Pending ISC Review** lists requests still waiting.
2. In **2. Submit New Assignable Role Request**:
   1. **Custom Organization**: the shell org the role applies to.
   2. The role: either pick an existing role in **Delegated Roles**, or type a new one in **New Delegated Role** in ALL CAPS (for example `COORDINATOR`, 100 characters at most). If the new name already exists, pick it from Delegated Roles instead.
   3. **Generated Workday Role Name** is filled in for you as `<Custom Organization>:ROLE:<role>`, for example `X:ADM:ROLE:COORDINATOR`.
   4. **Effective Date**.
   5. **Positions**: at least one.
   6. **Enabled For**: pick a **Functional Unit Hierarchy** *or* an **Academic Unit**, not both. If you pick neither, Enabled For is "Academic Unit - University of British Columbia".
3. Click **OK**. The request is saved with status **⏳ Pending ISC Review** and the ISC review starts in Workday (see [After you submit](#after-you-submit-the-isc-review)).

To see your requests, use **View Requests** on the RBAC Hub (**My Assignable Role Requests**).

### Request an AAA role (Admin Provisioning)

An AAA role (Organizations and Roles Assignment Administrator) decides who can manage shell orgs and submit role requests in ECO-COMS for an application.

1. On the RBAC Hub, click **Submit AAA Role**. **ECO-COMS: Admin Provisioning (AAA)** opens.
2. In **2. Submit New Assignable Role Request**:
   1. **Application**: required.
   2. **Enabled For**: pick a **Functional Unit Hierarchy** *or* an **Academic Unit**, not both, or leave both empty (Enabled For is then "Academic Unit - University of British Columbia").
   3. **Requested AAA Role** is generated for you: `Organizations and Roles Assignment Administrator (<Application>)`, with `, Functional Org` or `, Academic Unit` added when you pick one.
   4. **Effective Date**: required.
   5. **Positions**.
3. Click **OK**. If that AAA role already exists in Workday, the page says so and stops you from submitting a duplicate.

The form has no Delegated Roles field. Delegated Roles appears only as a column in the requests grid (to confirm whether AAA requests should capture it).

### Withdraw a pending request

**Withdraw Request** (on the request list pages) opens **ECO-COMS: Withdraw Assignable Role Request**. It lists only **your own** requests that are still **Pending ISC Review**.

1. Click **Select** on the request.
2. Tick **I confirm I want to withdraw this request.**
3. Click **OK**.

ECO-COMS cancels the request's ISC review in Workday. Within a few minutes the request shows **✗ Denied** and a DENY record appears in the audit log. A withdrawn review can't be restarted; submit a new request if you still need the role. An older request that never started a review is deleted instead, with a DELETE audit record.

Cancelling a review needs the **Cancel** permission on the business process. If OK fails with a permission error, ask the app admin to add requesters (or the Initiator) to Cancel on the business process policy (to confirm before go-live).

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

**View Audit Log** on the RBAC Hub opens **ECO-COMS: Audit Log Viewer**: one row per change made through ECO-COMS, newest first. A row is written only when Workday accepts the change.

- Columns: **Timestamp**, **Change Type**, **Action**, **Organization**, **Role**, **Position**, **Effective Date**, **Changed By**, **Details**.
- **Change Type**: Shell Org, Shell Org Pattern, Org Status, Role Assignment, Assignable Role.
- **Action**: ADD, INACTIVATE, REACTIVATE, ASSIGN POSITION, REMOVE POSITION, REQUEST, APPROVE, DENY, DELETE.
- Organizations, roles and positions that exist in Workday are links: hover for related actions. A role that doesn't exist in Workday yet is plain text.
- Use the grid's export action to download a CSV for compliance reporting.

You need the **View: COMS Audit Log** domain to open this page.

---

## Part 2: ISC reviewers and approvers

### Where review work appears

- **Your Workday inbox.** Each step arrives as an inbox item named "Review COMS Assignable Role Request: <role name>". The step help text explains what to check.
- **ECO-COMS → View Pending ISC Requests** (needs **Maintain: COMS Assignable Roles**). Choose **View All Pending Requests**, **Pending AAA Provisioning** or **Pending Assignable Roles**. Each row with a review shows a **Review Process: <role>** link; hover it for the event's related actions. Rows without a review event show **Maintain** (the older approve/deny page; to confirm whether it is still in use).

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
   3. Click **OK**. The request becomes **Approved**, an APPROVE audit record is written, it leaves Pending ISC Requests, and the requester is notified.

### Denying or cancelling

- **Deny** is on the approval step (step 2) while it is awaiting action. It needs the Deny permission on the business process policy; if you don't see it, ask the app admin.
- **Cancel** is on the event (find it with Find Events, or through the **Review Process** link → related actions). Use it when the approval has already completed or the request should be withdrawn at a later step.
- Both have the same result in ECO-COMS: the request is marked **Denied** and inactive and a DENY audit record is written, usually within 2–3 minutes.

### Self-approval is blocked

The approval step has the routing restriction **Exclude Initiator**. The requester is the initiator, so you never get the approval for a request you submitted yourself. If excluding the requester leaves nobody eligible, Workday marks the step **Not Required** and skips it. The app admin can prevent this with an alternate approval group (not yet tested live).

---

## Troubleshooting

| You see | What it means | What to do |
|---|---|---|
| "Workday rejected this request, so nothing was created. Check the values and try again." | ECO-COMS asked Workday to create the org or pattern, then checked, and it isn't there. | Check the values (code, dates). Try again. If it keeps failing, raise a helpdesk ticket with the name you entered and the time. |
| "Workday rejected this status change, so nothing was changed..." | Workday refused the inactivate or reactivate. The usual cause is a future-dated change already scheduled on the org. | Pick an effective date after the scheduled change, or wait for it to take effect. |
| "Workday rejected N of M changes. Check the role assignment in Workday and try again." | Some position changes failed. The rest went through. | Check the role's current positions, then redo only the missing changes. |
| "An organization with this code already exists" / "A Shell Org Pattern with this name already exists" | Duplicate name. | Use a different code, or use the existing org. |
| "This AAA role already exists in Workday" | Duplicate AAA request. | Review the existing role instead. |
| "Cannot select both Functional Unit Hierarchy and Academic Unit." | Enabled For takes one or the other. | Clear one of them. |
| A page opens and immediately sends you back to the hub or home page | You don't have the security domain for that page. This is not an error in the page. | Ask for the right domain: **Manage: COMS Shell Organizations** (shell orgs, patterns, status, role assignments), **Manage: COMS Assignable Roles** (role requests), **Manage: COMS Admin Provisioning** (AAA requests), **Maintain: COMS Assignable Roles** (ISC pages and review steps), **View: COMS Audit Log** (audit log). |
| "Access Restricted: ISC Access Required" | The page is for ISC Security Administrators. | Raise an Incident Ticket with ISC Service Delivery if you need access. |
| An org still shows **Active** after you inactivated it | The effective date is in the future. | Nothing to do. It turns inactive on that date. |
| Your request stays **Pending ISC Review** for a long time | It is waiting in an approver's inbox. | Contact ISC. |
