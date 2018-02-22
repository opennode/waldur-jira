import functools
import logging

from django.conf import settings
from django.db import transaction, IntegrityError
from django.utils import six
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.utils.functional import cached_property
from jira import JIRA, JIRAError
from jira.client import _get_template_list
from jira.utils import json_loads
from rest_framework import status

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

    def __init__(self, settings, project=None, verify=False):

        self.settings = settings
        self.project = project
        self.verify = verify

    def sync(self):
        self.ping(raise_exception=True)
        self.pull_project_templates()
        self.pull_priorities()

    def ping(self, raise_exception=False):
        try:
            self.manager.myself()
        except JIRAError as e:
            if raise_exception:
                six.reraise(JiraBackendError, e)
            return False
        else:
            return True

    @reraise_exceptions
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

    @reraise_exceptions
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
    def pull_priorities(self):
        backend_priorities = self.manager.priorities()
        with transaction.atomic():
            backend_priorities_map = {
                priority.id: priority for priority in backend_priorities
            }

            waldur_priorities = {
                priority.backend_id: priority
                for priority in models.Priority.objects.filter(settings=self.settings)
            }

            stale_priorities = set(waldur_priorities.keys()) - set(backend_priorities_map.keys())
            models.Priority.objects.filter(backend_id__in=stale_priorities)

            for priority in backend_priorities:
                models.Priority.objects.update_or_create(
                    backend_id=priority.id,
                    settings=self.settings,
                    defaults={
                        'name': priority.name,
                        'description': priority.description,
                        'icon_url': priority.iconUrl,
                    })

    @reraise_exceptions
    def import_priority(self, priority):
        return models.Priority(
            backend_id=priority.id,
            settings=self.settings,
            name=priority.name,
            description=getattr(property, 'description', ''),
            icon_url=priority.iconUrl,
        )

    @reraise_exceptions
    def get_project(self, project_id):
        return self.manager.project(project_id)

    @cached_property
    def default_assignee(self):
        # JIRA REST API basic authentication accepts either username or email.
        # But create project endpoint does not accept email.
        # Therefore we need to get username for the logged in user.
        user = self.manager.myself()
        return user['name']

    @reraise_exceptions
    def create_project(self, project):
        self.manager.create_project(
            key=project.backend_id,
            name=project.name,
            assignee=self.default_assignee,
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
            update_pulled_fields(issue_type, imported_issue_type, (
                'name', 'description', 'icon_url', 'subtask'
            ))

    def import_issue_type(self, backend_issue_type):
        return models.IssueType(
            settings=self.settings,
            backend_id=backend_issue_type.id,
            name=backend_issue_type.name,
            description=backend_issue_type.description,
            icon_url=backend_issue_type.iconUrl,
            subtask=backend_issue_type.subtask,
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

        if issue.priority:
            args['priority'] = {'name': issue.priority.name}

        if issue.parent:
            args['parent'] = {'key': issue.parent.backend_id}

        backend_issue = self.manager.create_issue(**args)
        issue.backend_id = backend_issue.key
        self._backend_issue_to_issue(backend_issue, issue)
        issue.save()

    def create_issue_from_jira(self, project, key):
        backend_issue = self.get_backend_issue(key)
        if not backend_issue:
            logger.debug('Unable to create issue with key=%s, '
                         'because it has already been deleted on backend.', key)
            return

        if models.Issue.objects.filter(backend_id=key, project=project).exists():
            logger.debug('Unable to create issue with key=%s, '
                         'because it already exists in Waldur.', key)
            return

        issue = models.Issue(project=project, backend_id=key)
        self._backend_issue_to_issue(backend_issue, issue)
        try:
            issue.save()
        except IntegrityError:
            logger.debug('Unable to create issue with key=%s, '
                         'because it has been created in another thread.', key)

    def update_issue(self, issue):
        backend_issue = self.get_backend_issue(issue.backend_id)
        if not backend_issue:
            logger.debug('Unable to update issue with key=%s, '
                         'because it has already been deleted on backend.', issue.backend_id)
            return

        backend_issue.update(summary=issue.summary, description=issue.get_description())

    def update_issue_from_jira(self, issue):
        start_time = timezone.now()

        backend_issue = self.get_backend_issue(issue.backend_id)
        if not backend_issue:
            logger.debug('Unable to update issue with key=%s, '
                         'because it has already been deleted on backend.', issue.backend_id)
            return

        issue.refresh_from_db()

        if issue.modified > start_time:
            logger.debug('Skipping issue update with key=%s, '
                         'because it has been updated from other thread.', issue.backend_id)
            return

        self._backend_issue_to_issue(backend_issue, issue)
        issue.save()

    def delete_issue(self, issue):
        backend_issue = self.get_backend_issue(issue.backend_id)
        if backend_issue:
            backend_issue.delete()
        else:
            logger.debug('Unable to delete issue with key=%s, '
                         'because it has already been deleted on backend.', issue.backend_id)

    def delete_issue_from_jira(self, issue):
        backend_issue = self.get_backend_issue(issue.backend_id)
        if not backend_issue:
            issue.delete()
        else:
            logger.debug('Skipping issue deletion with key=%s, '
                         'because it still exists on backend.', issue.backend_id)

    @reraise_exceptions
    def create_comment(self, comment):
        backend_comment = self.manager.add_comment(comment.issue.backend_id, comment.prepare_message())
        comment.backend_id = backend_comment.id
        comment.save(update_fields=['backend_id'])

    def create_comment_from_jira(self, issue, comment_backend_id):
        backend_comment = self.get_backend_comment(issue.backend_id, comment_backend_id)
        if not backend_comment:
            logger.debug('Unable to create comment with id=%s, '
                         'because it has already been deleted on backend.', comment_backend_id)
            return

        try:
            models.Comment.objects.create(
                issue=issue,
                backend_id=comment_backend_id,
                message=models.Comment().clean_message(backend_comment.body),
                state=models.Comment.States.OK,
            )
        except IntegrityError:
            logger.debug('Unable to create comment issue_id=%s, backend_id=%s, '
                         'because it already exists  n Waldur.', issue.id, comment_backend_id)

    def update_comment(self, comment):
        backend_comment = self.get_backend_comment(comment.issue.backend_id, comment.backend_id)
        if not backend_comment:
            logger.debug('Unable to update comment with id=%s, '
                         'because it has already been deleted on backend.', comment.id)
            return

        backend_comment.update(body=comment.prepare_message())

    def update_comment_from_jira(self, comment):
        backend_comment = self.get_backend_comment(comment.issue.backend_id, comment.backend_id)
        if not backend_comment:
            logger.debug('Unable to update comment with id=%s, '
                         'because it has already been deleted on backend.', comment.id)
            return

        comment.message = models.Comment().clean_message(backend_comment.body)
        comment.state = models.Comment.States.OK
        comment.save(update_fields=['message', 'state'])

    @reraise_exceptions
    def delete_comment(self, comment):
        backend_comment = self.get_backend_comment(comment.issue.backend_id, comment.backend_id)
        if backend_comment:
            backend_comment.delete()
        else:
            logger.debug('Unable to delete comment with id=%s, '
                         'because it has already been deleted on backend.', comment.id)

    def delete_comment_from_jira(self, comment):
        backend_comment = self.get_backend_comment(comment.issue.backend_id, comment.backend_id)
        if not backend_comment:
            comment.delete()
        else:
            logger.debug('Skipping comment deletion with id=%s, '
                         'because it still exists on backend.', comment.id)

    @reraise_exceptions
    def add_attachment(self, attachment):
        backend_issue = self.get_backend_issue(attachment.issue.backend_id)
        if not backend_issue:
            logger.debug('Unable to add attachment to issue with id=%s, '
                         'because it has already been deleted on backend.', attachment.issue.id)
            return

        backend_attachment = self.manager.add_attachment(backend_issue, attachment.file)
        attachment.backend_id = backend_attachment.id
        attachment.save(update_fields=['backend_id'])

    @reraise_exceptions
    def remove_attachment(self, attachment):
        backend_attachment = self.get_backend_attachment(attachment.backend_id)
        if backend_attachment:
            backend_attachment.delete()
        else:
            logger.debug('Unable to remove attachment with id=%s, '
                         'because it has already been deleted on backend.', attachment.id)

    @reraise_exceptions
    def import_project_issues(self, project):
        waldur_issues = list(models.Issue.objects.filter(project=project).values_list('id', flat=True))

        for backend_issue in self.manager.search_issues('project=%s' % project.backend_id):
            backend_issue._parse_raw(backend_issue.raw)  # XXX: deal with weird issue in JIRA 1.0.4
            key = backend_issue.key
            if key in waldur_issues:
                logger.debug('Skipping import of issue with key=%s, '
                             'because it already exists in Waldur.', key)
                continue

            issue = models.Issue(project=project, backend_id=key)
            self._backend_issue_to_issue(backend_issue, issue)
            issue.save()

            for backend_comment in self.manager.comments(backend_issue):
                tmp = issue.comments.model()
                tmp.clean_message(backend_comment.body)
                issue.comments.create(
                    user=tmp.user,
                    message=tmp.message,
                    created=parse_datetime(backend_comment.created),
                    backend_id=backend_comment.id,
                    state=issue.comments.model.States.OK)

    def get_backend_comment(self, issue_backend_id, comment_backend_id):
        return self._get_backend_obj('comment')(issue_backend_id, comment_backend_id)

    def get_backend_issue(self, issue_backend_id):
        return self._get_backend_obj('issue')(issue_backend_id)

    def get_backend_attachment(self, attachment_backend_id):
        return self._get_backend_obj('attachment')(attachment_backend_id)

    @reraise_exceptions
    def _get_backend_obj(self, method):
        def f(*args, **kwargs):
            try:
                func = getattr(self.manager, method)
                backend_obj = func(*args, **kwargs)
            except JIRAError as e:
                if e.status_code == status.HTTP_404_NOT_FOUND:
                    logger.debug('Jira object {} has been already deleted on backend'.format(method))
                    return
                else:
                    raise e
            return backend_obj
        return f

    def _backend_issue_to_issue(self, backend_issue, issue):
        priority = self._get_or_create_priority(issue.project, backend_issue.fields.priority)
        issue_type = self._get_or_create_issue_type(issue.project, backend_issue.fields.issuetype)
        resolution_sla = self._get_resolution_sla(backend_issue)

        issue.priority = priority
        issue.summary = backend_issue.fields.summary
        issue.description = backend_issue.fields.description or ''
        issue.type = issue_type
        issue.state = models.Issue.States.OK
        issue.status = backend_issue.fields.status.name or ''
        issue.resolution = (backend_issue.fields.resolution and backend_issue.fields.resolution.name) or ''
        issue.updated_username = backend_issue.fields.creator.name or ''
        issue.resolution_sla = resolution_sla

    def _get_or_create_priority(self, project, backend_priority):
        try:
            priority = models.Priority.objects.get(
                settings=project.service_project_link.service.settings,
                backend_id=backend_priority.id
            )
        except models.Priority.DoesNotExist:
            priority = self.import_priority(backend_priority)
            priority.save()
        return priority

    def _get_or_create_issue_type(self, project, backend_issue_type):
        try:
            issue_type = models.IssueType.objects.get(
                settings=project.service_project_link.service.settings,
                backend_id=backend_issue_type.id
            )
        except models.IssueType.DoesNotExist:
            issue_type = self.import_issue_type(backend_issue_type)
            issue_type.save()
            project.issue_types.add(issue_type)
        return issue_type

    def _get_resolution_sla(self, backend_issue):
        issue_settings = settings.WALDUR_JIRA.get('ISSUE')
        field_name = self.get_field_id_by_name(issue_settings['resolution_sla_field'])
        value = getattr(backend_issue.fields, field_name, None)

        if value and hasattr(value, 'ongoingCycle'):
            milliseconds = value.ongoingCycle.remainingTime.millis
            if milliseconds:
                resolution_sla = milliseconds / 1000
        else:
            resolution_sla = None
        return resolution_sla
