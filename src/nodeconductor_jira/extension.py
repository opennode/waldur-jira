from __future__ import unicode_literals

from nodeconductor.core import NodeConductorExtension


class JiraExtension(NodeConductorExtension):

    class Settings:
        # Jira admin account credentials
        NODECONDUCTOR_JIRA = {
         'username': 'admin',
         'password': 'secret',
         'project': 'PRJ',
         'server': 'https://jira.example.com/',
        }

    @staticmethod
    def django_app():
        return 'nodeconductor_jira'

    @staticmethod
    def rest_urls():
        from .urls import register_in
        return register_in

