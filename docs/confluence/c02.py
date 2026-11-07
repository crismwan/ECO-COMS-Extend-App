"""Fill 02 Solutions Design for ECO-COMS."""
import sys
from bs4 import BeautifulSoup
from fill import *

SRC = '02_part1.html'
OUT = sys.argv[1] if len(sys.argv) > 1 else 'out02.html'
s = BeautifulSoup(open(SRC, encoding='utf-8').read(), 'html.parser')
TBC = '[TBC]'
APP = 'ecocomsphase_xclw_cm_sync2_vmzvxm'
SO, AR, AP, MA, AUD, SET, PROF = ('Manage: COMS Shell Organizations', 'Manage: COMS Assignable Roles', 'Manage: COMS Admin Provisioning',
                                  'Maintain: COMS Assignable Roles', 'View: COMS Audit Log', 'Manage: COMS Application Setup', 'View: COMS Profile Section')


def diagram_after(title_start, src, alt, width=900):
    """Put the diagram after the last guidance paragraph of a 'Diagram — …' block."""
    diagram_html(s, title_start, img(src, alt, width))


# ---------------------------------------------------------------- page properties
pp = T(s, 'Solution name')
kv(s, pp, 'Solution name', 'XTND-0037-XFD_SEC-Custom_Organization_Management\nECO-COMS: Custom Organization Management System (shell organizations and shell roles in Workday)')
kv(s, pp, 'Solution ID', f'XTND-0037-XFD_SEC-Custom_Organization_Management\nExtend app reference ID {APP} (development tenant ubc_wcpdev2). Production reference ID to be fixed before the first upload to that account [TBC]; a reference ID can never be reused.')
kv(s, pp, 'Solution type', 'Extend App')
kv(s, pp, 'Solution pattern', 'In-tenant UI (one event-driven step on the review business process)')
kv(s, pp, 'Domain', 'HCM (security: custom organizations, assignable roles, role assignments)')
kv(s, pp, 'Document status', 'Draft (ready for review)')
kv(s, pp, 'Business owner(s)', f'{TBC}: Integrated Service Centre (ISC), Security / Access Management')
kv(s, pp, 'Product owner(s)', 'Crispin Mwanyumba, Integrated Service Centre')
kv(s, pp, 'Solutions Developer(s)', 'Crispin Mwanyumba')
kv(s, pp, 'Ticket Number', TBC)
kv(s, pp, 'Data classification', 'Medium risk (proposed; to confirm with UBC Privacy / Information Security)')
kv(s, pp, 'Personal information involved', 'Yes: worker names and position titles shown with role assignments; requester, approver and "changed by" names on request and audit records (Workday worker references). No sensitive categories.')
kv(s, pp, 'PIA required', f'{TBC}: to be confirmed with UBC Privacy')
kv(s, pp, 'Related solutions', 'Page 01 Business Requirements (ECO-COMS). Upstream: Workday positions, custom organization hierarchy. Downstream (unchanged): AccessUBC shell-role extract → Clockwork, OAMS, Admissions and other IRPS applications. Replaces Appian COMS.')
kv(s, pp, 'Version', 'v1.0 draft · last reviewed 2026-11-05 · next review due at sign-off [TBC]')

# ---------------------------------------------------------------- 1. type & pattern
cards = T(s, 'Workday Studio Integration')
for tr in cards.find_all('tr'):
    tds = tr.find_all('td')
    if len(tds) == 3:
        tds[0].decompose(); tds[1].decompose()
for col in cards.find_all('col')[:2]:
    col.decompose()
insert_before(s, cards.find('tr').find('td').find('p'), '<p>✓ <strong>Selected</strong></p>')
attr = T(s, 'Attribute', 0)
kv(s, attr, 'Solution type', 'Extend')
kv(s, attr, 'Delivery pattern', 'In-tenant UI (one event-driven step: IORC_0037_XFD_SEC_Close_Denied_Role_Request runs when the review process is denied or cancelled)')
kv(s, attr, 'Trigger', 'User task; business process event (Deny / Cancel); Workday Home card refresh')
kv(s, attr, 'Runs as', 'Initiating user (pages, all user-launched orchestrations, review start so the requester is the initiator). Exception, planned: an ISU writes audit and request records (§6.9). The BP-triggered IORC_0037_XFD_SEC_Close_Denied_Role_Request runs as the tenant\'s orchestration launch user.')
kv(s, attr, 'Interacts with external systems?', 'No. All calls stay inside the Workday tenant (Workday web services, REST, WQL, Graph). AccessUBC reads Workday through its existing extract.')
kv(s, attr, 'Mobile required?', 'No')

# ---------------------------------------------------------------- 2. architecture
insert_after(s, heading(s, 'Two to four sentences', tags=('p',)), para(
    'ECO-COMS is a Workday Extend app: 40 pages and 45 cards in one hub ("ECO-COMS"), reading Workday through REST, WQL and the Graph API with the signed-in user\'s token. '
    'Every change goes through a guarded orchestration (13 orchestrations sharing 4 sub-orchestrations) that re-checks its inputs, calls Workday\'s Human_Resources or Staffing web service, confirms Workday accepted the change, and only then writes an audit record. '
    'Application formats, role requests, audit records and bulk runs are kept in five Extend business objects and two attachment stores; the organizations, roles and assignments themselves live only in Workday, where AccessUBC already reads them.'))
a2 = T(s, 'Attribute', 1)
kv(s, a2, 'Build tool', 'App Builder (Code mode) and Orchestration Builder; source in a Git repository, built and checked by scripts, deployed by GitHub Actions with wdcli')
kv(s, a2, 'Runtime', 'Extend runtime (pages) and Orchestrate runtime (orchestrations)')
kv(s, a2, 'Entry point', 'Worklet / task (Workday search: Shell Org Manager, Audit Log Viewer, ISC Queue, Submit Assignable Role Request, Submit AAA Role Request, Withdraw Role Request); worker profile section; Workday Home cards; BP inbox steps; related action on an application record')
kv(s, a2, 'External systems', 'None')
kv(s, a2, 'Persistence', 'Extend business objects: COMS Application, COMS Assignable Role (requests), COMS Audit Log, COMS Bulk Run, COMS Bulk Row Result; attachment objects COMS Bulk Upload, COMS Bulk Template. Workday custom organizations and role assignments hold the real data.')
kv(s, a2, 'Reusable components consumed', 'Workday web services (Human_Resources v42.2, Staffing v42.2), Business Process REST API, WQL data sources (customOrganizations, topLevelOrganizations, allPositions, assignableRoles, academicUnits), Staffing v6 supervisory organization prompt values')
kv(s, a2, 'Reusable components produced', 'Sub-orchestrations IORC_0037_XFD_SEC_Sub_Create_Shell_Organization, IORC_0037_XFD_SEC_Sub_Process_Bulk_Role_Row, IORC_0037_XFD_SEC_Sub_Start_Request_Review, IORC_0037_XFD_SEC_Sub_Write_Audit_Record; schema-driven pattern engine (comsPatterns.script); application index (comsAppIndex.script); browse-by-supervisory-organization position picker pattern; static test suite of Extend pitfalls')
diagram_after('Diagram — Solution architecture', 'img/solution-architecture.png', 'Solution architecture: users reach the Extend app through SSO; orchestrations call Workday web services inside the tenant; AccessUBC reads Workday through its existing extract (the only boundary crossing, unchanged)')

# ---------------------------------------------------------------- 3. decision log
set_rows(s, T(s, 'ID', 0), [
    ['DD-01', 'Solution type: Studio vs Orchestrate vs Extend', 'Studio; Orchestrate only; Extend; keep Appian', 'People need screens (forms, review, lookup) and custom objects; data stays in the tenant', 'Model components deploy on the weekly service update; Extend skills to build', 'Solution architect / product owner', '2026-10'],
    ['DD-02', 'Where data is persisted', 'Copy organizations into app objects; keep them only in Workday', 'Organizations, roles and assignments live only in Workday (source of truth, read by AccessUBC). The app stores only what Workday has no place for: formats, requests, audit, bulk runs', 'Pages read large Workday lists (~600 organizations) at load', 'Solution architect', '2026-11-01'],
    ['DD-03', 'Authentication approach', 'ISU for everything; initiating user; mixed', 'Initiating user everywhere, so Workday\'s own security applies and the requester is the business process initiator (needed for Exclude Initiator). ISU only to write audit/request records so users can\'t edit them', 'An ISU must be assigned to the app in each tenant', 'Product owner', '2026-10-31'],
    ['DD-04', 'One schema-driven pattern form for every application', 'Clockwork-only form (as in Appian); one form per app; schema per app', 'Formats are data on the COMS Application record (prefixes, up to 7 fields, rules, examples), edited in the app; a new application needs no release', 'Field rules are checked on the page; the server checks prefix, field count and case (no regex in Orchestrate)', 'Solution architect / product owner', '2026-11-02, 11-04'],
    ['DD-05', 'Verify every change after the call (run-and-verify)', 'Trust the launch response; poll', 'An orchestration launch returns HTTP 200 even when it fails, so pages re-read Workday (organization in WQL, or audit count +1 written only after success) and block OK on failure', 'An extra read per submit', 'Developer', '2026-10-30'],
    ['DD-06', 'Organizations are add and inactivate/reactivate only', 'Allow rename/delete', 'A role assignment\'s meaning must never change; Workday cannot delete organizations anyway', 'Mistakes are fixed by inactivating', 'Solution architect', '2026-11-01'],
    ['DD-07', 'Bulk engine: asynchronous orchestration, CSV, row limits', 'Synchronous; Excel parsing; EIB', 'Page-launched synchronous calls stop at 25 s; Orchestrate reads CSV, not Excel. One engine (IORC_0037_XFD_SEC_Sub_Process_Bulk_Role_Row) behind the grid (50 rows) and the file (1,000 rows); validate first, then apply', 'Results arrive after a minute or two', 'Product owner', '2026-10-31'],
    ['DD-08', 'Role requests through a Workday business process', 'Status field only; email; BP', 'Approvals, inbox, delegation, Exclude Initiator, reminders and history come from Workday', 'BP definition is tenant configuration, set up per tenant', 'ISC / product owner', '2026-10-30'],
    ['DD-09', 'Shared sub-orchestrations', 'Copy steps into each orchestration', 'IORC_0037_XFD_SEC_Sub_Create_Shell_Organization, IORC_0037_XFD_SEC_Sub_Process_Bulk_Role_Row, IORC_0037_XFD_SEC_Sub_Start_Request_Review and IORC_0037_XFD_SEC_Sub_Write_Audit_Record exist once, so a fix is made once', 'A build step extracts them; sub-orchestration IDs must match', 'Developer', '2026-11-04'],
    ['DD-10', 'Graph API for the audit log', 'REST count + offset pages', 'Server-side sort (newest first) and filters on any field', 'Graph offsets need a first request; hub stays on REST (faster there)', 'Developer', '2026-11-04'],
    ['DD-11', 'Shell Org Manager application bar as pill cards', 'Search bar; drop-down; family/app cards (Option D)', 'Every application derived from Workday; two clicks to narrow; all actions visible (Option E on the design canvas)', 'Pill cards hold 10 pills; one card file per pill count', 'Product owner', '2026-11-05'],
    ['DD-12', 'Position picker browses supervisory organizations', 'Workday Graph prompt values; type-ahead only', 'Workday\'s own prompt values (Staffing v6) give the same browse experience as Workday; Graph prompt values don\'t cover positions', 'Several calls per level opened', 'Product owner', '2026-11-05'],
    ['DD-13', 'Naming standard: XTND-0037 app, IORC_0037 orchestrations', 'Keep ECO-COMS names; hyphens as written', 'App renamed XTND-0037-XFD_SEC-Custom_Organization_Management; orchestrations IORC_0037_XFD_SEC_<description> (Orchestration Builder refuses hyphens). IDs kept, so App Hub history stays', 'Business process launch configurations and Home cards store orchestration names and had to be re-pointed', 'Product owner', '2026-11-06'],
    ['DD-14', 'Organizations by subtype, applications by organization type', 'Find organizations by an X: in the code; create a new subtype', 'Organizations are the X:META and X:SHELL subtypes; an organization\'s application is its organization type; roles are those enabled for those types. Names and codes can be anything', 'Every list, check and test changed together (tools/subtype_apps.py); same 614 organizations and 12 roles as before', 'Product owner', '2026-11-06'],
    ['DD-15', 'Optional trailing pattern fields', 'One format per prefix; widen every rule', 'A field may be optional at the end and is left off the name when blank, so one format covers ORG:ELI and ORG:ARTS:HUMANITIES101 (ASMT) and ORG:SAO:GEOO (ADHC)', 'The server count check allows required-to-full field counts', 'Product owner', '2026-11-06'],
    ['DD-16', 'Clickable count cards', 'Leave counts as text; add buttons', 'Each count is a pill that filters its own page\'s list or opens the list it counts', 'One card file per target page (a pill\'s task can\'t be a parameter)', 'Product owner', '2026-11-06'],
], keep=1)

# ---------------------------------------------------------------- 4. traceability
TR = [
    ['FR-001', 'Every application listed, derived from Workday', 'comsAppIndex.script (appOfOrg: organization type); shellOrgManager bar; WQL allShellOrgs (subtype X:META / X:SHELL)', '§5.3, §6.7', 'TC-001'],
    ['FR-002', 'Narrow Shell Org Manager to one application', 'shellOrgManager (UX-002), SomPills cards, exact role match', '§5.5, §7.1', 'TC-002'],
    ['FR-003', 'Create shell organization (X:META / X:SHELL)', 'createShellOrgWizard/newShellOrg (UX-004); IORC_0037_XFD_SEC_Create_Application_Shell_Org → IORC_0037_XFD_SEC_Sub_Create_Shell_Organization', '§6.6 INT-01, §6.7', 'TC-003'],
    ['FR-004', 'Naming rules page + server', 'comsShellOrg.script; IORC_0037_XFD_SEC_Create_Application_Shell_Org guard', '§5.6', 'TC-004'],
    ['FR-005', 'Schema-driven pattern form with preview', 'newSchemaPattern (UX-006); comsPatterns.script; COMSApplication.patternSchema', '§5.6, §6.4', 'TC-005'],
    ['FR-006', 'Duplicate / prefix check', 'newSchemaPattern onSubmit; IORC_0037_XFD_SEC_Create_Pattern_Shell_Org CheckPatternName', '§5.6, §6.7', 'TC-006'],
    ['FR-007', 'Only the application\'s own org type', 'IORC_0037_XFD_SEC_Create_Application_Shell_Org / IORC_0037_XFD_SEC_Create_Pattern_Shell_Org (org type = application code)', '§6.9', 'TC-007'],
    ['FR-008', 'No rename / delete', 'No such page or call exists', '§3 DD-06', 'TC-008'],
    ['FR-009', 'Inactivate / reactivate', 'manageShellOrgStatus (UX-007); IORC_0037_XFD_SEC_Change_Shell_Org_Status (CheckInputs)', '§6.6 INT-02/03', 'TC-009'],
    ['FR-010', 'Add / remove positions; browse picker', 'editRoleAssignment (UX-008); IORC_0037_XFD_SEC_Assign_Remove_Role_Positions', '§6.6 INT-04', 'TC-010'],
    ['FR-011', 'Only shell roles', 'WQL allShellAssignableRolesinTenant: enabledForOrganizationTypes in the application types (appTypes list)', '§6.9', 'TC-011'],
    ['FR-012', 'Bulk grid (50) and file (1,000), validate then apply', 'bulkRoleGrid, bulkRoleChanges, bulkRoleResults, bulkRoleApply; IORC_0037_XFD_SEC_Bulk_Role_Changes_From_Grid / IORC_0037_XFD_SEC_Bulk_Role_Changes_From_CSV → IORC_0037_XFD_SEC_Sub_Process_Bulk_Role_Row', '§6.7, §6.11', 'TC-012'],
    ['FR-013', 'Pre-filled Excel template', 'bulkRoleTemplate (UX-015); COMS Bulk Template; CI build step', '§6.4', 'TC-013'],
    ['FR-014', 'Assignable role request', 'assignableRoleManager (UX-018); IORC_0037_XFD_SEC_Start_Role_Request_Review → IORC_0037_XFD_SEC_Sub_Start_Request_Review', '§6.8', 'TC-014'],
    ['FR-015', 'AAA role request, duplicate check', 'adminProvisioning (UX-019); WQL allAAArolesinTenant; IORC_0037_XFD_SEC_Start_Admin_Request_Review', '§5.6, §6.8', 'TC-015'],
    ['FR-016', 'Review BP with Exclude Initiator', 'Review COMS Assignable Role Request BP; review step pages (UX-022)', '§6.8', 'TC-016'],
    ['FR-017', 'Denied / withdrawn handling', 'IORC_0037_XFD_SEC_Close_Denied_Role_Request (BP-triggered); deleteAssignableRole (UX-018b)', '§6.8, §6.10', 'TC-017'],
    ['FR-018', 'ISC queue, overdue, reminder', 'iscRoleRequestsView (UX-021); comsRequestStats.script; BP delayed notification', '§6.8', 'TC-018'],
    ['FR-019', 'Maintain pattern format', 'appPatternSetup, editAppPattern (UX-009/010); comsAppSetup.script', '§5.6', 'TC-019'],
    ['FR-020', 'Inactive format takes no patterns', 'newSchemaPattern / Shell Org Manager checks on COMSApplication.active', '§7.1', 'TC-020'],
    ['FR-021', 'Audit after success, linked to event', 'IORC_0037_XFD_SEC_Sub_Write_Audit_Record sub-orchestration; COMS Audit Log (runId, eventWid)', '§6.4, §6.7', 'TC-021'],
    ['FR-022', 'Audit log filters and export', 'auditLogViewer (UX-016); Graph auditLogsNewest; comsAuditFilters.script', '§5.5', 'TC-022'],
    ['FR-023', 'Plain rejection message, no false success', 'Run-and-verify in onSubmit', '§5.7, §6.10', 'TC-023'],
    ['FR-024', 'Shell roles on vacant positions', 'accessReview, confirmAccessReview (UX-017)', '§5.3', 'TC-024'],
    ['FR-025', 'Insights', 'comsInsights, comsInsightsApps (UX-020)', '§5.3', 'TC-025'],
    ['FR-027', 'Clickable counts', 'tools/quick_filters.py: Quick<Task>Card pill cards; quick / status query parameters', '§5.5', 'TC-027'],
    ['FR-026', 'Context scoping', 'Not built yet: planned', '§9 RSK-02', 'n/a'],
    ['NFR-002', 'Bulk limits', 'Async orchestrations, row limits', '§6.11', 'TC-012'],
    ['NFR-008', 'Response time < 2 s', 'Speed passes; server timing', '§6.11', 'TC-030'],
    ['NFR-010', 'WCAG 2.2 AA', 'Canvas components as delivered; text + symbol for status', '§5.8', 'TC-031'],
]
set_rows(s, T(s, 'Requirement ID'), TR, keep=1)
insert_after(s, wrap_of(T(s, 'Requirement ID')), para('Test case IDs are proposed for page 03. Most are already automated in the repository\'s test runner (static, smoke and full suites); page 03 will map each TC to its suite.'))

# ---------------------------------------------------------------- 5.1 UX scope
set_rows(s, T(s, 'Question', 0), [
    ['Does this solution present an interface to a human?', 'Yes — Extend app'],
    ['Number of pages / screens', '40 pages (PMD) and 45 cards, one hub'],
    ['Primary persona (from page 01 §6.2)', 'Application administrator (AAA), e.g. Clockwork'],
    ['Where does the user come from?', 'Search (task names), worker profile section "COMS", Workday Home cards, inbox (review steps), related action on an application record'],
    ['Where does the user go afterwards?', 'Receipt pages link back to Shell Org Manager (same application) and the Audit Log; review steps return to the inbox'],
    ['Mobile in scope?', 'No'],
    ['Languages required', 'English only'],
    ['UX designer', 'Crispin Mwanyumba (product owner) with design review on the design canvas'],
    ['Design review date', '2026-11-05 (Shell Org Manager application bar); earlier reviews 2026-10-31, 11-02, 11-04'],
], keep=1, bold_first=True)

# ---------------------------------------------------------------- 5.2 entry points
set_rows(s, T(s, 'Entry point'), [
    ['Worklet / app card on the home page', 'Workday Home Card orchestrations (IORC_0037_XFD_SEC_My_Role_Requests_Home_Card, IORC_0037_XFD_SEC_ISC_Queue_Home_Card), placed with Create External Card', '"ECO-COMS: My Role Requests" · "ECO-COMS: ISC Queue"', 'Requesters; ISC reviewers', 'Run as the viewer; cached 1 hour'],
    ['Workday search', 'Tasks', 'Shell Org Manager · Audit Log Viewer · ISC Queue · Submit Assignable Role Request · Submit AAA Role Request · Withdraw Role Request · Add Shell Org Pattern', 'By task domain', 'Renamed 2026-11-01 to match how people ask for them'],
    ['Related action on a business object', 'Task with BO context (COMSApplication)', 'Maintain Application Pattern', SET, 'Shown on every application record (e.g. from the Audit Log)'],
    ['Business process step / Inbox', 'Review COMS Assignable Role Request definition', '"Review COMS Assignable Role Request: «role name»"', 'Approval group; ISC / HR administrators', 'Steps 1, 2 and 5 open ECO-COMS pages with "Step N of 5" banners'],
    ['Notification or direct link', 'BP notifications (completed; closed; 2-day reminder)', '"ECO-COMS role request completed" / "closed" / "Reminder: … waiting for review"', 'Requester; awaiting approvers', 'Tenant configuration'],
    ['Mobile app', 'n/a', 'n/a', 'n/a', 'Not mobile-enabled'],
], keep=1)
diagram_after('Diagram — Navigation map', 'img/navigation-map.png', 'Navigation map: entry points on the left, every page reachable from the RBAC Hub', 900)

# ---------------------------------------------------------------- 5.3 page inventory
PAGES = [
    ['UX-000', 'home', 'ECO-COMS (hub container)', 'View (hub)', 'Left navigation: RBAC Hub, FUH Administration, resources', SO, 'Search, app menu'],
    ['UX-001', 'hubLanding', 'ECO-COMS: RBAC Hub', 'View', 'Dashboard: Needs My Attention, ISC Queue, Shell Org Manager, Audit Log, App Activity, Pending by Age, Access Review, Insights, action cards', SO, 'Hub'],
    ['UX-002', 'shellOrgManager', 'ECO-COMS: Shell Org Manager', 'View', 'Application bar; tabs Summary, Application Patterns, Application Shell Organizations, Manage Role Assignments', SO, 'Hub, search, receipts'],
    ['UX-003', 'shellOrgDetail', 'ECO-COMS: Shell Organization – «org»', 'Detail', 'One organization: status, roles, history', SO, 'UX-002'],
    ['UX-004', 'createShellOrgWizard', 'Add New Shell Organization (wizard)', 'View (editWizard)', 'Wizard container with Review & Submit', SO, 'Hub, UX-002'],
    ['UX-004a', 'newShellOrg', 'Organization Details (wizard step)', 'Edit', 'Application, subtype X:META / X:SHELL, code, effective date', SO, 'UX-004'],
    ['UX-004b', 'newShellOrgSuccess', 'ECO-COMS: Shell Organization Created', 'View', 'Receipt', 'n/a (page open to app users)', 'UX-004'],
    ['UX-005', 'schemaPatternApps', 'ECO-COMS: Add Shell Org Pattern (choose application)', 'View', 'Applications with a format; Add Pattern per row', SO, 'Hub, UX-002, search'],
    ['UX-006', 'newSchemaPattern', 'ECO-COMS: Add Shell Org Pattern – «app»', 'Edit', 'Schema-driven form, live preview', SO, 'UX-005, UX-002'],
    ['UX-006a', 'newShellOrgPatternSuccess', 'ECO-COMS: Pattern Created', 'View', 'Receipt', 'n/a', 'UX-006'],
    ['UX-007', 'manageShellOrgStatus', 'ECO-COMS: Change Status – «org»', 'Edit', 'Inactivate / reactivate with confirmation', SO, 'UX-002, UX-003'],
    ['UX-007a', 'manageShellOrgStatusSuccess', 'ECO-COMS: Status Updated', 'View', 'Receipt', 'n/a', 'UX-007'],
    ['UX-008', 'editRoleAssignment', 'ECO-COMS: Manage Role Assignment – «role»', 'Edit', 'Add / remove positions (browse picker)', SO, 'UX-002, UX-003, UX-017'],
    ['UX-008a', 'roleAssignmentSuccess', 'ECO-COMS: Role Assignment Updated', 'View', 'Receipt', SO, 'UX-008'],
    ['UX-009', 'appPatternSetup', 'ECO-COMS: Maintain Application Pattern', 'View', 'Every application format; Add Application, Edit', SET, 'Hub, UX-002'],
    ['UX-010', 'editAppPattern', 'ECO-COMS: Add Application / Edit Pattern Format', 'Edit', 'Prefixes, fields grid, example; Copy from', SET, 'UX-009, related action'],
    ['UX-011', 'bulkRoleGridApps', 'ECO-COMS: Bulk Edit Role Assignments (choose application)', 'View', 'Application list', SO, 'UX-012'],
    ['UX-012', 'bulkRoleChanges', 'ECO-COMS: Bulk Role Changes', 'Edit', 'Upload CSV, effective date, Real run', SO, 'Hub'],
    ['UX-013', 'bulkRoleGrid', 'ECO-COMS: Bulk Edit Role Assignments', 'Edit', 'Current assignments (Remove) + Positions to Add grid, change counter', SO, 'UX-011'],
    ['UX-014', 'bulkRoleResults', 'ECO-COMS: Bulk Role Changes – Results', 'View', 'Run status and row results; Apply; My Uploads', SO, 'UX-012, UX-013, hub'],
    ['UX-014a', 'bulkRoleApply', 'ECO-COMS: Bulk Role Changes – Apply', 'Edit', 'Confirm and apply a validated run', SO, 'UX-014'],
    ['UX-015', 'bulkRoleTemplate', 'ECO-COMS: Bulk Role Changes – Template', 'View', 'Download the pre-filled Excel template; export grid', SO, 'Hub'],
    ['UX-015a', 'bulkTemplateUpload', 'ECO-COMS: Upload Bulk Template Version', 'Edit', 'Publish a template version (administrators)', SO, 'UX-015'],
    ['UX-016', 'auditLogViewer', 'ECO-COMS: Audit Log Viewer', 'View', 'Audit records with filters, Excel export', AUD, 'Hub, search, receipts'],
    ['UX-017', 'accessReview', 'ECO-COMS: Access Review', 'View', 'Shell roles held by vacant positions', SO, 'Hub'],
    ['UX-017a', 'confirmAccessReview', 'ECO-COMS: Review All Positions', 'Edit', 'Tick Still Needed; writes REVIEW records', SO, 'UX-017'],
    ['UX-018', 'assignableRoleManager', 'ECO-COMS: Submit Assignable Role Request', 'Edit', 'New shell role request', AR, 'Hub, search, profile'],
    ['UX-018a', 'assignableRoleManagerView', 'ECO-COMS: My Assignable Role Requests', 'View', 'Own requests; Withdraw, Retry/Reuse', AR, 'Hub, profile, Home card'],
    ['UX-018b', 'deleteAssignableRole', 'ECO-COMS: Withdraw Role Request', 'Edit', 'Withdraw own pending request (cancels the review)', AR, 'UX-018a, search'],
    ['UX-019', 'adminProvisioning', 'ECO-COMS: Submit AAA Role Request', 'Edit', 'AAA role request with duplicate check', AP, 'Hub, search'],
    ['UX-019a', 'adminProvisioningView', 'ECO-COMS: AAA Role Requests', 'View', 'All AAA requests', AP, 'Hub'],
    ['UX-020', 'comsInsights', 'ECO-COMS: Insights', 'View', 'Counts and charts across ECO-COMS', SO, 'Hub'],
    ['UX-020a', 'comsInsightsApps', 'ECO-COMS: Applications at a Glance', 'View', 'Per-application counts', SO, 'UX-020'],
    ['UX-021', 'iscRoleRequestsView', 'ECO-COMS: ISC Queue – «view»', 'View', 'Requests by type and status, waiting time, overdue', MA, 'Hub, search, Home card'],
    ['UX-022', 'reviewRoleRequestDetails', 'Review COMS Assignable Role Request (Step 1 of 5)', 'View (BP step)', 'Read-only request summary', MA, 'Inbox'],
    ['UX-022a', 'reviewRoleRequestApproval', 'Review COMS Assignable Role Request (Step 2 of 5)', 'View (BP step)', 'Approve / Deny context', MA, 'Inbox'],
    ['UX-022b', 'reviewRoleRequestAssignableRole', 'Add Workday Assignable Role (Step 5 of 5)', 'Edit (BP step)', 'Link the Workday role; request Approved', MA, 'Inbox'],
    ['UX-022c', 'reviewRoleRequestSecurityGroup', 'Create Security Group', 'Edit (BP step)', 'Kept in the model, not used in the current definition', MA, 'n/a'],
    ['UX-023', 'fuhLandingPage', 'ECO-COMS: Functional Unit Hierarchy Administration', 'View', 'Information only (no actions yet)', SO, 'Hub'],
    ['UX-024', 'errorPage', 'ECO-COMS: Something went wrong', 'View', 'Friendly error page for 400/401/403/404/408/500/503', 'n/a', 'Any page (SMD error mapping)'],
]
set_rows(s, T(s, 'ID', 1), [r[:6] + ['N', r[6]] for r in PAGES], keep=1)

# ---------------------------------------------------------------- 5.4 wireframes (screens from the dev tenant)
WF = [('UX-001', 'img/ux-rbac-hub.png', 'RBAC Hub'), ('UX-002', 'img/ux-shell-org-manager.png', 'Shell Org Manager with the BPMS family open'),
      ('UX-006', 'img/ux-add-pattern.png', 'Add Shell Org Pattern for Clockwork (X:CLW)'), ('UX-015', 'img/ux-download-template.png', 'Download Template'),
      ('UX-020', 'img/ux-insights.png', 'Insights'), ('Home', 'img/ux-home-cards.png', 'Workday Home cards')]
html_wf = ''.join(img(src, f'{uid} · {alt} (screen from the development tenant)', 700) for uid, src, alt in WF)
diagram_html(s, 'Diagram — Wireframes', html_wf)
set_rows(s, T(s, 'UX ID', 0), [
    ['UX-001', 'Screenshot above (RBAC Hub)', 'High-fidelity (built)', 'Product owner', 'Reviewed'],
    ['UX-002', 'Screenshot above; options A–E on the design canvas "Shell Org Manager application filter options"', 'High-fidelity (built)', 'Product owner', 'Approved (Option E, 2026-11-05)'],
    ['UX-006', 'Screenshot above', 'High-fidelity (built)', 'Product owner', 'Reviewed'],
    ['UX-015', 'Screenshot above', 'High-fidelity (built)', 'Product owner', 'Reviewed'],
    ['UX-020', 'Screenshot above', 'High-fidelity (built)', 'Product owner', 'Reviewed'],
    ['All other pages', 'Built pages in ubc_wcpdev2; presentation deck and live demo runbook (2026-11-05)', 'High-fidelity (built)', 'Product owner', 'Reviewed'],
], keep=1)

# ---------------------------------------------------------------- 5.5 components
set_rows(s, T(s, 'UX ID', 1), [
    ['UX-001', 'Body', 'Card containers (simple, pill and chart cards: stackedBarChart2)', 'Request, audit and bulk-run records; WQL shell orgs', 'Read-only; each card links to its page', 'Cards show zero counts and an action ("Nothing waiting")'],
    ['UX-002', 'Body top', 'Card container with dynamic cards (pill cards SomPills1–10, format cards)', 'comsAppIndex.barCards over WQL allShellOrgs + COMS Application', 'Pills reload the page with appCode / family', 'n/a (always lists applications)'],
    ['UX-002', 'Body', 'Tabs with grids (LIST style), donut chart card', 'WQL shell orgs, patterns, role assignments; COMS Application', 'Read-only; Manage / Details / Inactivate buttons', '"Nothing to show" text per tab, with the next step (e.g. Set Up Pattern Format)'],
    ['UX-006', 'Body', 'Field set with up to 7 text fields, read-only preview, date', 'COMS Application.patternSchema (json:parse)', 'Labels, hints and visibility from the schema; checked on change', 'Inactive application: "Application Inactive", no OK'],
    ['UX-008', 'Body', 'Read-only fields, instanceList (multi-select, dynamicMonikerLevels), date', 'WQL positions; Staffing v6 supervisory organization values', 'Browse or type; picked position clears errors', 'Current Positions "None"'],
    ['UX-013', 'Body', 'Editable grids (Current Assignments with Remove; Positions to Add), counter', 'WQL role assignments; instanceList role/org and position', 'Rows checked as they change; counter counts only valid changes', '"No changes yet" on OK'],
    ['UX-016', 'Body', 'Pill filter cards, donut, LIST grid with Excel export, instanceList links', 'Graph auditLogsNewest (newest 500)', 'Read-only; related actions on Workday objects and events', '"No changes match these filters"'],
    ['UX-018', 'Body', 'Grid (pending), instanceLists, text, date', 'COMS Assignable Role; WQL roles, positions, units', 'Generated role name; Enabled For one-of', 'Grid empty-state text'],
], keep=1)

# ---------------------------------------------------------------- 5.6 messages
set_rows(s, T(s, 'UX ID', 2), [
    ['UX-004a', 'Organization Code', 'Format: capitals, digits, _ or -; no spaces', 'On change and on Next', 'Use upper case (A–Z), digits, _ or -, with no spaces.', 'Error'],
    ['UX-004a', 'Effective Date', 'Weekday, this year or next', 'On change and on Next', 'Choose a weekday (Monday to Friday) in this year or next year.', 'Error'],
    ['UX-004a', 'Organization Code', 'Business rule: unique', 'On OK', 'An organization with this code already exists: «name».', 'Error'],
    ['UX-006', 'Each pattern field', 'Format from the schema', 'On change', '«Field»: «hint from the format» (e.g. Subject: 2–6 capital letters, then _V or _O).', 'Error'],
    ['UX-006', 'Pattern name', 'Business rule: unique', 'On OK', 'A Shell Org Pattern with this name already exists.', 'Error'],
    ['UX-004a, UX-006, UX-007, UX-008', 'OK', 'Run-and-verify', 'After the launch', 'Workday rejected this request, so nothing was created. Check the values and try again.', 'Error'],
    ['UX-007', 'Confirmation', 'Required', 'On OK', 'Tick the box to confirm you have checked the role assignments.', 'Error'],
    ['UX-007', 'OK', 'Workday rejection', 'After the launch', 'Workday rejected this status change, so nothing was changed. The organization may already have a future-dated change; choose a later date.', 'Error'],
    ['UX-008', 'Positions to Add / Remove', 'Cross-field: at least one', 'On OK', 'Select at least one position to add or remove.', 'Error'],
    ['UX-008', 'OK', 'Partial failure', 'After the launch', 'Workday rejected N of M changes. Check the role assignment in Workday and try again.', 'Error'],
    ['UX-013', 'Position (new row)', 'Business rule: not already held', 'On change', 'This position already holds this role on this organization.', 'Error'],
    ['UX-018, UX-019', 'Enabled For', 'Cross-field: one of two', 'On change', 'Cannot select both Functional Unit Hierarchy and Academic Unit.', 'Error'],
    ['UX-019', 'Application', 'Business rule: duplicate role', 'On change / OK', 'This AAA role already exists in Workday.', 'Error'],
    ['UX-010', 'Example', 'Cross-field: matches format', 'On change / OK', 'Field «n»: the example «value» does not match the format «hint».', 'Error'],
    ['UX-006', 'Inactive application', 'Business rule', 'On load', 'Application Inactive: this application takes no new patterns. Reactivate it on Maintain Application Pattern.', 'Info'],
], keep=1)

# ---------------------------------------------------------------- 5.7 states
st = T(s, 'State')
for key, val in [
    ('Empty', ['Grid has no rows (e.g. no pending requests, nothing on vacant positions)', 'A plain sentence saying there is nothing to show and why, e.g. "No shell roles are held by vacant positions."', 'Follow the suggested action button where there is one (e.g. Submit New Request)']),
    ('Loading', ['Large lists (~600 organizations) at page load; bulk runs in the background', 'Workday\'s page spinner (page loads under 2 s); bulk results page shows Running and a Refresh button', 'Refresh the results page after about 30 seconds']),
    ('Validation', ['A field breaks a rule', 'The exact message under the field (§5.6); OK refused until fixed; the error clears as soon as it is fixed', 'Fix the field']),
    ('Permission', ['User lacks the page\'s security domain', 'Workday sends them back to the hub; ISC-only pages show "Access Restricted: ISC Access Required"; HTTP errors go to the ECO-COMS error page', 'Ask for the named domain (user guide lists them)']),
    ('Downstream', ['Workday rejects the change or an orchestration fails', '"Workday rejected …" message on the page, no receipt; bulk rows FAILED with Workday\'s reason', 'Correct and try again; rows that succeeded stay done']),
    ('Success', ['Change accepted and verified', 'Receipt page with what changed, the effective date, links to Shell Org Manager and the Audit Log', 'Add another, return to the application, view the audit record']),
    ('Session', ['Session expires', 'Workday sign-in; entered values on an edit page are lost', 'Sign in and start the form again']),
]:
    for tr in st.find_all('tr'):
        c = tr.find_all('td')
        if c and c[0].get_text(' ', strip=True).startswith(key):
            for i, v in enumerate(val, 1):
                set_cell(s, st, st.find_all('tr').index(tr), i, v)

# ---------------------------------------------------------------- 5.8 accessibility checks
set_rows(s, T(s, 'Check'), [
    ['Automated scan', 'axe / Lighthouse on the main pages', TBC, 'Not run yet', TBC],
    ['Keyboard-only walkthrough', 'Manual: Shell Org Manager, Add Pattern, Manage Role Assignment', TBC, 'Not run yet', TBC],
    ['Screen reader walkthrough', 'NVDA on Add Shell Org Pattern', TBC, 'Not run yet', TBC],
    ['Contrast audit', 'Workday Canvas components as delivered; richText uses only #0B4D9C / #374151 / #B45309 on white; status shown with ✓ / ○ / text, not colour alone', 'Developer', 'Passes by design (to confirm)', '2026-11-05'],
], keep=1)

# ---------------------------------------------------------------- 5.9 content
c59 = T(s, 'Item')
for key, val in [('Task and page names', 'Tasks named as people ask: "Shell Org Manager", "Submit Assignable Role Request", "Withdraw Role Request"; every page title starts "ECO-COMS:"'),
                 ('Field labels', 'Workday terms reused: Organization Subtype, Effective Date, Positions, Enabled For, Assignable Role'),
                 ('Button labels', 'Actions named: Add Pattern, Narrow to this application, Set Up Pattern Format, Withdraw Request, Apply; OK only where Workday requires it'),
                 ('Dates', 'Effective dates in the user\'s format; timestamps in Pacific time to the minute with the zone shown'),
                 ('Translations', 'None'), ('Locales', 'English only'),
                 ('Tone', 'Direct, no blame; every error says what to do next')]:
    try:
        kv(s, c59, key, val, col=2)
    except KeyError:
        pass

# ---------------------------------------------------------------- 5.10 mobile
set_rows(s, T(s, 'Task'), [['All tasks', 'N', 'Administrators work at a desk; wide grids and Excel files', 'n/a']], keep=1)

# ---------------------------------------------------------------- 5.11 UX sign-off
set_rows(s, T(s, 'Reviewer'), [
    ['UX designer', 'Crispin Mwanyumba', '', '', ''],
    ['Product owner / functional lead', 'Crispin Mwanyumba', 'Approved (iterative reviews 2026-10-31 to 2026-11-05)', '2026-11-05', ''],
    ['Representative end user', f'{TBC} (Clockwork administrator for the pilot)', '', '', ''],
    ['Accessibility reviewer', TBC, '', '', ''],
    ['Apps & Config solution lead', TBC, '', '', ''],
], keep=1)

# ---------------------------------------------------------------- 6.1 what it does
insert_after(s, heading(s, 'In a technical context', tags=('p',)), para(
    'Sequence for a single change (create organization, create pattern, change status, change role positions):\n'
    '• The page loads Workday data with the user\'s token: WQL (custom and top-level organizations, positions, assignable roles, academic units), REST (app business objects, /workers/me), Graph (audit records).\n'
    '• The user fills the form; scripts check each field against the rules (for patterns, the application\'s schema JSON on its COMS Application record).\n'
    '• On OK, onSubmit launches the orchestration through a deferred inbound endpoint (launch URL with URL-encoded parameters) as the user.\n'
    '• The orchestration re-checks every input that decides what changes (CheckInputs / CheckPatternName / CheckMode), calls the Workday web service (Organization_Add_Update, Organization_Inactivate, Reactivate_Organization, Assign_Roles), stops if the response is not 2xx or is a SOAP fault (CheckWWSAccepted), extracts the Workday event reference, and calls IORC_0037_XFD_SEC_Sub_Write_Audit_Record with the run ID.\n'
    '• The page re-reads Workday (the new code in WQL, or the audit record count +1) and either shows the receipt or blocks OK with "Workday rejected …".\n'
    'Bulk changes: the grid writes its rows to COMS Bulk Row Result, the file upload stores a CSV in COMS Bulk Upload; an asynchronous orchestration (IORC_0037_XFD_SEC_Bulk_Role_Changes_From_Grid / IORC_0037_XFD_SEC_Bulk_Role_Changes_From_CSV) runs IORC_0037_XFD_SEC_Sub_Process_Bulk_Role_Row per row in VALIDATE or APPLY mode and updates COMS Bulk Run.\n'
    'Role requests: the request is saved in COMS Assignable Role; IORC_0037_XFD_SEC_Start_Role_Request_Review / IORC_0037_XFD_SEC_Start_Admin_Request_Review (→ IORC_0037_XFD_SEC_Sub_Start_Request_Review) starts the Review COMS Assignable Role Request event as the requester and stores its WID; review step pages complete the steps; IORC_0037_XFD_SEC_Close_Denied_Role_Request runs on Deny or Cancel.\n'
    'Reports: four model report data sources (ECO-COMS Role Requests, Audit Trail, Bulk Runs, Applications) for Workday custom reports.'))
set_rows(s, T(s, 'Question', 1), [
    ['Is this a workaround for a platform constraint?', 'Partly: Workday has no delegated, bounded way to create custom organizations or a schema for their names; ECO-COMS provides it with guarded calls.'],
    ['Does it feed a downstream process?', 'Yes, indirectly'],
    ['Which one', 'AccessUBC shell-role extract (unchanged), then the target applications'],
    ['Does it create, change or delete records?', 'Creates custom organizations; changes their status; adds/removes positions on role assignments; creates app records (requests, audit, bulk runs, formats). Deletes nothing in Workday.'],
    ['Which, and can it be reversed?', 'Organizations: inactivate (cannot delete). Role assignments: reversed by the opposite change (Assign Roles can\'t be rescinded). Requests: withdrawn/denied, not deleted once a review exists.'],
    ['Is it scheduled or user-triggered?', 'User-triggered (plus BP-triggered Deny/Cancel step)'],
    ['Why is this more appropriate than an EIB or core configuration?', 'Delegation to non-ISC users needs bounded, checked forms; an EIB or the standard tasks give no naming rules, no limit to an application\'s own org type, and show other roles. The bulk feature mirrors a Get/Put EIB inside those limits.'],
], keep=1, bold_first=True)
diagram_after('Diagram — Data flow', 'img/data-flow.png', 'One change: page checks, guarded orchestration, Workday call, audit after success, verification by the page; error branches shown')

# ---------------------------------------------------------------- 6.3 launch parameters
set_rows(s, T(s, 'Name'), [
    ['Validation Mode', 'Boolean', 'TRUE / FALSE', 'Yes', 'TRUE', 'Bulk runs: Real run unticked = VALIDATE (checks every row, changes nothing); ticked = validate and apply'],
    ['effectiveDate', 'Date (yyyy-MM-dd)', '2026-11-06', 'Yes', 'none', 'Every Workday change; weekday this year or next on the page'],
    ['appCode / orgType', 'Text', 'X:BPMS(AOC)', 'Yes', 'none', 'Organization type the new organization goes under; must equal the application code'],
    ['orgName / orgCode / orgSubtype', 'Text', 'X:BPMS(AOC):TST / X:SHELL', 'Yes', 'X:META', 'New organization; code = name'],
    ['patternName', 'Text', 'X:CLW:PATTERN:CPSC:CPSC_V:110:101:2026W2', 'Yes', 'none', 'Must start with «app»:«prefix»: and match the field count'],
    ['inactivate', 'Boolean', 'true', 'Yes', 'none', 'IORC_0037_XFD_SEC_Change_Shell_Org_Status; must agree with the action written to the audit record'],
    ['mode, roleWid, orgWid, positionIds', 'Text', 'ADD / REMOVE, P-00009', 'Yes', 'none', 'IORC_0037_XFD_SEC_Assign_Remove_Role_Positions; mode checked against allowed values'],
    ['changedBy, changedByWid, timestamp', 'Text', '«worker», WID, 2026-11-05T18:30:00Z', 'Yes', 'none', 'Written to the audit record (orchestrations have no other way to know who acted)'],
], keep=1)

# ---------------------------------------------------------------- 6.4 data model
set_rows(s, T(s, 'Object'), [
    ['COMS Application', 'appId, name, namePrefix, patternSchema (JSON), orgType, orgSubtype, active', 'Text / Boolean', 'X:CLW · PATTERN · {"fieldLabel1":"Academic Unit",…}', 'R/W', 'One record per application with a pattern format (15 today)'],
    ['COMS Assignable Role', 'roleName, status, shellOrgCode, positions, positionWids, effectiveDate, enabledFor*, requestedBy, reviewEventWid, denialReason, workdayAssignableRole', 'Text / Date / Instance', 'X:ADM:ROLE:COORDINATOR · Pending ISC Review', 'R/W', 'Role and AAA requests and their review status'],
    ['COMS Audit Log', 'timestamp, objectType, action, coName, roleName, positionName, effectiveDate, worker, changedByWid, orgWid, roleWid, positionWid, eventWid, runId, details', 'Text / Date / Instance', 'Role Assignment · ASSIGN POSITION · P-00009', 'Write once (ISU planned) / R', 'One record per accepted change'],
    ['COMS Bulk Run', 'batchRef, source, runMode, status, effectiveDate, uploadedBy*, changeCount, summary', 'Text', 'GRID-… · VALIDATE · Validated', 'R/W', 'One per grid submit or file upload'],
    ['COMS Bulk Row Result', 'batchRef, rowAction, roleName, orgName, positionId, result, message', 'Text', 'ADD · P-00009 · VALID', 'R/W', 'One per row of a bulk run'],
    ['COMS Bulk Upload (attachment)', 'file + batchRef, runMode, status', 'Attachment', 'role-changes.csv', 'R/W', 'Uploaded CSV files'],
    ['COMS Bulk Template (attachment)', 'file + version, asOf, rowCount', 'Attachment', 'ECO-COMS-role-assignments.xlsx', 'R/W', 'Pre-filled Excel template versions'],
], keep=1)
set_rows(s, T(s, 'Structure'), [
    ['Orchestration launch', 'Request', 'Query parameters on POST …/orchestrations/«Name»/launch (§6.3)', 'Orchestrate API, app base URL', 'Values URL-encoded; long free text avoided (gateway refuses some query strings)'],
    ['Bulk CSV', 'Request', 'Action, Role, Role WID, Organization, Organization WID, Position, Position ID, Assignee WID (one header row)', 'COMS Bulk Upload', 'Up to 1,000 ADD/REMOVE rows; unchanged rows ignored'],
    ['patternSchema', 'Internal', '{"prefixes":[…],"fieldLabel1..7","fieldRegex1..7","fieldHint1..7","fieldExample1..7","fieldAny1..7","example"}', 'COMS Application', 'Read by the pattern form and the server check'],
    ['Home card', 'Response', '{title, subtitle, linkText, linkPath}', 'CardData / HomeCard orchestrations', 'Rendered by Workday Home'],
], keep=1)
set_rows(s, T(s, 'ID', 2), [
    ['OBJ-01', 'COMS Application', 'appId (reference), patternSchema, active', 'Text / Boolean', 'Y', SET, 'Yes', 'Formats editable in the app'],
    ['OBJ-02', 'COMS Assignable Role', 'roleName (display), status, reviewEventWid …', 'Text / Date / Reference', 'Y', AR + ' (+ ISU writes planned)', 'Yes', 'Target of the review business process'],
    ['OBJ-03', 'COMS Audit Log', 'timestamp, action, objectType, eventWid, runId …', 'Text / Date / Reference', 'Y', AUD + ' (+ ISU writes planned)', 'Yes', 'Users read only once ISU writes are live'],
    ['OBJ-04', 'COMS Bulk Run', 'batchRef, status, runMode …', 'Text', 'Y', SO, 'Yes', ''],
    ['OBJ-05', 'COMS Bulk Row Result', 'batchRef, result, message …', 'Text', 'Y', SO, 'Yes', ''],
], keep=1)
comp = T(s, 'Component type')
for key, name in [('Business Object', 'COMS Application; COMS Assignable Role; COMS Audit Log; COMS Bulk Run; COMS Bulk Row Result'),
                  ('Task', 'Shell Org Manager; Add Shell Org Pattern; Audit Log Viewer; ISC Queue; Submit Assignable Role Request; Submit AAA Role Request; Withdraw Role Request; Maintain Application Pattern (record task); ECO-COMS Home; Hub Landing; My Role Requests; Submit Role Request (profile)'),
                  ('Security Domain', f'{SO}; {AR}; {AP}; {MA}; {AUD}; {SET}; {PROF}'),
                  ('Report', 'ECO-COMS Role Requests; ECO-COMS Audit Trail; ECO-COMS Bulk Runs; ECO-COMS Applications'),
                  ('Business Process', 'Review COMS Assignable Role Request'),
                  ('Attachment', 'COMS Bulk Upload; COMS Bulk Template'),
                  ('Page (PMD)', '40 pages (§5.3); profile group COMS (Worker Profile)'),
                  ('Orchestration', '13 orchestrations + 4 sub-orchestrations (§6.7)'),
                  ('Script module', '10 modules (§6.7)'),
                  ('Extend card', '45 page cards; 2 Workday Home Card orchestrations')]:
    kv(s, comp, key, name)
set_rows(s, T(s, 'App attribute'), [
    ['None yet', 'Nothing differs between tenants in the code today except the values below, which must move to app attributes before promotion', 'n/a', 'n/a', 'n/a', 'n/a'],
    ['Workday host (Excel export links)', 'Builds https://«host»/«tenant»/d/wid/«WID».htmld in exported audit rows', 'wcpdev.wd101.myworkday.com', TBC, TBC, TBC],
    ['ISU username (SMD isuAuth)', 'Integration user that writes audit and request records', 'DNU_ISU_ECO_COMS_DEPLOY_CMM', TBC, TBC, TBC],
], keep=1)

# ---------------------------------------------------------------- 6.5 reports
set_rows(s, T(s, 'Report name'), [
    ['ECO-COMS Role Requests', 'Model report (data source)', 'COMS Assignable Role', 'Workday custom reports; Insights', 'n/a', f'{AR}, {MA}, {AP}'],
    ['ECO-COMS Audit Trail', 'Model report (data source)', 'COMS Audit Log', 'Custom reports; audit', 'n/a', AUD],
    ['ECO-COMS Bulk Runs', 'Model report (data source)', 'COMS Bulk Run', 'Custom reports', 'n/a', SO],
    ['ECO-COMS Applications', 'Model report (data source)', 'COMS Application', 'Custom reports', 'n/a', f'{SET}, {AP}'],
    ['WQL queries (not reports): allShellOrgs, customOrganizations, allPositions, allShellAssignableRolesinTenant, allAAArolesinTenant', 'WQL', 'customOrganizations, topLevelOrganizations, allPositions, assignableRoles, academicUnits', 'Pages (§6.7)', 'Code starts with X:; shell roles only', 'User\'s own Workday security'],
], keep=1)
set_rows(s, T(s, 'Report field'), [
    ['roleName / status', 'X:ADM:ROLE:COORDINATOR · Approved', 'Request report: what was asked and where it is'],
    ['action / objectType / coName', 'ASSIGN POSITION · Role Assignment · X:BPMS(ODMT)…', 'Audit report: what changed'],
    ['eventWid / runId', 'WID / orchestration run ID', 'Links to the Workday event and the run'],
], keep=1)

# ---------------------------------------------------------------- 6.6 APIs
UT = 'Access Token From Initiating User'
set_rows(s, T(s, 'ID', 3), [
    ['INT-01', 'Human_Resources / Organization_Add_Update', 'v42.2', 'POST (SOAP)', 'Extend → Workday', UT, 'Create shell organization or pattern', 'Workday API throttling (429); retry config default'],
    ['INT-02', 'Human_Resources / Organization_Inactivate', 'v42.2', 'POST (SOAP)', 'Extend → Workday', UT, 'Inactivate organization', 'as above'],
    ['INT-03', 'Human_Resources / Reactivate_Organization', 'v42.2', 'POST (SOAP)', 'Extend → Workday', UT, 'Reactivate organization', 'as above'],
    ['INT-04', 'Staffing / Assign_Roles', 'v42.2', 'POST (SOAP)', 'Extend → Workday', UT, 'Add / remove positions on a role assignment (single and bulk)', 'as above'],
    ['INT-05', 'App BO REST /apps/«app»/v1/… (incl. reviewCOMSAssignableRoleRequestEvents)', 'v1', 'GET/POST/PATCH/DELETE', 'Internal', UT + ' (ISU planned for audit/request writes)', 'App records; start review event', 'REST: 100 rows per page'],
    ['INT-06', 'Business Process REST businessProcess/v1 (eventSteps submit, events cancel, comments)', 'v1', 'GET/POST', 'Internal', UT, 'Complete step 5, withdraw, read deny comments', ''],
    ['INT-07', 'WQL /wql/v1/data', 'v1', 'GET', 'Internal', UT, 'Organizations, positions, roles, units', '10,000 rows per page'],
    ['INT-08', 'Graph API /graphql/v1 (audit logs)', 'v1', 'POST', 'Internal', UT, 'Audit log, newest first', '100 per page'],
    ['INT-09', 'Staffing v6 values/jobChangesGroup/supervisoryOrganization', 'v6', 'GET', 'Internal', UT, 'Browse positions by supervisory organization', '100 per level page'],
    ['INT-10', 'Orchestrate API …/orchestrations/«Name»/launch', 'v1', 'POST', 'Internal', UT, 'Launch orchestrations from pages', 'Page call 24 s; sync run 25 s'],
], keep=1)
set_rows(s, T(s, 'Field'), [
    ['Organization_Name / Organization_Code', 'New organization name (code = name)', 'X:BPMS(AOC):TST', 'Yes', 'Built from application code + code'],
    ['Organization_Type_Name', 'Application code', 'X:BPMS(AOC)', 'Yes', 'Bounds the change to the application\'s own type'],
    ['Organization_Subtype_Name', 'X:META / X:SHELL', 'X:SHELL', 'Yes', 'Subtype by name only (v47 XSD has no subtype ID here)'],
    ['Role_Assignee (Position_ID)', 'Position', 'P-00009', 'Yes', 'Positions sent by Position_ID, not WID'],
    ['Assign_Roles_Event_Reference', 'Event WID in the response', 'WID', 'n/a', 'Stored on the audit record (eventWid)'],
], keep=1)

# ---------------------------------------------------------------- 6.7 processing logic
set_rows(s, T(s, 'Component', 1), [
    ['Assembly / Route / XSLT / ISA / Business Form Layout', 'Not applicable', 'Studio components; this is an Extend app', ''],
    ['Orchestrations (user-launched, synchronous)', 'IORC_0037_XFD_SEC_Create_Application_Shell_Org, IORC_0037_XFD_SEC_Create_Pattern_Shell_Org, IORC_0037_XFD_SEC_Change_Shell_Org_Status, IORC_0037_XFD_SEC_Assign_Remove_Role_Positions, IORC_0037_XFD_SEC_Start_Role_Request_Review, IORC_0037_XFD_SEC_Start_Admin_Request_Review, IORC_0037_XFD_SEC_My_Role_Requests_Card_Data, IORC_0037_XFD_SEC_ISC_Queue_Card_Data', 'One change each; guarded; secured by the launching page\'s domain', ''],
    ['Orchestrations (asynchronous)', 'IORC_0037_XFD_SEC_Bulk_Role_Changes_From_CSV (file), IORC_0037_XFD_SEC_Bulk_Role_Changes_From_Grid (grid)', 'Bulk engine', ''],
    ['Orchestration (BP-triggered)', 'IORC_0037_XFD_SEC_Close_Denied_Role_Request', 'Deny / Cancel on the review', 'Runs as the tenant launch user'],
    ['Workday Home Card orchestrations', 'IORC_0037_XFD_SEC_My_Role_Requests_Home_Card, IORC_0037_XFD_SEC_ISC_Queue_Home_Card', 'Cards on Workday Home', 'No security domain allowed on this type'],
    ['Sub-orchestrations', 'IORC_0037_XFD_SEC_Sub_Create_Shell_Organization, IORC_0037_XFD_SEC_Sub_Process_Bulk_Role_Row, IORC_0037_XFD_SEC_Sub_Start_Request_Review, IORC_0037_XFD_SEC_Sub_Write_Audit_Record', 'Shared steps', 'Callers pass "" for unused audit fields'],
], keep=1)
set_rows(s, T(s, 'Step #'), [
    ['1', 'Script (CreateValues)', 'GetInputParams', 'Launch query parameters', 'Typed values incl. runId = context.orchestrateId()', 'Fail', 'IORC_0037_XFD_SEC_Assign_Remove_Role_Positions'],
    ['2', 'Condition (Continue on Conditions)', 'CheckMode', 'mode', 'Continue only for ADD / REMOVE', 'Fail', 'Guard before any Workday call'],
    ['3', 'HTTP (SendWorkdayApiRequest)', 'CallOrganizationUpdate', 'SOAP Assign_Roles_Request', 'SOAP response', 'Continue to check', 'Staffing v42.2'],
    ['4', 'Condition', 'CheckWWSAccepted', 'Status code, SOAP fault', 'Continue if 2xx and no fault', 'Fail (logged)', 'Nothing is audited on failure'],
    ['5', 'Script', 'ExtractEvent', 'Response text', 'eventWid', 'Continue', 'Assign_Roles_Event_Reference'],
    ['6', 'Sub-orchestration call', 'CallWriteAudit', 'Audit fields', 'COMS Audit Log record', 'Fail', 'IORC_0037_XFD_SEC_Sub_Write_Audit_Record'],
    ['7', 'End', 'EndSync', '', 'Launch returns 200', '', 'Page verifies (audit total +1)'],
], keep=1)
insert_after(s, wrap_of(T(s, 'Step #')), para(
    'Other guards: IORC_0037_XFD_SEC_Change_Shell_Org_Status CheckInputs (code starts X:, is a real shell organization, action matches the inactivate flag); IORC_0037_XFD_SEC_Create_Pattern_Shell_Org CheckPatternName (starts «app»:«prefix»:, field count, upper case, no spaces); IORC_0037_XFD_SEC_Bulk_Role_Changes_From_CSV CheckInputs / CheckUpload (mode, upload belongs to the run, row limit).\n'
    'Expressions worth knowing: success = responseStatusCode.is2xxStatusCode() and not response.isSoapFault(); event WID read as text from the response (substringAfter "Assign_Roles_Event_Reference"); Orchestrate has no regex, so field formats are checked on the page.'))
diagram_after('Diagram — Orchestration flow', 'img/orchestration-flow.png', 'Bulk engine: one sub-orchestration per row, VALIDATE or APPLY, failures recorded per row')
set_rows(s, T(s, 'Page (UX ID)'), [
    ['UX-002', 'allShellOrgs (WQL), comsApplications (REST), shell role assignments (WQL)', 'GET', 'Page load', 'Organizations, formats, roles', UT, 'One organization list serves every tab and the application bar'],
    ['UX-004a', 'addShellOrg (deferred), verify (WQL)', 'POST / GET', 'OK (onSubmit)', 'Launch + verification', UT, 'Run-and-verify'],
    ['UX-006', 'launchAddShellOrgPattern (deferred), verifyPattern (deferred WQL)', 'POST / GET', 'OK', 'Launch + verification', UT, ''],
    ['UX-008', 'assignRolePositions (deferred), audit count', 'POST / GET', 'OK', 'Launch + audit total', UT, 'Positions browse: Staffing v6 values (deferred, per level)'],
    ['UX-013', 'Bulk rows (REST), IORC_0037_XFD_SEC_Bulk_Role_Changes_From_Grid launch', 'POST', 'OK', 'Run created', UT, 'Results page polls with Refresh'],
    ['UX-016', 'auditLogsNewest (Graph) pages 0–4', 'POST', 'Page load', 'Newest 500 audit records', UT, 'Pages 1–4 skipped when the total is smaller'],
    ['UX-018 / UX-019', 'Request write (REST), IORC_0037_XFD_SEC_Start_Role_Request_Review / IORC_0037_XFD_SEC_Start_Admin_Request_Review launch', 'POST', 'OK', 'Request + review event', UT, 'Review started as the requester'],
], keep=1)
set_rows(s, T(s, 'Script module'), [
    ['comsAppIndex', 'appOf, index, barCards, appIds', 'UX-002', 'Applications derived from organization codes; the application bar cards'],
    ['comsPatterns', 'schemaFor, buildName, checkField, formatGuide, summary', 'UX-002, UX-005, UX-006, UX-009, UX-013', 'Schema-driven pattern engine'],
    ['comsAppSetup', 'schemaJson, fieldsError, exampleName, copyOptions', 'UX-009, UX-010', 'Format editor checks'],
    ['comsShellOrg', 'orgName, codeError, preview', 'UX-004a', 'New organization naming'],
    ['comsValidations', 'isWeekday, isCurrentOrFutureYear, isDuplicatePattern …', 'Forms', 'Shared field checks'],
    ['comsRequestStats', 'filterRequests, waitingFor, isOverdue, countPending', 'UX-001, UX-018a, UX-019a, UX-020, UX-021', 'Request queue logic (business days)'],
    ['comsAuditFilters', 'filterLogs, countAction, activityByDay', 'UX-001, UX-016, UX-020', 'Audit filters and charts'],
    ['comsInsights / comsPendingAge / comsAccessReview', 'slices, appRows, buckets, vacantIds', 'UX-001, UX-017, UX-020', 'Dashboards and access review'],
], keep=1)

# ---------------------------------------------------------------- 6.8 BPs
set_rows(s, T(s, 'Business process'), [
    ['Review COMS Assignable Role Request', 'New', 'Initiation; Approval (Exclude Initiator); To Do Add Assignable Role; To Do Create Role-Based Security Group; Action Link Workday Role; notifications Completed / Closed / 2-day reminder; orchestration on Deny and Cancel', 'ISC', 'Y (definition, policy, approval group, launch configuration per tenant)'],
    ['Assign Roles', 'Consumed only', 'Called through the Assign_Roles web service', 'ISC / HR', 'N'],
], keep=1)

# ---------------------------------------------------------------- 6.9 security
set_rows(s, T(s, 'ID', 4), [
    ['SEC-01', 'Domains securing the data', 'Domain security policy', f'{SO}; {AR}; {AP}; {MA}; {AUD}; {SET}; {PROF}', 'View for GET · Modify for POST/PUT/PATCH/DELETE', 'One domain per area so each group gets only its pages'],
    ['SEC-02', 'Security groups granted access', 'Role / user-based', f'AAA holders → {SO}, {AR}, {AP}, {AUD}; ISC reviewers → {MA}, {AUD}; pattern maintainers → {SET}; [TBC: exact groups per tenant]', 'View + Modify', 'Approval group must be user-based or Unconstrained (the request object has no organization context)'],
    ['SEC-03', 'Page security domain (Extend)', 'Page security', 'Each page has one domain (§5.3)', 'View or Modify', 'Orchestrations launched by a page use the same domain (enabledForOrchestrationSecurity)'],
    ['SEC-04', 'ISSG', 'Integration System Security Group', f'{TBC} (for the ECO-COMS ISU)', 'Get/Put on audit and request domains', 'Only so records can be made read-only for users'],
    ['SEC-05', 'ISU', 'Integration System User', 'DNU_ISU_ECO_COMS_DEPLOY_CMM (planned; assigned to the app in App Manager per tenant)', 'Writes audit and request records only', 'Unavoidable to make audit records tamper-resistant: users keep View/Get only. Workday changes and BP starts stay as the user'],
    ['SEC-06', 'Credential', 'ISU (orchestration credential)', 'Stored in Orchestration Builder / Workday, never in the repository', 'n/a', 'CI tokens are GitHub secrets, refreshed by a person'],
], keep=1)
set_rows(s, T(s, 'Access matrix'), [
    ['', 'AAA (shell org + request domains)', 'Shell Org Manager, own app data*, audit', 'Organizations, patterns, role changes, requests', 'Status, positions on shell roles', 'Nothing (Workday has no delete)'],
    ['', 'ISC reviewer', 'ISC Queue, review steps, audit', 'Approvals (BP)', 'Request status via BP', 'No'],
    ['', 'Pattern maintainer', 'Maintain Application Pattern', 'Applications', 'Formats', 'No'],
    ['', 'Worker without COMS domains (negative)', 'Nothing: pages redirect to the hub / error page; launch URLs refused', 'No', 'No', 'No'],
    ['', 'Any user (negative)', 'Real Workday roles, supervisory orgs, academic units are never offered', 'No', 'No', 'No'],
], keep=1)
insert_after(s, wrap_of(T(s, 'Access matrix')), para('* Until context scoping is built, an AAA can see and change every application\'s shell data (page 01 RSK-02).'))

# ---------------------------------------------------------------- 6.10 errors
set_rows(s, T(s, 'Failure scenario'), [
    ['Source data missing or malformed', 'Page checks; orchestration guards; bulk row checks', 'Refuse on the page; guard stops the run; bulk row INVALID', 'No', 'The user', 'Message under the field / row reason'],
    ['Endpoint unavailable or timing out', 'Workday error codes (failOnStatusCodes)', 'Error page; nothing claimed as done', 'Default Workday retry config in orchestrations', 'The user', 'ECO-COMS error page'],
    ['Authentication or token failure', 'HTTP 401', 'Workday sign-in; CI deploy stops at the token step', 'No', 'User; developer for CI', 'Sign-in page; GitHub run'],
    ['Permission denied (403)', 'Domain policy', 'Redirect to hub or the friendly error page', 'n/a', 'The user', '"Access Restricted" / error page'],
    ['Partial success', 'Per position / per row result', 'Successful changes stay; failed ones listed', 'No (user re-runs the remainder)', 'The user', '"Workday rejected N of M changes" / FAILED rows'],
    ['Downstream rejects the payload', 'Not 2xx or SOAP fault (CheckWWSAccepted)', 'Run stops, nothing audited, logged with Workday\'s text; page blocks OK', 'No', 'The user; developer via app Logs', 'Page message; developer console Logs (15 min)'],
], keep=1)

# ---------------------------------------------------------------- 6.11 performance
set_rows(s, T(s, 'Dimension'), [
    ['Records per run', 'Single change: 1; grid: ≤ 50; file: ≤ 1,000 rows', '1,000', 'Page request 60 s; background run 60 min (production)', 'Asynchronous bulk; limits enforced on the page and in the orchestration'],
    ['Run duration', 'Single change 2–5 s; bulk ~1–2 min for tens of rows', TBC, 'Synchronous orchestration from a page 25 s', 'One Workday call per change; bulk async'],
    ['Concurrent users (Extend)', 'A few administrators', '< 20', 'Tenant-wide', 'No isCollection on large reads; WQL / Graph instead'],
    ['API calls per page load (Extend)', '3–12 (Shell Org Manager 3; RBAC Hub 12)', '16 (AAA request page)', '30 non-deferred inbound endpoints per page', 'Measured: list pages 0.5–2.0 s server time'],
    ['Third-party rate limit', 'n/a', 'n/a', 'Workday throttling (429)', 'Retry config'],
    ['Extend model component limits', '5 BOs, 2 attachments, 7 domains, 4 reports, 1 BP, 12 tasks, 40 pages', 'n/a', '20 BOs, 10 domains, 10 reports, 20 tasks, 75 pages per app', 'Headroom kept; unused components removed 2026-11-04'],
    ['File size / payload size', 'CSV ≤ 1,000 rows (~100 KB)', '1 MB', 'fileUploader 10 MB; launch message 20 MB', 'Row limit checked before processing'],
], keep=1)

# ---------------------------------------------------------------- 6.12 environments
for title in ('Studio', 'Orchestrate'):
    ct = [p for p in s.find_all('p', class_='ct') if p.get_text(strip=True) == title][0]
    nxt = ct.find_next_sibling()
    ct.decompose()
    while nxt is not None and nxt.name == 'p' and 'ct' not in (nxt.get('class') or []):
        n2 = nxt.find_next_sibling(); nxt.decompose(); nxt = n2
set_rows(s, T(s, 'Tenant'), [
    ['WCP Development (ubc_wcpdev2)', 'Build and test; deployed on every push to main', 'Sample only — never PII', 'GitHub Actions (wdcli) after static checks; smoke tests after each deploy', 'n/a', 'Write suite run by hand; test data marked TEST and listed in the admin runbook'],
    ['Implementation', 'Configure and test', TBC, 'Promote the latest passing Dev build', TBC, 'Re-assign the ISU in App Manager; set up the BP definition, policies, launch configuration'],
    ['Sandbox / Sandbox Preview', 'Production-like verification (Clockwork pilot)', 'Production copy', TBC, 'Weekly', 'Anything configured only here is lost at refresh'],
    ['Production', 'Live', 'Live', 'Account Administrator', 'n/a', 'Cannot be uninstalled; plan roll-forward'],
], keep=1)

# ---------------------------------------------------------------- 7. workflows
set_rows(s, T(s, 'Condition A'), [
    ['Shell Org Manager: no appCode', 'family empty', '—', 'Families card + "No pattern format yet" card; all data'],
    ['Shell Org Manager: no appCode', 'family = F', '—', 'Families card (✓ F) + F\'s applications as pills, 10 per card'],
    ['Shell Org Manager: appCode = A', 'A has no format record', '—', 'Navigation pills + "Set Up Pattern Format" card; Add Pattern hidden'],
    ['Shell Org Manager: appCode = A', 'record active', '—', 'Navigation pills + Ready card (Add Pattern, Maintain)'],
    ['Shell Org Manager: appCode = A', 'record inactive', '—', 'Navigation pills + Inactive card (Maintain); no new patterns'],
    ['Role assignment row', 'descriptor = A, or starts with "A:" or "A "', '—', 'Shown under A (exact match: X:LLIS excludes X:LLIS(CPE))'],
    ['Bulk row', 'mode VALIDATE', 'row passes checks', 'VALID, nothing changed'],
    ['Bulk row', 'mode APPLY', 'Workday accepts', 'DONE + audit record'],
    ['Bulk row', 'mode APPLY', 'Workday rejects', 'FAILED with Workday\'s message; next row continues'],
    ['Review request', 'Approve', 'step 5 completed', 'Approved, APPROVE audit, requester notified'],
    ['Review request', 'Deny or Cancel (incl. withdraw)', '—', 'Denied, inactive, DENY audit with the comment'],
], keep=1)
diagram_after('Diagram — Process workflow', 'img/process-workflow.png', 'Role request workflow: requester, ECO-COMS orchestrations and the Workday review business process, including deny, cancel and withdraw')
insert_after(s, heading(s, 'A worked example', tags=('p',)), para(
    'Monday 3 Nov, Clockwork exam coordination needs access for CPSC 110 section 101 in 2026W2.\n'
    '1. The Clockwork administrator searches "Shell Org Manager", picks Standalone → CLW. The Ready card shows the format "PATTERN: Academic Unit, Subject, Course, Section, Academic Period".\n'
    '2. Add Pattern: CPSC · CPSC_V · 110 · 101 · 2026W2. Typing "cpsc_v" shows an error; corrected, the preview reads X:CLW:PATTERN:CPSC:CPSC_V:110:101:2026W2. Effective date: a weekday.\n'
    '3. OK: IORC_0037_XFD_SEC_Create_Pattern_Shell_Org checks the prefix and five fields, IORC_0037_XFD_SEC_Sub_Create_Shell_Organization calls Organization_Add_Update under type X:CLW, subtype X:SHELL; Workday accepts; an audit record is written; the page finds the new code in WQL and shows "Pattern Created". Elapsed: a few seconds.\n'
    '4. The administrator opens Manage Role Assignments for the Clockwork role on that organization, browses My Organizations → their department, picks the coordinator\'s position, OK. Assign_Roles runs; the audit record links to the Assign Roles event.\n'
    '5. Overnight, AccessUBC extracts the new organization and assignment; Clockwork grants access for that section. No ISC ticket was raised.\n'
    '6. In January the coordinator moves to another job. The position becomes vacant, so the next extract removes access; Access Review lists the shell role on the vacant position until someone confirms or removes it.\n'
    'If step 3 had failed (e.g. the X:CLW organization type missing), the page would have shown "Workday rejected this request, so nothing was created" and no audit record would exist.'))

# ---------------------------------------------------------------- 8. naming register
set_rows(s, T(s, 'Object type'), [
    ['Integration system', 'n/a (Extend app)', 'n/a', 'n/a', 'n/a'],
    ['Custom report', 'ECO-COMS Role Requests / Audit Trail / Bulk Runs / Applications (model reports)', 'COMSRoleRequests, COMSAuditTrail, COMSBulkRunHistory, COMSApplicationSetup', 'Extend model naming', 'Y'],
    ['ISSG', 'ECO-COMS ISU security group', TBC, TBC, 'N'],
    ['ISU', 'ECO-COMS integration user', 'DNU_ISU_ECO_COMS_DEPLOY_CMM (dev); prod [TBC]', TBC, 'N'],
    ['Security domain', '7 COMS domains', 'ManageCOMSShellOrgs, ManageCOMSAssignableRoles, ManageCOMSAdminProvisioning, MaintainCOMSAssignableRoles, ViewCOMSAuditLog, ManageCOMSApplicationSetup, ViewCOMSProfileGroup', 'Manage/Maintain/View: COMS …', 'Y'],
    ['Extend app ID', 'ECO-COMS', f'{APP} (dev). Production: [TBC]', 'Begins with a letter; a–z 0–9 _ only; never reusable', 'N (production ID to agree)'],
    ['Extend business object', '5 objects + 2 attachments', 'COMSApplication, COMSAssignableRole, COMSAuditLog, COMSBulkRun, COMSBulkRowResult, COMSBulkUpload, COMSBulkTemplate', 'COMS prefix; IDs never change', 'Y'],
    ['Orchestration', '13 + 4 sub-orchestrations', 'IORC_0037_XFD_SEC_Create_Application_Shell_Org, IORC_0037_XFD_SEC_Create_Pattern_Shell_Org, IORC_0037_XFD_SEC_Change_Shell_Org_Status, IORC_0037_XFD_SEC_Assign_Remove_Role_Positions, IORC_0037_XFD_SEC_Bulk_Role_Changes_From_CSV, IORC_0037_XFD_SEC_Bulk_Role_Changes_From_Grid, IORC_0037_XFD_SEC_Start_Role_Request_Review, IORC_0037_XFD_SEC_Start_Admin_Request_Review, IORC_0037_XFD_SEC_Close_Denied_Role_Request, IORC_0037_XFD_SEC_My_Role_Requests_Card_Data, IORC_0037_XFD_SEC_ISC_Queue_Card_Data, IORC_0037_XFD_SEC_My_Role_Requests_Home_Card, IORC_0037_XFD_SEC_ISC_Queue_Home_Card; IORC_0037_XFD_SEC_Sub_Create_Shell_Organization, IORC_0037_XFD_SEC_Sub_Process_Bulk_Role_Row, IORC_0037_XFD_SEC_Sub_Start_Request_Review, IORC_0037_XFD_SEC_Sub_Write_Audit_Record', 'PascalCase verb + object', 'Y'],
    ['Business process', 'Review COMS Assignable Role Request', 'ReviewCOMSAssignableRoleRequest', 'Extend model', 'Y'],
], keep=1)

# ---------------------------------------------------------------- 9. ACR
set_rows(s, T(s, 'ID', 5), [
    ['AS-01', 'Assumption', 'AccessUBC extract continues unchanged', 'Changes do not reach target apps', 'Confirm with AccessUBC owners before pilot', TBC, 'Open'],
    ['AS-02', 'Assumption', 'Each application has an organization type named after its code', 'Workday refuses new organizations (X:SET, X:PHA today)', 'Set up the type when an application is onboarded (note on Add Application)', 'ISC', 'Validated (dev)'],
    ['CN-01', 'Constraint', 'Extend apps cannot be uninstalled; reference IDs never reused', 'Roll-forward only', 'Agree the production app ID before the first upload', 'Product owner', 'Open'],
    ['CN-02', 'Constraint', 'Orchestration launch returns 200 even on failure', 'False success if unchecked', 'Run-and-verify on every write page', 'Developer', 'Mitigated'],
    ['CN-03', 'Constraint', 'Model components deploy only with the weekly service update', 'A late model change can cost a week', 'Freeze the model before promotion', 'Developer', 'Accepted'],
    ['RSK-01', 'Risk', 'Audit and request records editable through REST until ISU writes are live', 'Tampering', 'ISU writes built (tools/isu_writes.py); needs ISU + App Manager assignment + policy change', 'ISC Security', 'Open'],
    ['RSK-02', 'Risk', 'No context scoping yet', 'An AAA could change another application\'s data', 'Security domains limit who uses the app; audit; context scoping when built', 'Product owner', 'Open'],
    ['RSK-03', 'Risk', 'Exclude Initiator not yet tested live with a requester in the approval group', 'Self-approval possible', 'Test before go-live; alternate approval group', 'ISC', 'Open'],
    ['RSK-04', 'Risk', 'Some API gateway refusals (HTML 403) on long launch query strings', 'Launch fails', 'Pass codes/IDs instead of long text; URL-encode values', 'Developer', 'Mitigated'],
    ['RSK-05', 'Risk', 'CI tokens expire (1 h / 8 h)', 'Deploys stop', 'Documented refresh; static checks run first', 'Developer', 'Accepted'],
], keep=1)

# ---------------------------------------------------------------- supporting docs, tickets, sign-off
set_rows(s, T(s, 'Document name and URI'), [
    ['Requirements from architect + Current Architecture diagram', 'Functional Context Document', 'Solution architect', '2026-11-01', 'Mandatory'],
    ['01: Business Requirements (ECO-COMS)', 'Business Requirements Specification (page 01)', 'Crispin Mwanyumba', '2026-11-05', 'Mandatory'],
    ['02: Solutions Design (this page)', 'Solution Design (page 02)', 'Crispin Mwanyumba', '2026-11-05', 'Mandatory'],
    ['Design canvas "Shell Org Manager application filter options"; presentation and live demo runbook 2026-11-05', 'UX Design pack', 'Crispin Mwanyumba', '2026-11-05', 'Extend only'],
    [f'Privacy Impact Assessment {TBC}', 'Privacy Impact Assessment', TBC, TBC, 'If personal information is involved'],
    [f'Security review {TBC}', 'Security review / architecture review record', TBC, TBC, 'Per governance'],
    ['Appian COMS documentation (shell roles, IRPS)', 'Integration Design Document (legacy format)', 'Solution architect', TBC, 'Optional'],
    ['App Hub build log (developer.workday.com → app → Builds)', 'App Hub build log', 'CI', 'Each deploy', 'Extend / Orchestrate'],
    ['GitHub repository crismwan/ECO-COMS-Extend-App (code, user guide, admin runbook, notes, tests)', 'Source repository', 'Crispin Mwanyumba', '2026-11-05', 'Studio (used here for Extend)'],
], keep=1)
set_rows(s, T(s, 'System'), [['Jira', TBC, 'Epic', ''], ['ServiceNow', TBC, 'Change', '']], keep=1)
set_rows(s, T(s, 'Role', 0), [
    ['Apps & Config solution lead', TBC, '', '', ''],
    ['Developer / builder', 'Crispin Mwanyumba', '', '', ''],
    ['UX designer (mandatory for Extend)', 'Crispin Mwanyumba', '', '', ''],
    ['Product owner / functional lead', 'Crispin Mwanyumba', '', '', ''],
    ['Security', f'{TBC} (ISC Security)', '', '', ''],
    ['Architecture review (per governance)', TBC, '', '', ''],
], keep=1)

open(OUT, 'w', encoding='utf-8').write(str(s))
print('wrote', OUT)
