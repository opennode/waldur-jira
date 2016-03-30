from rest_framework import viewsets, filters, mixins, exceptions

from nodeconductor.core import filters as core_filters
from nodeconductor.structure import views as structure_views

from .backend import JiraBackendError
from .filters import IssueFilter
from . import executors, models, serializers


class JiraServiceViewSet(structure_views.BaseServiceViewSet):
    queryset = models.JiraService.objects.all()
    serializer_class = serializers.ServiceSerializer
    import_serializer_class = serializers.ProjectImportSerializer


class JiraServiceProjectLinkViewSet(structure_views.BaseServiceProjectLinkViewSet):
    queryset = models.JiraServiceProjectLink.objects.all()
    serializer_class = serializers.ServiceProjectLinkSerializer


class ProjectViewSet(structure_views.BaseResourceExecutorViewSet):
    queryset = models.Project.objects.all()
    serializer_class = serializers.ProjectSerializer
    create_executor = executors.ProjectCreateExecutor
    update_executor = executors.ProjectUpdateExecutor
    delete_executor = executors.ProjectDeleteExecutor


class IssueViewSet(structure_views.BaseResourcePropertyExecutorViewSet):
    queryset = models.Issue.objects.all()
    filter_class = IssueFilter
    filter_backends = filters.DjangoFilterBackend, core_filters.StaffOrUserFilter
    serializer_class = serializers.IssueSerializer
    create_executor = executors.IssueCreateExecutor
    update_executor = executors.IssueUpdateExecutor
    delete_executor = executors.IssueDeleteExecutor


class CommentViewSet(structure_views.BaseResourcePropertyExecutorViewSet):
    queryset = models.Comment.objects.all()
    filter_backends = filters.DjangoFilterBackend, core_filters.StaffOrUserFilter
    serializer_class = serializers.CommentSerializer
    create_executor = executors.CommentCreateExecutor
    update_executor = executors.CommentUpdateExecutor
    delete_executor = executors.CommentDeleteExecutor
