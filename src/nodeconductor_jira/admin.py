from django.contrib import admin

from nodeconductor.core.admin import ExecutorAdminAction
from nodeconductor.structure import admin as structure_admin

from . import executors
from .models import JiraService, JiraServiceProjectLink, Project, Issue, Comment


class ProjectAdmin(structure_admin.ResourceAdmin):
    actions = ['import_issues']

    class ImportIssues(ExecutorAdminAction):
        executor = executors.ProjectImportExecutor
        short_description = 'Import issues'

    import_issues = ImportIssues()


admin.site.register(Issue, admin.ModelAdmin)
admin.site.register(Comment, admin.ModelAdmin)
admin.site.register(Project, ProjectAdmin)
admin.site.register(JiraService, structure_admin.ServiceAdmin)
admin.site.register(JiraServiceProjectLink, structure_admin.ServiceProjectLinkAdmin)
