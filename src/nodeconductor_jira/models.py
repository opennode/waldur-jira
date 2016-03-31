from django.db import models
from django.conf import settings
from django.utils.encoding import python_2_unicode_compatible
from model_utils.models import TimeStampedModel

from nodeconductor.core import models as core_models
from nodeconductor.structure import models as structure_models


class JiraService(structure_models.Service):
    projects = models.ManyToManyField(
        structure_models.Project, related_name='jira_services', through='JiraServiceProjectLink')

    @classmethod
    def get_url_name(cls):
        return 'jira'


class JiraServiceProjectLink(structure_models.ServiceProjectLink):
    service = models.ForeignKey(JiraService)

    @classmethod
    def get_url_name(cls):
        return 'jira-spl'


class Project(core_models.StateMixin, structure_models.ResourceMixin):
    service_project_link = models.ForeignKey(
        JiraServiceProjectLink, related_name='projects', on_delete=models.PROTECT)

    reporter_field = models.CharField(max_length=64, blank=True)
    default_issue_type = models.CharField(max_length=64, blank=True)

    def get_backend(self):
        return super(Project, self).get_backend(
            project=self.backend_id,
            reporter_field=self.reporter_field,
            default_issue_type=self.default_issue_type)

    def get_access_url(self):
        return self.service_project_link.service.settings.backend_url + 'projects/' + self.backend_id

    @classmethod
    def get_url_name(cls):
        return 'jira-projects'


@python_2_unicode_compatible
class Issue(core_models.UuidMixin, core_models.StateMixin, TimeStampedModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True)
    project = models.ForeignKey(Project, related_name='issues')
    summary = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    resolution = models.CharField(max_length=255)
    status = models.CharField(max_length=255)
    backend_id = models.CharField(max_length=255)

    def get_backend(self):
        return self.project.get_backend()

    @classmethod
    def get_url_name(cls):
        return 'jira-issues'

    def get_access_url(self):
        return self.project.service_project_link.service.settings.backend_url + 'browse/' + self.backend_id

    def __str__(self):
        return '{}: {}'.format(self.backend_id or '???', self.summary)


@python_2_unicode_compatible
class Comment(core_models.UuidMixin, core_models.StateMixin, TimeStampedModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True)
    issue = models.ForeignKey(Issue, related_name='comments')
    message = models.TextField(blank=True)
    backend_id = models.CharField(max_length=255)

    def get_backend(self):
        return self.issue.project.get_backend()

    @classmethod
    def get_url_name(cls):
        return 'jira-comments'

    def __str__(self):
        return '{}: {}'.format(self.issue.backend_id or '???', self.message)
