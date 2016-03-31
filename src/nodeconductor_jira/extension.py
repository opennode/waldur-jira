from __future__ import unicode_literals

from nodeconductor.core import NodeConductorExtension


class JiraExtension(NodeConductorExtension):

    @staticmethod
    def django_app():
        return 'nodeconductor_jira'

    @staticmethod
    def django_urls():
        from .urls import urlpatterns
        return urlpatterns

    @staticmethod
    def rest_urls():
        from .urls import register_in
        return register_in
