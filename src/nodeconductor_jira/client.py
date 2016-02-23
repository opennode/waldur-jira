from django.conf import settings

from nodeconductor.structure.models import ServiceSettings
from .backend import JiraBackend, JiraBackendError


class SupportClient(object):
    """ NodeConductor support client via JIRA backend """

    ISSUE_TYPE = 'Support Request'
    REPORTER_FIELD = 'Original Reporter'

    def __new__(cls):
        try:
            project = settings.NODECONDUCTOR_JIRA['project']
            jira_settings = ServiceSettings(
                backend_url=settings.NODECONDUCTOR_JIRA['server'],
                username=settings.NODECONDUCTOR_JIRA['username'],
                password=settings.NODECONDUCTOR_JIRA['password'])
        except (KeyError, AttributeError):
            raise JiraBackendError("Missed JIRA_SUPPORT settings or improperly configured")

        return JiraBackend(
            jira_settings,
            core_project=project,
            reporter_field=cls.REPORTER_FIELD,
            default_issue_type=cls.ISSUE_TYPE)
