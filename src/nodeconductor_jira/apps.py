from django.apps import AppConfig

from nodeconductor.structure import SupportedServices


class JiraConfig(AppConfig):
    name = 'nodeconductor_jira'
    verbose_name = 'JIRA'
    service_name = 'JIRA'

    def ready(self):
        from .backend import JiraBackend
        SupportedServices.register_backend(JiraBackend)
