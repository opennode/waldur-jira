import logging

from rest_framework import filters, generics, permissions, viewsets

from nodeconductor.core import mixins as core_mixins
from nodeconductor.structure import views as structure_views
from nodeconductor.structure import filters as structure_filters

from .filters import AttachmentFilter, IssueFilter, CommentFilter, ProjectFilter
from . import executors, models, serializers

logger = logging.getLogger(__name__)


class JiraServiceViewSet(structure_views.BaseServiceViewSet):
    queryset = models.JiraService.objects.all()
    serializer_class = serializers.ServiceSerializer
    import_serializer_class = serializers.ProjectImportSerializer


class JiraServiceProjectLinkViewSet(structure_views.BaseServiceProjectLinkViewSet):
    queryset = models.JiraServiceProjectLink.objects.all()
    serializer_class = serializers.ServiceProjectLinkSerializer


class JiraPermissionMixin(object):
    def get_queryset(self):
        user = self.request.user
        queryset = super(JiraPermissionMixin, self).get_queryset()
        if user.is_staff:
            return queryset
        else:
            return queryset.filter(user=user)


class ProjectViewSet(structure_views.BaseResourceExecutorViewSet):
    queryset = models.Project.objects.all()
    filter_class = ProjectFilter
    serializer_class = serializers.ProjectSerializer
    create_executor = executors.ProjectCreateExecutor
    update_executor = executors.ProjectUpdateExecutor
    delete_executor = executors.ProjectDeleteExecutor
    async_executor = False


class IssueViewSet(JiraPermissionMixin,
                   structure_views.BaseResourcePropertyExecutorViewSet):
    queryset = models.Issue.objects.all()
    filter_class = IssueFilter
    serializer_class = serializers.IssueSerializer
    create_executor = executors.IssueCreateExecutor
    update_executor = executors.IssueUpdateExecutor
    delete_executor = executors.IssueDeleteExecutor
    async_executor = False


class CommentViewSet(JiraPermissionMixin,
                     structure_views.BaseResourcePropertyExecutorViewSet):
    queryset = models.Comment.objects.all()
    filter_class = CommentFilter
    serializer_class = serializers.CommentSerializer
    create_executor = executors.CommentCreateExecutor
    update_executor = executors.CommentUpdateExecutor
    delete_executor = executors.CommentDeleteExecutor
    async_executor = False


class AttachmentViewSet(JiraPermissionMixin,
                        core_mixins.CreateExecutorMixin,
                        core_mixins.DeleteExecutorMixin,
                        viewsets.ModelViewSet):
    queryset = models.Attachment.objects.all()
    filter_class = AttachmentFilter
    filter_backends = structure_filters.GenericRoleFilter, filters.DjangoFilterBackend
    permission_classes = permissions.IsAuthenticated, permissions.DjangoObjectPermissions
    serializer_class = serializers.AttachmentSerializer
    create_executor = executors.AttachmentCreateExecutor
    delete_executor = executors.AttachmentDeleteExecutor
    async_executor = False
    lookup_field = 'uuid'


class WebHookReceiverViewSet(generics.CreateAPIView):
    authentication_classes = ()
    permission_classes = ()
    serializer_class = serializers.WebHookReceiverSerializer

    def create(self, request, *args, **kwargs):
        try:
            return super(WebHookReceiverViewSet, self).create(request, *args, **kwargs)
        except Exception as e:
            # Throw validation errors to the logs
            logger.error("Can't parse JIRA WebHook request: %s" % e)
            raise
