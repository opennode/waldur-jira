import logging
import functools

from jira import JIRA, JIRAError

from django.utils import six

from nodeconductor.structure import ServiceBackend, ServiceBackendError
from . import executors


logger = logging.getLogger(__name__)


class JiraBackendError(ServiceBackendError):
    pass


class JiraBaseBackend(ServiceBackend):

    def __init__(self, settings, project=None, reporter_field=None, default_issue_type='Task', verify=False):
        self.settings = settings
        self.project = project
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

    @property
    def manager(self):
        if not hasattr(self, '_manager'):
            self._manager = JIRA(
                server=self.settings.backend_url,
                options={'verify': self.verify},
                basic_auth=(self.settings.username, self.settings.password),
                validate=False)

            if self.reporter_field:
                try:
                    self.reporter_field_id = next(
                        f['id'] for f in self.manager.fields() if self.reporter_field in f['clauseNames'])
                except StopIteration:
                    raise JiraBackendError("Can't find custom field %s" % self.reporter_field)

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
        jira = self.manager  # XXX: init manager before accessing reporter_field_id
        if self.reporter_field:
            args[self.reporter_field_id] = issue.user.uuid.hex

        backend_issue = jira.create_issue(**args)
        issue.backend_id = backend_issue.key
        issue.save(update_fields=['backend_id'])

    @reraise_exceptions
    def update_issue(self, issue):
        backend_issue = self.manager.issue(issue.backend_id)
        backend_issue.update(summary=issue.summary, description=issue.description)

    @reraise_exceptions
    def delete_issue(self, issue):
        self.manager.delete_issue(issue.backend_id)

    @reraise_exceptions
    def create_comment(self, comment):
        backend_comment = self.manager.add_comment(comment.issue.backend_id, comment.message)
        comment.backend_id = backend_comment.id
        comment.save(update_fields=['backend_id'])

    @reraise_exceptions
    def update_comment(self, comment):
        backend_comment = self.manager.comment(comment.issue.backend_id, comment.backend_id)
        backend_comment.update(body=comment.message)

    @reraise_exceptions
    def delete_comment(self, comment):
        backend_comment = self.manager.comment(comment.issue.backend_id, comment.backend_id)
        backend_comment.delete()
