from django.apps import AppConfig


class JiraConfig(AppConfig):
    name = 'nodeconductor_jira'
    verbose_name = 'JIRA'

    def ready(self):
        pass
