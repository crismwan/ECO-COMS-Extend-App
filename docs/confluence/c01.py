"""Fill 01: Business Requirements for ECO-COMS."""
import sys
from bs4 import BeautifulSoup
from fill import *

SRC = '01_part1.html'
OUT = sys.argv[1] if len(sys.argv) > 1 else 'out01.html'
s = BeautifulSoup(open(SRC, encoding='utf-8').read(), 'html.parser')
TBC = '[TBC]'
ARCH = 'To be confirmed'
PO = 'Product owner decision'

# ---------------------------------------------------------------- page properties
pp = T(s, 'Solution name')
kv(s, pp, 'Solution name', 'XTND-0037-XFD_SEC-Custom_Organization_Management\nECO-COMS: Custom Organization Management System (shell organizations and shell roles in Workday)')
kv(s, pp, 'Solution ID', 'XTND-0037-XFD_SEC-Custom_Organization_Management (EDG Naming Standard; its orchestrations are IORC_0037_XFD_SEC_<description>)\n'
   'Extend app reference ID: the ID App Hub assigned when the app was created (development tenant); production ID [TBC]')
kv(s, pp, 'Linked Tickets', f'{TBC} (no ServiceNow or Jira item recorded yet)')
kv(s, pp, 'Solution type', 'Extend App')
kv(s, pp, 'Solution pattern', 'In-tenant UI (with one event-driven step: an orchestration triggered by the review business process on Deny or Cancel)')
kv(s, pp, 'Domain', 'HCM (security: custom organizations, assignable roles and role assignments)')
kv(s, pp, 'Document status', 'Draft (ready for review)')
kv(s, pp, 'Business owner(s)', f'{TBC}: Integrated Service Centre (ISC), Security / Access Management')
kv(s, pp, 'Product owner(s)', 'Crispin Mwanyumba, Integrated Service Centre')
kv(s, pp, 'Solutions Developer(s)', 'Crispin Mwanyumba')
kv(s, pp, 'Security Lead', f'{TBC} (ISC Security)')
kv(s, pp, 'QA Lead', TBC)
kv(s, pp, 'Project Manager', TBC)
kv(s, pp, 'Ticket Number', TBC)
kv(s, pp, 'Data classification', 'Medium risk (proposed; to be confirmed with UBC Privacy / Information Security)')
kv(s, pp, 'Personal information involved', 'Yes: worker names and position titles shown next to role assignments; requester, approver and "changed by" names on requests and audit records. Read from Workday, not collected from the public. No sensitive categories.')
kv(s, pp, 'PIA required', f'{TBC}: to be confirmed with UBC Privacy (the app adds no new personal data to Workday; it shows existing data and records who made each change)')
kv(s, pp, 'Related solutions', 'Upstream: Workday positions and the custom organization hierarchy (X: shell organizations). Downstream (unchanged): AccessUBC shell-role extract, then the target applications (Clockwork, OAMS, Admissions and others delivered under IRPS). Replaces: Appian COMS.')
kv(s, pp, 'Version', 'v1.0 draft · last reviewed 2026-11-05 · next review due at sign-off [TBC]')

# ---------------------------------------------------------------- 1. delivery pattern
cards = T(s, 'Workday Studio Integration')
for tr in cards.find_all('tr'):
    tds = tr.find_all('td')
    if len(tds) == 3:
        tds[0].decompose(); tds[1].decompose()
for col in cards.find_all('col')[:2]:
    col.decompose()
first = cards.find('tr').find('td')
insert_before(s, first.find('p'), '<p>✓ <strong>Selected</strong></p>')
attr = T(s, 'Do not delete or rename the fields in this box', nth=1)
kv(s, attr, 'Solution type', 'Extend')
kv(s, attr, 'Delivery pattern', 'In-tenant UI (plus one event-driven step when the review business process is denied or cancelled)')
kv(s, attr, 'Trigger', 'User task (pages in the app); business process event (Deny / Cancel on the review process); Home card refresh when Workday Home is opened')
kv(s, attr, 'Runs as', 'Initiating user for every page and orchestration. Planned exception: an integration system user (ISU) writes audit and request records so users can only read them (justification in 02 §6.9).')
kv(s, attr, 'Interacts with external systems?', 'No. Everything stays in the Workday tenant. AccessUBC and the target applications read the result through the existing shell-role extract, which this solution does not change.')
kv(s, attr, 'Mobile required?', 'No (desktop; the app is used at a desk by administrators). Nice to have later for reviewers.')

# ---------------------------------------------------------------- 2. overview
ov = T(s, 'Question')
set_rows(s, ov, [
    ['What is this solution?', 'ECO-COMS is a Workday Extend app that lets application administrators create and maintain the "shell" organizations and shell role assignments their downstream systems use, inside Workday and within limits ISC sets, instead of raising ISC tickets or using the old Appian COMS. It also routes requests for new shell roles to ISC through a Workday business process and records every change in an audit log.'],
    ['Who uses it or benefits from it?', 'Application access administrators (AAAs) of applications that use shell roles (Clockwork, OAMS, Admissions, BPMS applications and others, 33 today); ISC security administrators, who review role requests and no longer process routine tickets; auditors, who get one log of every change.'],
    ['What happens today without it?', 'Only ISC can create shell organizations and assignable roles, so every new organization is a ticket. Clockwork needs new ones every term. The Appian COMS handles one pattern shape (Clockwork) and runs on a platform UBC wants to exit. In the standard Workday task an AAA can see every role on a position, including real Workday roles, and can request their deletion.'],
    ['What is the single measurable outcome?', 'Application administrators create the shell organizations and patterns they need in Workday themselves, within their own boundary, with no ISC ticket, and the Appian COMS licence can be retired.'],
    ['When is it needed and why that date?', f'{TBC}: driven by the Appian licence renewal date and the start of the next term (Clockwork creates new patterns each term).'],
], keep=1, bold_first=True)

# ---------------------------------------------------------------- 3. current state
cs = T(s, 'Aspect')
set_rows(s, cs, [
    ['How the work gets done now', 'Application administrators raise a ticket to ISC for each new shell organization or assignable role. Clockwork uses the Appian COMS form, which builds one pattern shape. ISC staff create the custom organization (org type X:«code», subtype X:SHELL) and roles in Workday by hand. Role assignments are made with the standard Workday Assign Roles task.'],
    ['Systems and objects involved', 'Workday: custom organizations (X:«code» hierarchy), assignable roles, role assignments on positions, security groups (none for shell roles). Appian COMS. AccessUBC (extract and ad hoc assignments). Target applications.'],
    ['Volume and frequency', 'In the development tenant today: 33 applications, 216 shell organizations and 397 Clockwork-style patterns; Clockwork adds patterns every term. Assignable roles change rarely. Production volumes: [TBC].'],
    ['Effort / cost today', f'{TBC}: one ISC ticket per organization or role, plus the Appian licence.'],
    ['Known failure modes', '• ISC is the bottleneck: changes wait in a queue.\n• The Appian form only knows one pattern shape, so each new application would need a rebuild.\n• A AAA using the standard task sees other roles on a position and can request their deletion; if the owner approves by mistake, access is lost ("two errors").\n• No single audit trail of who changed what.'],
    ['Related tickets in the last 12 months if any', TBC],
], keep=1, bold_first=True)
insert_after(s, wrap_of(cs), img('img/current-architecture.png', 'Current shell-role architecture: Workday holds the truth, AccessUBC adds ad hoc assignments, the application turns roles into grants', 800))

# ---------------------------------------------------------------- 4. future state
ul = heading(s, '4. Future / Desired State').find_next_sibling('ul')
insert_after(s, ul, para(
    'Who: application access administrators (AAAs) for applications that use shell roles initiate changes; ISC security administrators review new role requests; auditors read the log.\n'
    'What: ECO-COMS creates shell organizations and shell organization patterns (custom organizations under the application\'s own org type), inactivates and reactivates them, adds and removes positions on shell roles (one at a time, in a grid or from a file), raises requests for new shell assignable roles and AAA roles, and records every accepted change.\n'
    'For which population: the custom organizations with subtype X:META or X:SHELL (named anything; since 2026-11-06 the X: prefix is a convention, not a rule), each belonging to the application its organization type names (for example X:CLW, X:BPMS(AOC)); shell roles (X:«code»:ROLE:…) on those organizations; positions in the tenant. Real Workday roles, supervisory organizations and academic units are out of reach.\n'
    'When: on demand, whenever an administrator needs a change (Clockwork: at least each term). Role requests start a Workday review immediately; a review waiting 2 days sends a reminder.\n'
    'How it behaves: each application has its own pattern format (prefix, fields, rules), kept as data in the app, so a new application is set up by filling in a record, not by a development release. Every change is checked on the page and again on the server before Workday is called, and is recorded only after Workday accepts it. AccessUBC picks up the result through its existing extract; nothing changes downstream.'))
insert_after(s, wrap_of(T(s, 'Diagram — Future-state process flow')), img('img/future-state.png', 'Future-state process: the administrator works in ECO-COMS, which checks, calls Workday, records the change; AccessUBC and the target application are unchanged', 900))

# ---------------------------------------------------------------- 5. users
act = T(s, 'Actor')
set_rows(s, act, [
    ['Application access administrator (AAA), e.g. Clockwork exam coordinator', 'Manage: COMS Shell Organizations; Manage: COMS Assignable Roles; Manage: COMS Admin Provisioning (AAA requests); View: COMS Audit Log', 'Uses the app as needed (weekly to termly)', f'{TBC} (about 1–3 per application)'],
    ['ISC security administrator / reviewer', 'Maintain: COMS Assignable Roles; review business process approval group; View: COMS Audit Log', 'Reviews requests in the Workday inbox and the ISC Queue', TBC],
    ['Application pattern maintainer (ISC or app owner)', 'Manage: COMS Application Setup', 'Sets up a new application\'s pattern format', '1–3'],
    ['Auditor / compliance', 'View: COMS Audit Log (and the ECO-COMS reports)', 'Reads the audit log and reports', TBC],
    ['System / scheduled process', 'Integration system user (planned, to write audit and request records); the tenant\'s orchestration launch user (business-process-triggered step)', 'Runs unattended', 'n/a'],
], keep=1)
per = T(s, 'Persona')
set_rows(s, per, [
    ['Application administrator (e.g. Clockwork)', 'Create the shell organizations / patterns and role holders the application needs this term, without a ticket', 'Termly peaks, weekly otherwise', 'Desktop, at a desk', 'Occasional', 'Not knowing the naming format; cryptic Workday errors; having to know a position ID; waiting for ISC'],
    ['ISC security reviewer', 'Approve or deny new shell role requests and see what is waiting', 'Weekly', 'Desktop; Workday inbox', 'Expert', 'Requests without enough detail; duplicate requests; being asked to approve their own request'],
    ['Application pattern maintainer', 'Describe a new application\'s pattern format once, so its administrators can self-serve', 'Once per application, rarely after', 'Desktop', 'Expert', 'Needing a developer or a release to add an application'],
], keep=1)
jt = T(s, 'Step')
set_rows(s, jt, [
    ['1', 'Find where to make the change', 'Email or ticket to ISC; Appian for Clockwork only', 'Workday search "Shell Org Manager" or the RBAC Hub; the Application bar narrows to one application in two clicks', 'Not knowing where to go'],
    ['2', 'Get the name right', 'Remember the format; mistakes found later by ISC', 'The form shows this application\'s fields, examples and a live name preview; each field is checked as you type', 'Rework and back-and-forth'],
    ['3', 'Make the change', 'Wait for ISC', 'OK creates it in Workday in seconds; the page re-checks Workday and shows a receipt', 'Waiting days'],
    ['4', 'Put people on the role', 'Standard task: need the position ID; see others\' roles', 'Pick positions by browsing supervisory organizations, or edit many at once in a grid or Excel', 'Searching for IDs; seeing other people\'s roles'],
    ['5', 'Prove what happened', 'No single record', 'Every change is in the Audit Log, linked to the Workday event', 'Investigations without evidence'],
], keep=1)
insert_after(s, wrap_of(T(s, 'Diagram — User journey map')), img('img/user-journey.png', 'User journey for the primary persona: today versus with ECO-COMS', 900))

# ---------------------------------------------------------------- 6. impact
imp = T(s, 'Group, record or cohort impacted')
set_rows(s, imp, [
    ['Application administrators (AAAs)', 'People holding an AAA role for an application that uses shell roles (X:«code»)', 'They create and maintain their own shell organizations, patterns and role holders the same day, inside their own boundary', 'Every change remains an ISC ticket; Clockwork waits each term'],
    ['ISC security team', 'ISC staff who create custom organizations and roles today', 'Routine organization tickets disappear; they review only new roles, in a Workday inbox with a queue and reminders', 'ISC remains the bottleneck for routine, low-risk changes'],
    ['Downstream applications', 'Clockwork, OAMS, Admissions, BPMS applications and others fed by AccessUBC', 'Access is ready sooner; data reaches them unchanged through the existing extract', 'Delays in granting access at term start'],
    ['UBC IT / Appian platform', 'Owners of the Appian COMS and its licence', 'Appian COMS can be retired', 'The Appian licence and a second platform remain'],
    ['Auditors', 'Anyone who must reconstruct who granted access and when', 'One audit log of every change, linked to Workday events', 'Evidence spread across tickets and Workday history'],
], keep=1)

# ---------------------------------------------------------------- 7. functional requirements
fr_intro = T(s, 'One row per testable statement')
insert_after(s, wrap_of(fr_intro), para(
    'Use cases:\n'
    '• UC-01 Create a shell organization (X:META or X:SHELL) for an application\n'
    '• UC-02 Create a shell organization pattern from the application\'s format\n'
    '• UC-03 Inactivate or reactivate a shell organization or pattern\n'
    '• UC-04 Add or remove positions on a shell role\n'
    '• UC-05 Change many role assignments at once (grid or Excel/CSV)\n'
    '• UC-06 Request a new shell assignable role or AAA role\n'
    '• UC-07 Review a role request (ISC)\n'
    '• UC-08 Maintain an application\'s pattern format\n'
    '• UC-09 Find and narrow to an application; see its organizations, patterns and roles\n'
    '• UC-10 Audit and report on changes\n'
    '• UC-11 Review shell roles held by vacant positions'))
FR = [
    ['FR-001', 'The system shall list every application that has a shell organization (subtype X:META or X:SHELL) or a pattern record, derived from Workday data (an organization\'s application is its organization type), so a new application appears without any change to the app, whatever it is named.', 'UC-09', 'Must', 'Given a new organization X:NEWAPP exists in Workday, when Shell Org Manager loads, then X:NEWAPP is listed under its family or Standalone.', ARCH],
    ['FR-002', 'The system shall let a user narrow Shell Org Manager to one application (family, then application) and back to all applications; every tab shall show only that application\'s organizations, patterns and roles.', 'UC-09', 'Must', 'Given BPMS is picked and then ODMT, then all tabs show only X:BPMS(ODMT) data; X:LLIS shows no X:LLIS(CPE) roles.', f'{PO}, 2026-11-05'],
    ['FR-003', 'The system shall create a shell organization named «application code»:«code» with subtype X:META or X:SHELL, effective on a chosen weekday this year or next.', 'UC-01', 'Must', 'Given application X:BPMS(AOC), subtype X:SHELL and code TST, when OK, then X:BPMS(AOC):TST exists in Workday and a receipt is shown.', ARCH],
    ['FR-004', 'The system shall enforce naming rules for new shell organizations on the page and again on the server: upper case, no spaces, unique code.', 'UC-01', 'Must', 'Given code "tst", when OK, then the page refuses with "Use upper case"; a direct launch with a lower-case code is rejected by the orchestration.', f'{PO}, 2026-11-05'],
    ['FR-005', 'The system shall build a pattern form from the application\'s format (prefixes, up to 7 fields, rules and examples), preview the name as the user types, and treat a blank field as "*" (any) unless the field is required; trailing fields may be optional and are then left off the name when blank (e.g. X:BPMS(ASMT):ORG:ELI and X:BPMS(ASMT):ORG:ARTS:HUMANITIES101).', 'UC-02', 'Must', 'Given X:CLW, when Subject is typed as "cpsc_v", then an error explains the expected format; the preview reads X:CLW:PATTERN:CPSC:CPSC_V:110:101:2026W2 for valid values.', 'Application Patterns.xlsx; ' + ARCH],
    ['FR-006', 'The system shall refuse a pattern whose name already exists or whose prefix is not one of the application\'s prefixes, on the page and on the server.', 'UC-02', 'Must', 'Given an existing pattern name, when OK, then the page shows "A Shell Org Pattern with this name already exists" and nothing is created.', ARCH],
    ['FR-007', 'The system shall only create organizations under the chosen application\'s own organization type; it shall not create or change academic units, supervisory organizations or other Workday organizations.', 'UC-01, UC-02', 'Must', 'Given any input, then the orchestration sends only organization type = application code and subtype X:META/X:SHELL.', ARCH],
    ['FR-008', 'Shell organizations shall be add and inactivate/reactivate only: no rename and no delete, so the meaning of an existing role assignment never changes.', 'UC-03', 'Must', 'Given an existing organization, then no page offers rename or delete.', ARCH],
    ['FR-009', 'The system shall inactivate or reactivate a shell organization or pattern on an effective date, after the user confirms a warning that role assignments are not removed.', 'UC-03', 'Must', 'Given the confirmation is not ticked, then OK is refused; given a future date, then the organization stays Active until that date.', 'ISC'],
    ['FR-010', 'The system shall add and remove positions on a shell role through Workday\'s Assign Roles, and let users find positions by name, ID or by browsing supervisory organizations.', 'UC-04', 'Must', 'Given one position added and one removed, when OK, then both changes are in Workday and in the Audit Log as Assign position / Remove position.', ARCH],
    ['FR-011', 'The system shall show only shell roles (roles enabled for an application\'s organization type) in role pickers and role lists, never real Workday roles.', 'UC-04, UC-05', 'Must', 'Given a position that also holds a Workday security role, then that role does not appear in ECO-COMS.', ARCH],
    ['FR-012', 'The system shall let a user change up to 50 role assignments in an in-app grid and up to 1,000 from an Excel/CSV file, validate every row first without changing anything, and then apply them.', 'UC-05', 'Must', 'Given a file with one invalid Position ID, when validated, then that row is INVALID with a reason and nothing changes; after fixing, Apply marks rows DONE or FAILED with Workday\'s message.', f'{PO}, 2026-10-31'],
    ['FR-013', 'The system shall provide a pre-filled Excel template listing every current shell role assignment, refreshed after each deploy, that checks rows as the user types.', 'UC-05', 'Should', 'Given the template is downloaded, then its "as of" time is shown and the Summary reads Ready when the sheet is clean.', PO],
    ['FR-014', 'The system shall let a user request a new shell assignable role (name «organization»:ROLE:«ROLE»), with positions, effective date and Enabled For (one Functional Unit Hierarchy or one Academic Unit, default Academic Unit - UBC).', 'UC-06', 'Must', 'Given a new role, when OK, then a request is saved as Pending ISC Review and a Workday review starts; picking both Enabled For options is refused.', 'ISC process'],
    ['FR-015', 'The system shall let a user request an AAA role for an application, named "Organizations and Roles Assignment Administrator («application full ID»)", and refuse duplicates of roles that already exist in Workday.', 'UC-06', 'Must', 'Given X:BPMS(COMS), then the role name ends "(X:BPMS(COMS))"; given an existing AAA role, then submit is refused.', f'{PO}, 2026-11-05'],
    ['FR-016', 'Every role request shall go through a Workday business process (Role Details, Approve/Deny, Add Assignable Role, Create Role-Based Security Group, Link Workday Role) in which the requester cannot approve their own request.', 'UC-07', 'Must', 'Given the requester is in the approval group, then they never receive their own approval step (Exclude Initiator).', 'ISC'],
    ['FR-017', 'A denied, cancelled or withdrawn request shall be marked Denied with the reviewer\'s comment as the reason, and the requester notified.', 'UC-07', 'Must', 'Given ISC denies with a comment, then within minutes the request shows ✗ Denied with that reason and a DENY audit record names the reviewer.', 'ISC'],
    ['FR-018', 'The system shall show ISC a queue of requests with waiting time in business days, overdue flags (more than 3 business days) and a reminder to approvers after 2 days.', 'UC-07', 'Should', 'Given a request waiting 4 business days, then it shows "overdue" in the ISC Queue.', 'ISC'],
    ['FR-019', 'A pattern maintainer shall be able to add an application and edit its pattern format (prefixes, field labels, rules, hints, examples, optional trailing fields) in the app, with an example checked against the rules before saving.', 'UC-08', 'Must', 'Given an example that does not match its format, when OK, then the page refuses with the field\'s hint; a valid save is used by the Add Pattern form at once.', ARCH],
    ['FR-020', 'An inactive application format shall take no new patterns.', 'UC-08', 'Should', 'Given an inactive record, then Add Pattern is hidden and the form shows "Application Inactive".', PO],
    ['FR-021', 'The system shall write an audit record for every change Workday accepts (who, when, what, organization, role, position, effective date), linked to the Workday event where one exists, and only after Workday accepts it.', 'UC-10', 'Must', 'Given Workday rejects a change, then no audit record is written and the user sees "Workday rejected …".', ARCH],
    ['FR-022', 'The system shall show the audit log with period, change type, changed-by and organization filters, and export to Excel.', 'UC-10', 'Must', 'Given "Last 7 days" and "Role Assignment", then only matching records are shown and the count says so.', PO],
    ['FR-023', 'The system shall tell the user plainly when Workday rejects a change, and never show a success page for a change that did not happen.', 'UC-01–UC-04', 'Must', 'Given a forced Workday rejection, then OK is blocked with the rejection message and no receipt is shown.', 'Design principle'],
    ['FR-024', 'The system shall list shell roles still held by positions that have become vacant, with a way to confirm they are still needed or remove them.', 'UC-11', 'Should', 'Given a vacant position holding X:BPMS(ODMT):ROLE:ADVISORS, then it is listed; ticking Still Needed writes a REVIEW audit record.', ARCH + ' (deprovision on vacancy)'],
    ['FR-025', 'The system shall provide summary insight: requests by status and application, ISC turnaround, changes over time, and applications at a glance.', 'UC-10', 'Could', 'Given the Insights page, then counts match the request and audit records.', PO],
    ['FR-027', 'Every count shown on a summary card shall be clickable: on a page with a list it filters that list (marked ✓, a second click clears it); elsewhere it opens the list it counts.', 'UC-09, UC-10', 'Should', 'Given My Assignable Role Requests with 51 requests, when "4 pending" is clicked, then the list shows the 4 pending requests and the count shows ✓; clicking again shows all 51.', PO],
    ['FR-026', f'(Not built yet) The system shall scope each user to the applications they administer, read from their own AAA meta role assignments, on every page, search and orchestration.', 'UC-09', 'Should', 'Given a user who is AAA for X:CLW only, then they see and change only X:CLW data.', ARCH],
]
# Sources are to be confirmed (product owner, 2026-11-06)
set_rows(s, T(s, 'ID', 0), [r[:-1] + ['To be confirmed'] for r in FR], keep=1)
oos = heading(s, 'Explicitly out of scope').find_next_sibling('p')
insert_after(s, oos, para(
    '• Creating or changing real Workday security roles, security groups, supervisory organizations or academic units.\n'
    '• Renaming or deleting shell organizations (inactivate only).\n'
    '• Changing the AccessUBC extract or any target application.\n'
    '• Hiring or position management (HR keeps doing this; deprovisioning on vacancy follows from the position).\n'
    '• Mobile use.\n'
    '• Delegating creation of shell assignable roles without ISC review, context scoping, and a COMS API for automation such as AWS: later work, recorded in FR-026 and the delivery plan.\n'
    '• Migrating Appian COMS history (the existing organizations are already in Workday and are read from there).'))

# ---------------------------------------------------------------- 8. NFR
set_rows(s, T(s, 'ID', 1), [
    ['NFR-001', 'Volume', 'Applications, organizations and role assignments handled', 'Dev today: 33 applications, 614 shell organizations (subtypes X:META and X:SHELL), 829 positions; design for 5× growth', 'All'],
    ['NFR-002', 'Throughput / runtime', 'Bulk changes complete within platform limits', 'Grid: 50 changes per submit (page request ≤ 60 s); file: 1,000 changes per run (background run ≤ 60 min in production)', 'All'],
    ['NFR-003', 'Scheduling window', 'When it may run', 'On demand, any time; no scheduled jobs', 'All'],
    ['NFR-004', 'Availability', 'Expected uptime', 'Same as the Workday tenant; no other dependency', 'All'],
    ['NFR-005', 'Error tolerance', 'Partial-failure behaviour', 'Single changes: all or nothing from the user\'s view, verified after the call. Bulk: a failed row does not stop the others; each row shows DONE or FAILED with Workday\'s reason; the uploader sees the run status', 'All'],
    ['NFR-006', 'Retention', 'How long records are kept', 'Audit and request records: kept for the life of the app [TBC with records management]; bulk files and templates: [TBC]; Workday business process history is permanent', 'All'],
    ['NFR-007', 'Auditability', 'What must be reconstructable', 'Who changed what, on which organization, role and position, when, with what effective date, linked to the Workday event; records writable only by the app\'s integration user once set up', 'All'],
    ['NFR-008', 'Response time', 'Page load', '< 2 s server time for list pages (measured 0.5–2.0 s in dev); Shell Org Manager ~1.9 s', 'Extend'],
    ['NFR-009', 'Mobile', 'Tasks on the Workday mobile app', 'None (desktop only)', 'Extend'],
    ['NFR-010', 'Accessibility', 'WCAG 2.2 AA', 'Workday Canvas components as delivered; status never shown by colour alone (✓ / ○ / text)', 'Extend'],
    ['NFR-011', 'Security', 'Least privilege', 'Every page and every user-launched orchestration secured by a COMS security domain; inputs re-checked on the server', 'All'],
], keep=1)

# ---------------------------------------------------------------- 9. assumptions, constraints, risks
set_rows(s, T(s, 'ID', 2), [
    ['AS-01', 'Assumption', 'AccessUBC keeps extracting shell organizations, roles and assignments from Workday as today.', 'Changes made in ECO-COMS would not reach the target applications; needs a downstream change.', TBC, 'Open'],
    ['AS-02', 'Assumption', 'Each application\'s organizations use an organization type named after the application (e.g. X:CLW).', 'New organizations for that application are refused until its type exists (X:SET and X:PHA today).', 'ISC', 'Validated (dev)'],
    ['AS-03', 'Assumption', 'ISC is comfortable delegating shell organization creation within an application\'s own type.', 'The scope shrinks to requests only.', 'ISC Security', 'Open'],
    ['CN-01', 'Constraint', 'Workday allows one pending status change per organization; future-dated changes block another.', 'Users must choose a later date; the page explains the rejection.', 'n/a', 'Accepted'],
    ['CN-02', 'Constraint', 'Extend platform limits: 60 s per page request, 24 s per call, 25 s for a synchronous orchestration from a page, 60 min per background run.', 'Bulk work runs in the background with row limits (50 / 1,000).', 'n/a', 'Accepted'],
    ['CN-03', 'Constraint', 'Organizations can only be inactivated, never deleted; business process records are permanent.', 'Test data stays in the tenant; naming marks it as TEST.', 'n/a', 'Accepted'],
    ['RSK-01', 'Risk', 'Until the integration system user is set up, a user with Modify on the audit domain could edit audit records through the REST API.', 'Audit could be tampered with. Mitigation: ISU writes (built, awaiting ISU setup) and View-only access for users.', 'ISC Security', 'Open'],
    ['RSK-02', 'Risk', 'An AAA sees every application in ECO-COMS until context scoping is built.', 'Changes to another application\'s organizations. Mitigation: security domains, audit log, context scoping when built.', 'Product owner', 'Open'],
    ['RSK-03', 'Risk', 'Workday changes custom organization security or web services in a release.', 'Orchestrations fail. Mitigation: test after every deploy; check each release.', 'Developer', 'Open'],
    ['RSK-04', 'Risk', 'Single developer / knowledge concentration.', 'Support gaps. Mitigation: user guide, admin runbook and notes.', 'Product owner', 'Open'],
], keep=1)

# ---------------------------------------------------------------- 10. FAQ
set_rows(s, T(s, 'Question', 1), [
    ['Can ECO-COMS give anyone real Workday access?', 'No. Shell roles have no security group, so they carry no power inside Workday. ECO-COMS cannot create or change real roles, supervisory organizations or academic units.', 'To be confirmed', '2026-11-01'],
    ['Why can organizations not be renamed or deleted?', 'Role assignments depend on them; renaming would silently change what an assignment means. Organizations can be inactivated and reactivated.', 'To be confirmed', '2026-11-01'],
    ['What happens to access when someone leaves a position?', 'The role assignment stays on the position; with nobody in it, the next extract turns access off, and a replacement gets it back. The Access Review page lists shell roles on vacant positions.', 'To be confirmed', '2026-11-01'],
    ['How is a new application added?', 'A pattern maintainer adds a record on Maintain Application Pattern (prefixes, fields, rules, example). The application needs an organization type named after it in Workday.', 'Product owner', '2026-11-04'],
    ['Why does Clockwork keep ":PATTERN:" in its names?', 'About 395 existing Clockwork organizations use it; keeping it keeps names consistent.', 'Product owner', '2026-11-04'],
    ['Why CSV and not an Excel upload?', 'Workday orchestrations read CSV; there is no Excel parser. The Excel template checks rows and is saved as CSV for upload.', 'Product owner', '2026-10-31'],
], keep=1)

# ---------------------------------------------------------------- 11. supporting documentation
set_rows(s, T(s, 'Document name and URI'), [
    ['Requirements briefing + Current Architecture diagram', 'Functional Context Document', 'To be confirmed', '2026-11-01', 'Mandatory'],
    ['01: Business Requirements (this page)', 'Business Requirements Specification (page 01)', 'Crispin Mwanyumba', '2026-11-05', 'Mandatory'],
    ['02: Solutions Design', 'Solution Design (page 02)', 'Crispin Mwanyumba', '2026-11-05', 'Mandatory'],
    ['Shell Org Manager design options (design canvas); ECO-COMS presentation and live demo runbook (2026-11-05)', 'UX Design pack', 'Crispin Mwanyumba', '2026-11-05', 'Extend only'],
    [f'Security review / architecture review record {TBC}', 'Security review / architecture review record', TBC, TBC, 'Mandatory'],
    ['Application Patterns.xlsx (pattern formats per application)', 'Source data', TBC, '2026-11-02', 'Supporting'],
    ['ECO-COMS user guide, admin runbook and notes', 'User and support documentation', 'Crispin Mwanyumba', '2026-11-05', 'Supporting'],
], keep=1)

# ---------------------------------------------------------------- 12. sign-off
set_rows(s, T(s, 'Role'), [
    ['Business owner', TBC, '', '', ''],
    ['Product owner / functional lead', 'Crispin Mwanyumba', '', '', ''],
    ['Project / product manager', TBC, '', '', ''],
], keep=1)

open(OUT, 'w', encoding='utf-8').write(str(s))
print('wrote', OUT)
