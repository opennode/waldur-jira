from django.db import models
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

    @classmethod
    def get_url_name(cls):
        return 'jira-projects'


class Issue(core_models.UuidMixin, TimeStampedModel):
    project = models.ForeignKey(Project, related_name='issues')
    summary = models.CharField(max_length=255)
    assignee = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    resolution = models.CharField(max_length=255)
    status = models.CharField(max_length=255)
    backend_id = models.CharField(max_length=255)

    def get_backend(self):
        return self.project.get_backend()

    @classmethod
    def get_url_name(cls):
        return 'jira-issues'


class Comment(core_models.UuidMixin, TimeStampedModel):
    issue = models.ForeignKey(Issue, related_name='comments')
    author = models.CharField(max_length=255)
    message = models.TextField(blank=True)
    backend_id = models.CharField(max_length=255)

    def get_backend(self):
        return self.issue.project.get_backend()

    @classmethod
    def get_url_name(cls):
        return 'jira-comments'
