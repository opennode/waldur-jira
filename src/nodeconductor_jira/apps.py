from django.apps import AppConfig


class JiraConfig(AppConfig):
    name = 'nodeconductor_jira'
    verbose_name = 'Jira'

    def ready(self):
        pass
