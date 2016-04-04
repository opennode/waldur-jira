from django.apps import AppConfig
from django.db.models import signals

from nodeconductor.structure import SupportedServices


class JiraConfig(AppConfig):
    name = 'nodeconductor_jira'
    verbose_name = 'JIRA'
    service_name = 'JIRA'

    def ready(self):
        from . import handlers
        from .backend import JiraBackend
        SupportedServices.register_backend(JiraBackend)

        Issue = self.get_model('Issue')
        Comment = self.get_model('Comment')

        signals.post_save.connect(
            handlers.log_issue_save,
            sender=Issue,
            dispatch_uid='nodeconductor_jira.handlers.log_issue_save',
        )

        signals.post_delete.connect(
            handlers.log_issue_delete,
            sender=Issue,
            dispatch_uid='nodeconductor_jira.handlers.log_issue_delete',
        )

        signals.post_save.connect(
            handlers.log_comment_save,
            sender=Comment,
            dispatch_uid='nodeconductor_jira.handlers.log_comment_save',
        )

        signals.post_delete.connect(
            handlers.log_comment_delete,
            sender=Comment,
            dispatch_uid='nodeconductor_jira.handlers.log_comment_delete',
        )
