"""Orchestration names (naming standard 2026-11-06) and the names they had before.
Builders that derive an id from a name hash the OLD name (LEGACY), so the ids App Hub knows never change."""
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
LEGACY = {new: old for old, new in MAP.items()}


def legacy(name):
    """The pre-2026-11-06 name of an orchestration (or the name itself)."""
    return LEGACY.get(name, name)
