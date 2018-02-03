from django.contrib import admin

from waldur_core.core import admin as core_admin
from waldur_core.structure import admin as structure_admin

from . import models


class JiraPropertyAdmin(core_admin.UpdateOnlyModelAdmin,
                        structure_admin.BackendModelAdmin,
                        admin.ModelAdmin):
    list_display = ('name', 'description', 'settings')
    search_fields = ('name', 'description')


class ProjectTemplateAdmin(JiraPropertyAdmin):
    list_display = ('name', 'description')
    search_fields = ('name', 'description')


admin.site.register(models.Priority, JiraPropertyAdmin)
admin.site.register(models.IssueType, JiraPropertyAdmin)
admin.site.register(models.ProjectTemplate, ProjectTemplateAdmin)
admin.site.register(models.Issue, admin.ModelAdmin)
admin.site.register(models.Comment, admin.ModelAdmin)
admin.site.register(models.Project, structure_admin.ResourceAdmin)
admin.site.register(models.JiraService, structure_admin.ServiceAdmin)
admin.site.register(models.JiraServiceProjectLink, structure_admin.ServiceProjectLinkAdmin)
