from __future__ import unicode_literals

from rest_framework import viewsets, mixins, exceptions

from .client import SupportClient, JiraBackendError
from .filters import IssueSearchFilter
from .serializers import IssueSerializer, CommentSerializer


class SupportMixin(object):

    def initial(self, request, *args, **kwargs):
        super(SupportMixin, self).initial(request, *args, **kwargs)
        self.user_uuid = request.user.uuid.hex
        self.client = SupportClient()


class IssueViewSet(SupportMixin, mixins.RetrieveModelMixin, mixins.ListModelMixin,
                   mixins.CreateModelMixin, viewsets.GenericViewSet):
    serializer_class = IssueSerializer
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

    serializer_class = CommentSerializer

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