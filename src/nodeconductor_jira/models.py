import re

from django.db import models
from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils.encoding import python_2_unicode_compatible
from model_utils.models import TimeStampedModel

from nodeconductor.core import models as core_models
from nodeconductor.logging.loggers import LoggableMixin
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

    impact_field = models.CharField(max_length=64, blank=True)
    reporter_field = models.CharField(max_length=64, blank=True)
    default_issue_type = models.CharField(max_length=64, blank=True)

    def get_backend(self):
        return super(Project, self).get_backend(
            project=self.backend_id,
            impact_field=self.impact_field,
            reporter_field=self.reporter_field,
            default_issue_type=self.default_issue_type)

    def get_access_url(self):
        return self.service_project_link.service.settings.backend_url + 'projects/' + self.backend_id

    @classmethod
    def get_url_name(cls):
        return 'jira-projects'


@python_2_unicode_compatible
class Issue(core_models.UuidMixin, core_models.StateMixin, LoggableMixin, TimeStampedModel):

    class Priority:
        UNKNOWN = 0
        MINOR = 1
        MAJOR = 2
        CRITICAL = 3

        CHOICES = (
            (UNKNOWN, 'n/a'),
            (MINOR, 'Minor'),
            (MAJOR, 'Major'),
            (CRITICAL, 'Critical'),
        )

    class Impact:
        UNKNOWN = 0
        SMALL = 1
        MEDIUM = 2
        LARGE = 3

        CHOICES = (
            (UNKNOWN, 'n/a'),
            (SMALL, 'Small - Partial loss of service, one person affected'),
            (MEDIUM, 'Medium - One department or service is affected'),
            (LARGE, 'Large - Whole organization or all services are affected'),
        )

    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True)
    type = models.CharField(max_length=255)
    project = models.ForeignKey(Project, related_name='issues')
    summary = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    resolution = models.CharField(blank=True, max_length=255)
    priority = models.SmallIntegerField(choices=Priority.CHOICES, default=0)
    impact = models.SmallIntegerField(choices=Impact.CHOICES, default=0)
    status = models.CharField(max_length=255)
    updated = models.DateTimeField(auto_now_add=True)
    updated_username = models.CharField(max_length=255, blank=True)
    backend_id = models.CharField(max_length=255)

    @property
    def key(self):
        return self.backend_id

    def get_backend(self):
        return self.project.get_backend()

    @classmethod
    def get_url_name(cls):
        return 'jira-issues'

    def get_access_url(self):
        return self.project.service_project_link.service.settings.backend_url + 'browse/' + self.backend_id

    def get_log_fields(self):
        return ('uuid', 'user', 'key', 'summary', 'status')

    def __str__(self):
        return '{}: {}'.format(self.backend_id or '???', self.summary)


@python_2_unicode_compatible
class Comment(core_models.UuidMixin, core_models.StateMixin, LoggableMixin, TimeStampedModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True)
    issue = models.ForeignKey(Issue, related_name='comments')
    message = models.TextField(blank=True)
    backend_id = models.CharField(max_length=255)

    def get_backend(self):
        return self.issue.project.get_backend()

    @classmethod
    def get_url_name(cls):
        return 'jira-comments'

    def get_log_fields(self):
        return ('uuid', 'user', 'issue')

    def clean_message(self, message):
        template = getattr(settings, 'JIRA_COMMENT_TEMPLATE', None)
        if not template:
            return self.message

        User = get_user_model()
        template = re.sub(r'([\^~*?:\(\)\[\]|+])', r'\\\1', template)
        pattern = template.format(body='', user=User(full_name=r'(.+?)', username=r'([\w.@+-]+)'))
        match = re.search(pattern, message)

        if match:
            try:
                self.user = User.objects.get(username=match.group(2))
            except User.DoesNotExist:
                pass
            self.message = message[:match.start()]
        else:
            self.message = message

        return self.message

    def prepare_message(self):
        template = getattr(settings, 'JIRA_COMMENT_TEMPLATE', None)
        if template and self.user:
            return template.format(user=self.user, body=self.message)
        return self.message

    def __str__(self):
        return '{}: {}'.format(self.issue.backend_id or '???', self.message)


class Attachment(core_models.UuidMixin, core_models.StateMixin, TimeStampedModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True)
    file = models.FileField(upload_to='jira_attachments')
    issue = models.ForeignKey(Issue, related_name='attachments')
    backend_id = models.CharField(max_length=255)

    def get_backend(self):
        return self.issue.project.get_backend()

    @classmethod
    def get_url_name(cls):
        return 'jira-attachments'
