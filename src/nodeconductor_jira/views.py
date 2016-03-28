from rest_framework import viewsets, mixins, exceptions

from nodeconductor.structure import views as structure_views

from .backend import JiraBackendError
from .filters import IssueSearchFilter
from . import models, serializers


class JiraServiceViewSet(structure_views.BaseServiceViewSet):
    queryset = models.JiraService.objects.all()
    serializer_class = serializers.ServiceSerializer
    import_serializer_class = serializers.ProjectImportSerializer


class JiraServiceProjectLinkViewSet(structure_views.BaseServiceProjectLinkViewSet):
    queryset = models.JiraServiceProjectLink.objects.all()
    serializer_class = serializers.ServiceProjectLinkSerializer


class ProjectViewSet(structure_views.BaseOnlineResourceViewSet):
    queryset = models.Project.objects.all()
    serializer_class = serializers.ProjectSerializer
    # XXX: Ignore errors with new resource models (NC-1237)
    filter_class = None

    def perform_provision(self, serializer):
        resource = serializer.save()
        backend = resource.get_backend()
        backend.provision(resource)


class SupportMixin(object):

    def initial(self, request, *args, **kwargs):
        super(SupportMixin, self).initial(request, *args, **kwargs)
        self.user_uuid = request.user.uuid.hex
        self.client = SupportClient()


class IssueViewSet(SupportMixin, mixins.RetrieveModelMixin, mixins.ListModelMixin,
                   mixins.CreateModelMixin, viewsets.GenericViewSet):
    serializer_class = serializers.IssueSerializer
    filter_backends = (IssueSearchFilter,)

    def get_queryset(self):
        return self.client.issues.list_by_user(self.user_uuid)

    def get_object(self):
        try:
            return self.client.issues.get_by_user(self.user_uuid, self.kwargs['pk'])
        except JiraBackendError as e:
            raise exceptions.NotFound(e)

    def perform_create(self, serializer):
        try:
            serializer.save(client=self.client, reporter=self.user_uuid)
        except JiraBackendError as e:
            raise exceptions.ValidationError(e)


class CommentViewSet(SupportMixin, mixins.ListModelMixin,
                     mixins.CreateModelMixin, viewsets.GenericViewSet):

    serializer_class = serializers.CommentSerializer

    def get_queryset(self):
        try:
            return self.client.comments.list(self.kwargs['pk'])
        except JiraBackendError as e:
            raise exceptions.NotFound(e)

    def perform_create(self, serializer):
        try:
            serializer.save(client=self.client, issue=self.kwargs['pk'])
        except JiraBackendError as e:
            raise exceptions.ValidationError(e)
