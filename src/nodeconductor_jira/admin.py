from django.contrib import admin

from nodeconductor.structure import admin as structure_admin

from .models import JiraService, JiraServiceProjectLink, Project, Issue, Comment


admin.site.register(Issue, admin.ModelAdmin)
admin.site.register(Comment, admin.ModelAdmin)
admin.site.register(Project, structure_admin.ResourceAdmin)
admin.site.register(JiraService, structure_admin.ServiceAdmin)
admin.site.register(JiraServiceProjectLink, structure_admin.ServiceProjectLinkAdmin)
