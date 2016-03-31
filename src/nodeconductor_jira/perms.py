from nodeconductor.core.permissions import FilteredCollaboratorsPermissionLogic
from nodeconductor.structure.models import CustomerRole, ProjectRole, ProjectGroupRole
from nodeconductor.structure import perms as structure_perms


PERMISSION_LOGICS = (
    ('nodeconductor_jira.JiraService', FilteredCollaboratorsPermissionLogic(
        collaborators_query='customer__roles__permission_group__user',
        collaborators_filter={
            'customer__roles__role_type': CustomerRole.OWNER,
        },
        any_permission=True,
    )),
    ('nodeconductor_jira.JiraServiceProjectLink', FilteredCollaboratorsPermissionLogic(
        collaborators_query=[
            'service__customer__roles__permission_group__user',
            'project__project_groups__roles__permission_group__user',
        ],
        collaborators_filter=[
            {'service__customer__roles__role_type': CustomerRole.OWNER},
            {'project__project_groups__roles__role_type': ProjectGroupRole.MANAGER},
        ],
        any_permission=True,
    )),
    ('nodeconductor_jira.Project', structure_perms.resource_permission_logic),
    ('nodeconductor_jira.Issue', FilteredCollaboratorsPermissionLogic(
        collaborators_query=[
            'project__service_project_link__project__roles__permission_group__user',
            'project__service_project_link__project__customer__roles__permission_group__user',
        ],
        collaborators_filter=[
            {'project__service_project_link__project__roles__role_type': ProjectRole.ADMINISTRATOR},
            {'project__service_project_link__project__customer__roles__role_type': CustomerRole.OWNER},
        ],
        any_permission=True,
    )),
    ('nodeconductor_jira.Comment', FilteredCollaboratorsPermissionLogic(
        collaborators_query=[
            'issue__project__service_project_link__project__roles__permission_group__user',
            'issue__project__service_project_link__project__customer__roles__permission_group__user',
        ],
        collaborators_filter=[
            {'issue__project__service_project_link__project__roles__role_type': ProjectRole.ADMINISTRATOR},
            {'issue__project__service_project_link__project__customer__roles__role_type': CustomerRole.OWNER},
        ],
        any_permission=True,
    )),
)
