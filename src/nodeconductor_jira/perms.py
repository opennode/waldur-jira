from nodeconductor.structure import perms as structure_perms


PERMISSION_LOGICS = (
    ('nodeconductor_jira.JiraService', structure_perms.service_permission_logic),
    ('nodeconductor_jira.JiraServiceProjectLink', structure_perms.service_project_link_permission_logic),
    ('nodeconductor_jira.Project', structure_perms.resource_permission_logic),
    ('nodeconductor_jira.Issue', structure_perms.property_permission_logic('project', user_field='user')),
    ('nodeconductor_jira.Comment', structure_perms.property_permission_logic('issue__project', user_field='user')),
    ('nodeconductor_jira.Attachment', structure_perms.property_permission_logic('issue__project', user_field='user')),
)
