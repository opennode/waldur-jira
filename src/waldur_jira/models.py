import re
import urlparse

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils.encoding import python_2_unicode_compatible
from model_utils import FieldTracker
from model_utils.models import TimeStampedModel

from waldur_core.core import models as core_models
from waldur_core.structure import models as structure_models


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


class ProjectTemplate(core_models.UiDescribableMixin, structure_models.GeneralServiceProperty):
    @classmethod
    def get_url_name(cls):
        return 'jira-project-templates'


class Project(structure_models.NewResource):

    class Permissions(structure_models.NewResource.Permissions):
        extra_query = dict(available_for_all=True)

    service_project_link = models.ForeignKey(
        JiraServiceProjectLink, related_name='projects', on_delete=models.PROTECT)
    template = models.ForeignKey(ProjectTemplate)

    impact_field = models.CharField(max_length=64, blank=True)
    reporter_field = models.CharField(max_length=64, blank=True)
    available_for_all = models.BooleanField(default=False, help_text="Allow access to any user")

    def get_backend(self):
        return super(Project, self).get_backend(
            project=self.backend_id,
            impact_field=self.impact_field,
            reporter_field=self.reporter_field
        )

    def get_access_url(self):
        base_url = self.service_project_link.service.settings.backend_url
        return urlparse.urljoin(base_url, 'projects/' + self.backend_id)

    @classmethod
    def get_url_name(cls):
        return 'jira-projects'


class JiraPropertyIssue(core_models.UuidMixin, core_models.StateMixin, TimeStampedModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True)
    backend_id = models.CharField(max_length=255)

    class Permissions(object):
        customer_path = 'project__service_project_link__project__customer'
        project_path = 'project__service_project_link__project'
        extra_query = dict(project__available_for_all=True)

    class Meta(object):
        abstract = True


@python_2_unicode_compatible
class IssueType(core_models.UiDescribableMixin, structure_models.ServiceProperty):
    projects = models.ManyToManyField(Project, related_name='issue_types')

    @classmethod
    def get_url_name(cls):
        return 'jira-issue-types'

    def __str__(self):
        return self.name


@python_2_unicode_compatible
class Issue(structure_models.StructureLoggableMixin,
            JiraPropertyIssue):

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

    type = models.ForeignKey(IssueType)
    project = models.ForeignKey(Project, related_name='issues')
    summary = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    resolution = models.CharField(blank=True, max_length=255)
    priority = models.SmallIntegerField(choices=Priority.CHOICES, default=0)
    impact = models.SmallIntegerField(choices=Impact.CHOICES, default=0)
    status = models.CharField(max_length=255)
    updated = models.DateTimeField(auto_now_add=True)
    updated_username = models.CharField(max_length=255, blank=True)

    resource_content_type = models.ForeignKey(ContentType, blank=True, null=True, related_name='jira_issues')
    resource_object_id = models.PositiveIntegerField(blank=True, null=True)
    resource = GenericForeignKey('resource_content_type', 'resource_object_id')

    tracker = FieldTracker()

    def get_backend(self):
        return self.project.get_backend()

    @classmethod
    def get_url_name(cls):
        return 'jira-issues'

    @property
    def key(self):
        return self.backend_id

    @property
    def issue_user(self):
        return self.user  # XXX: avoid logging conflicts

    @property
    def issue_project(self):
        return self.project  # XXX: avoid logging conflicts

    def get_access_url(self):
        base_url = self.project.service_project_link.service.settings.backend_url
        return urlparse.urljoin(base_url, 'browse/' + self.backend_id)

    def get_log_fields(self):
        return ('uuid', 'issue_user', 'key', 'summary', 'status', 'issue_project')

    def get_description(self):
        template = settings.WALDUR_JIRA['ISSUE_TEMPLATE']['RESOURCE_INFO']
        if template and self.resource:
            return self.description + template.format(resource=self.resource)

        return self.description

    def __str__(self):
        return '{}: {}'.format(self.backend_id or '???', self.summary)


class JiraSubPropertyIssue(JiraPropertyIssue):

    class Permissions(object):
        customer_path = 'issue__project__service_project_link__project__customer'
        project_path = 'issue__project__service_project_link__project'
        extra_query = dict(issue__project__available_for_all=True)

    class Meta(object):
        abstract = True


@python_2_unicode_compatible
class Comment(structure_models.StructureLoggableMixin,
              JiraSubPropertyIssue):
    issue = models.ForeignKey(Issue, related_name='comments')
    message = models.TextField(blank=True)

    def get_backend(self):
        return self.issue.project.get_backend()

    @classmethod
    def get_url_name(cls):
        return 'jira-comments'

    @property
    def comment_user(self):
        return self.user  # XXX: avoid logging conflicts

    def get_log_fields(self):
        return ('uuid', 'comment_user', 'issue')

    def clean_message(self, message):
        template = settings.WALDUR_JIRA['COMMENT_TEMPLATE']
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
        template = settings.WALDUR_JIRA['COMMENT_TEMPLATE']
        if template and self.user:
            return template.format(user=self.user, body=self.message)
        return self.message

    def __str__(self):
        return '{}: {}'.format(self.issue.backend_id or '???', self.backend_id)


class Attachment(JiraSubPropertyIssue):
    issue = models.ForeignKey(Issue, related_name='attachments')
    file = models.FileField(upload_to='jira_attachments')

    def get_backend(self):
        return self.issue.project.get_backend()

    @classmethod
    def get_url_name(cls):
        return 'jira-attachments'
