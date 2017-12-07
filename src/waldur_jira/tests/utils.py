import copy

from django.conf import settings
from django.test import override_settings, utils

from .. import views


def override_jira_settings(**kwargs):
    support_settings = copy.deepcopy(settings.WALDUR_JIRA)
    support_settings.update(kwargs)
    return override_settings(WALDUR_JIRA=support_settings)


class _jira_sync(utils.TestContextDecorator):
    def __init__(self, enable):
        self.value = not enable
        self.old = self.view.async_executor
        super(_jira_sync, self).__init__()

    def enable(self):
        self.view.async_executor = self.value

    def disable(self):
        self.view.async_executor = self.old


class jira_sync_issue(_jira_sync):
    def __init__(self, *args, **kwargs):
        self.view = views.IssueViewSet
        super(jira_sync_issue, self).__init__(*args, **kwargs)


class jira_sync_project(_jira_sync):
    def __init__(self, *args, **kwargs):
        self.view = views.ProjectViewSet
        super(jira_sync_project, self).__init__(*args, **kwargs)


