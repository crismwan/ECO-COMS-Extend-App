"""One-off rename (2026-11-06) to the naming standard:
  app:            XTND-0037-XFD_SEC-Custom_Organization_Management
  orchestrations: IORC_0037_XFD_SEC_<Functional_Description>  (sub-orchestrations: ..._Sub_<Description>)
                  Underscores, not hyphens: Orchestration Builder refuses a hyphen in a name (live 2026-11-06).

Renames each orchestration's `name`, its file (orchestration/ and tools/subflow_src/), and every reference
in pages, builders, tests and docs. Ids (and so sub-orchestration `subflowId`s) don't change.
CLAUDE.md is left alone: its mentions are history.

  python3 tools/rename_orchestrations.py          rename
  python3 tools/rename_orchestrations.py --check  exit 1 if any old name is still referenced
"""
import os, re, sys

P = 'IORC_0037_XFD_SEC_'
MAP = {
    'AddShellOrgPattern': P + 'Create_Pattern_Shell_Org',
    'AddShellOrg': P + 'Create_Application_Shell_Org',
    'AssignRolePositions': P + 'Assign_Remove_Role_Positions',
    'BulkRoleGridApply': P + 'Bulk_Role_Changes_From_Grid',
    'BulkRoleApply': P + 'Bulk_Role_Changes_From_CSV',
    'DenyRoleRequest': P + 'Close_Denied_Role_Request',
    'IscQueueCardData': P + 'ISC_Queue_Card_Data',
    'IscQueueHomeCard': P + 'ISC_Queue_Home_Card',
    'ManageShellOrgStatus': P + 'Change_Shell_Org_Status',
    'MyRoleRequestsCardData': P + 'My_Role_Requests_Card_Data',
    'MyRoleRequestsHomeCard': P + 'My_Role_Requests_Home_Card',
    'StartAAARequestReview': P + 'Start_Admin_Request_Review',
    'StartRoleRequestReview': P + 'Start_Role_Request_Review',
    'CreateShellOrganization': P + 'Sub_Create_Shell_Organization',
    'ProcessBulkRoleRow': P + 'Sub_Process_Bulk_Role_Row',
    'StartRequestReview': P + 'Sub_Start_Request_Review',
    'WriteAuditRecord': P + 'Sub_Write_Audit_Record',
}
# A name is a whole word: not part of a longer identifier (AddShellOrg vs AddShellOrgPattern).
RX = re.compile(r'(?<![A-Za-z0-9_])(' + '|'.join(sorted(MAP, key=len, reverse=True)) + r')(?![A-Za-z0-9_])')
TEXT = ('.orchestration', '.suborchestration', '.pmd', '.amd', '.smd', '.py', '.js', '.json', '.md', '.mmd',
        '.sh', '.yml', '.yaml', '.txt', '.script', '.card', '.carddefinition')
SKIP_DIRS = {'.git', 'node_modules', 'brand-assets'}
SKIP_FILES = {'CLAUDE.md', 'tools/rename_orchestrations.py'}

root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(root)


def files():
    for d, dirs, fs in os.walk('.'):
        dirs[:] = [x for x in dirs if x not in SKIP_DIRS]
        for f in fs:
            p = os.path.relpath(os.path.join(d, f))
            if p.endswith(TEXT) and p not in SKIP_FILES:
                yield p


check = '--check' in sys.argv
left = 0
for p in files():
    t = open(p, encoding='utf-8').read()
    n = RX.sub(lambda m: MAP[m.group(1)], t)
    if n != t:
        if check:
            left += 1
            print('old name still in', p)
        else:
            open(p, 'w', encoding='utf-8').write(n)
            print('updated', p)
if not check:
    for d in ('orchestration', 'tools/subflow_src'):
        for f in sorted(os.listdir(d)):
            stem, ext = os.path.splitext(f)
            if stem in MAP:
                os.rename(os.path.join(d, f), os.path.join(d, MAP[stem] + ext))
                print('renamed', d + '/' + f, '->', MAP[stem] + ext)
sys.exit(1 if left else 0)
