import logging
import functools

from jira import JIRA, JIRAError

from django.conf import settings
from django.utils import six
from django.utils.dateparse import parse_datetime

from nodeconductor.structure import ServiceBackend, ServiceBackendError


logger = logging.getLogger(__name__)


class JiraBackendError(ServiceBackendError):
    pass


class JiraBaseBackend(ServiceBackend):

    def __init__(self, settings, project=None, impact_field=None,
                 reporter_field=None, default_issue_type='Task', verify=False):

        self.settings = settings
        self.project = project
        self.impact_field = impact_field
        self.reporter_field = reporter_field
        self.default_issue_type = default_issue_type
        self.verify = verify

    def sync(self):
        self.ping(raise_exception=True)

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


class JiraBackend(JiraBaseBackend):
    """ NodeConductor interface to JIRA.
        http://pythonhosted.org/jira/
        http://docs.atlassian.com/jira/REST/latest/
    """

    @staticmethod
    def convert_field(value, choices, mapping_setting=None):
        """ Reverse mapping for choice fields """
        if mapping_setting:
            mapping = getattr(settings, mapping_setting, {})
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
                six.reraise(JiraBackendError, e)

            return self._manager

    def reraise_exceptions(func):
        @functools.wraps(func)
        def wrapped(self, *args, **kwargs):
            try:
                return func(self, *args, **kwargs)
            except JIRAError as e:
                six.reraise(JiraBackendError, e)
        return wrapped

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
    def get_project(self, project_id):
        return self.manager.project(project_id)

    @reraise_exceptions
    def create_project(self, project):
        self.manager.create_project(project.backend_id, name=project.name, assignee=self.settings.username)

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
            description=issue.description,
            issuetype={'name': self.default_issue_type},
        )
        if self.reporter_field:
            args[self.get_field_id_by_name(self.reporter_field)] = issue.user.username

        if self.impact_field and issue.impact:
            args[self.get_field_id_by_name(self.impact_field)] = issue.get_impact_display()

        if issue.priority:
            mapping = getattr(settings, 'JIRA_PRIORITY_MAPPING', {})
            priority = issue.get_priority_display()
            args['priority'] = {'name': mapping.get(priority, priority)}

        backend_issue = self.manager.create_issue(**args)
        issue.updated_username = issue.user.username
        issue.backend_id = backend_issue.key
        issue.resolution = backend_issue.fields.resolution or ''
        issue.status = backend_issue.fields.status.name or ''
        issue.type = self.default_issue_type
        issue.save(update_fields=['backend_id', 'resolution', 'status', 'type', 'updated_username'])

    @reraise_exceptions
    def update_issue(self, issue):
        backend_issue = self.manager.issue(issue.backend_id)
        backend_issue.update(summary=issue.summary, description=issue.description)

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
            issue = project.issues.create(
                impact=self.convert_field(impact, project.issues.model.Impact.CHOICES),
                type=fields.issuetype.name,
                status=fields.status.name,
                summary=fields.summary,
                priority=self.convert_field(
                    priority, project.issues.model.Priority.CHOICES, mapping_setting='JIRA_PRIORITY_MAPPING'),
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
