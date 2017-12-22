import functools
import logging

from jira import JIRA, JIRAError
from jira.client import _get_template_list
from jira.utils import json_loads

from django.conf import settings
from django.db import transaction
from django.utils import six
from django.utils.dateparse import parse_datetime

from waldur_core.structure import ServiceBackend, ServiceBackendError
from waldur_core.structure.utils import update_pulled_fields
from . import models


logger = logging.getLogger(__name__)


class JiraBackendError(ServiceBackendError):
    pass


def check_captcha(e):
    if e.response is None:
        return False
    if not hasattr(e.response, 'headers'):
        return False
    return e.response.headers['X-Seraph-LoginReason'] == 'AUTHENTICATED_FAILED'


def reraise_exceptions(func):
    @functools.wraps(func)
    def wrapped(self, *args, **kwargs):
        try:
            return func(self, *args, **kwargs)
        except JIRAError as e:
            six.reraise(JiraBackendError, e)
    return wrapped


class JiraBackend(ServiceBackend):
    """ Waldur interface to JIRA.
        http://pythonhosted.org/jira/
        http://docs.atlassian.com/jira/REST/latest/
    """

    def __init__(self, settings, project=None, impact_field=None,
                 reporter_field=None, verify=False):

        self.settings = settings
        self.project = project
        self.impact_field = impact_field
        self.reporter_field = reporter_field
        self.verify = verify

    def sync(self):
        self.ping(raise_exception=True)
        self.pull_project_templates()

    def ping(self, raise_exception=False):
        try:
            self.manager.myself()
        except JIRAError as e:
            if raise_exception:
                six.reraise(JiraBackendError, e)
            return False
        else:
            return True

    def get_resources_for_import(self):
        return [{
            'name': proj.name,
            'backend_id': proj.key,
        } for proj in self.manager.projects()]

    @staticmethod
    def convert_field(value, choices, mapping=None):
        """ Reverse mapping for choice fields """
        if mapping:
            mapping = {v: k for k, v in mapping.items()}
            value = mapping.get(value, value)

        try:
            return next(k for k, v in choices if v == value)
        except StopIteration:
            return 0

    @property
    def manager(self):
        try:
            return getattr(self, '_manager')
        except AttributeError:
            try:
                self._manager = JIRA(
                    server=self.settings.backend_url,
                    options={'verify': self.verify},
                    basic_auth=(self.settings.username, self.settings.password),
                    validate=False)
            except JIRAError as e:
                if check_captcha(e):
                    raise JiraBackendError('JIRA CAPTCHA is triggered. Please reset credentials.')
                six.reraise(JiraBackendError, e)

            return self._manager

    @reraise_exceptions
    def get_field_id_by_name(self, field_name):
        if not field_name:
            return None
        try:
            fields = getattr(self, '_fields')
        except AttributeError:
            fields = self._fields = self.manager.fields()
        try:
            return next(f['id'] for f in fields if field_name in f['clauseNames'])
        except StopIteration:
            raise JiraBackendError("Can't find custom field %s" % field_name)

    @reraise_exceptions
    def get_project_templates(self):
        url = self.manager._options['server'] + '/rest/project-templates/latest/templates'

        response = self.manager._session.get(url)
        json_data = json_loads(response)
        return _get_template_list(json_data)

    def pull_project_templates(self):
        backend_templates = self.get_project_templates()
        with transaction.atomic():
            for template in backend_templates:
                backend_id = template['projectTemplateModuleCompleteKey']
                icon_url = self.manager._options['server'] + template['iconUrl']
                models.ProjectTemplate.objects.update_or_create(
                    backend_id=backend_id,
                    defaults={
                        'name': template['name'],
                        'description': template['description'],
                        'icon_url': icon_url,
                    })

    @reraise_exceptions
    def get_project(self, project_id):
        return self.manager.project(project_id)

    @reraise_exceptions
    def create_project(self, project):
        self.manager.create_project(
            key=project.backend_id,
            name=project.name,
            assignee=self.settings.username,
            template_name=project.template.name,
        )
        self.pull_issue_types(project)

    def pull_issue_types(self, project):
        backend_project = self.get_project(project.backend_id)
        backend_issue_types = {
            issue_type.id: issue_type
            for issue_type in backend_project.issueTypes
        }
        project_issue_types = {
            issue_type.backend_id: issue_type
            for issue_type in project.issue_types.all()
        }
        global_issue_types = {
            issue_type.backend_id: issue_type
            for issue_type in models.IssueType.objects.filter(settings=self.settings)
        }

        new_issue_types = set(backend_issue_types.keys()) - set(project_issue_types.keys())
        for issue_type_id in new_issue_types:
            if issue_type_id in global_issue_types:
                issue_type = global_issue_types[issue_type_id]
            else:
                issue_type = self.import_issue_type(backend_issue_types[issue_type_id])
                issue_type.save()
            project.issue_types.add(issue_type)

        stale_issue_types = set(project_issue_types.keys()) - set(backend_issue_types.keys())
        project.issue_types.filter(backend_id__in=stale_issue_types).delete()

        common_issue_types = set(project_issue_types.keys()) & set(backend_issue_types.keys())
        for issue_type_id in common_issue_types:
            issue_type = project_issue_types[issue_type_id]
            imported_issue_type = self.import_issue_type(backend_issue_types[issue_type_id])
            update_pulled_fields(issue_type, imported_issue_type, ('name', 'description', 'icon_url'))

    def import_issue_type(self, backend_issue_type):
        return models.IssueType(
            settings=self.settings,
            backend_id=backend_issue_type.id,
            name=backend_issue_type.name,
            description=backend_issue_type.description,
            icon_url=backend_issue_type.iconUrl,
        )

    @reraise_exceptions
    def update_project(self, project):
        backend_project = self.manager.project(project.backend_id)
        backend_project.update(name=project.name)

    @reraise_exceptions
    def delete_project(self, project):
        self.manager.delete_project(project.backend_id)

    @reraise_exceptions
    def create_issue(self, issue):
        args = dict(
            project=issue.project.backend_id,
            summary=issue.summary,
            description=issue.get_description(),
            issuetype={'name': issue.type.name},
        )
        if self.reporter_field:
            args[self.get_field_id_by_name(self.reporter_field)] = issue.user.username

        if self.impact_field and issue.impact:
            args[self.get_field_id_by_name(self.impact_field)] = issue.get_impact_display()

        if issue.priority:
            mapping = settings.WALDUR_JIRA['PRIORITY_MAPPING']
            priority = issue.get_priority_display()
            args['priority'] = {'name': mapping.get(priority, priority)}

        backend_issue = self.manager.create_issue(**args)
        issue.updated_username = issue.user.username
        issue.backend_id = backend_issue.key
        issue.resolution = backend_issue.fields.resolution or ''
        issue.status = backend_issue.fields.status.name or ''
        issue.save(update_fields=['backend_id', 'resolution', 'status', 'type', 'updated_username'])

    @reraise_exceptions
    def update_issue(self, issue):
        backend_issue = self.manager.issue(issue.backend_id)
        backend_issue.update(summary=issue.summary, description=issue.get_description())

    @reraise_exceptions
    def delete_issue(self, issue):
        backend_issue = self.manager.issue(issue.backend_id)
        backend_issue.delete()

    @reraise_exceptions
    def create_comment(self, comment):
        backend_comment = self.manager.add_comment(comment.issue.backend_id, comment.prepare_message())
        comment.backend_id = backend_comment.id
        comment.save(update_fields=['backend_id'])

    @reraise_exceptions
    def update_comment(self, comment):
        backend_comment = self.manager.comment(comment.issue.backend_id, comment.backend_id)
        backend_comment.update(body=comment.prepare_message())

    @reraise_exceptions
    def delete_comment(self, comment):
        backend_comment = self.manager.comment(comment.issue.backend_id, comment.backend_id)
        backend_comment.delete()

    @reraise_exceptions
    def add_attachment(self, attachment):
        backend_issue = self.manager.issue(attachment.issue.backend_id)
        backend_attachment = self.manager.add_attachment(backend_issue, attachment.file)
        attachment.backend_id = backend_attachment.id
        attachment.save(update_fields=['backend_id'])

    @reraise_exceptions
    def remove_attachment(self, attachment):
        backend_attachment = self.manager.attachment(attachment.backend_id)
        backend_attachment.delete()

    @reraise_exceptions
    def import_project_issues(self, project):
        impact_field = self.get_field_id_by_name(self.impact_field) if self.impact_field else None
        for backend_issue in self.manager.search_issues('project=%s' % project.backend_id):
            backend_issue._parse_raw(backend_issue.raw)  # XXX: deal with weird issue in JIRA 1.0.4
            fields = backend_issue.fields
            impact = getattr(fields, impact_field, None)
            priority = fields.priority.name

            try:
                issue_type = models.IssueType.objects.get(
                    settings=project.settings,
                    backend_id=fields.issuetype.id
                )
            except models.IssueType.DoesNotExist:
                issue_type = self.import_issue_type(backend_issue.raw['issuetype'])
                issue_type.save()
                project.issue_types.add(issue_type)

            issue = project.issues.create(
                impact=self.convert_field(impact, project.issues.model.Impact.CHOICES),
                type=issue_type,
                status=fields.status.name,
                summary=fields.summary,
                priority=self.convert_field(
                    priority, project.issues.model.Priority.CHOICES, mapping=settings.WALDUR_JIRA['PRIORITY_MAPPING']),
                description=fields.description or '',
                resolution=fields.resolution or '',
                updated_username=fields.creator.displayName,
                backend_id=backend_issue.key,
                created=parse_datetime(fields.created),
                updated=parse_datetime(fields.updated),
                state=project.issues.model.States.OK)

            for backend_comment in self.manager.comments(backend_issue):
                tmp = issue.comments.model()
                tmp.clean_message(backend_comment.body)
                issue.comments.create(
                    user=tmp.user,
                    message=tmp.message,
                    created=parse_datetime(backend_comment.created),
                    backend_id=backend_comment.id,
                    state=issue.comments.model.States.OK)
