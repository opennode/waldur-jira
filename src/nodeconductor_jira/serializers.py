import re

from rest_framework import serializers

from nodeconductor.core.serializers import AugmentedSerializerMixin
from nodeconductor.structure import serializers as structure_serializers

from .backend import JiraBackendError
from . import models


class ServiceSerializer(structure_serializers.BaseServiceSerializer):

    SERVICE_ACCOUNT_FIELDS = {
        'backend_url': 'JIRA host (e.g. https://jira.example.com/)',
        'username': 'JIRA user with excessive privileges',
        'password': '',
    }

    class Meta(structure_serializers.BaseServiceSerializer.Meta):
        model = models.JiraService
        view_name = 'jira-detail'


class ServiceProjectLinkSerializer(structure_serializers.BaseServiceProjectLinkSerializer):
    class Meta(structure_serializers.BaseServiceProjectLinkSerializer.Meta):
        model = models.JiraServiceProjectLink
        view_name = 'jira-spl-detail'
        extra_kwargs = {
            'service': {'lookup_field': 'uuid', 'view_name': 'jira-detail'},
        }


class ProjectSerializer(structure_serializers.BaseResourceSerializer):

    key = serializers.CharField(write_only=True)

    service = serializers.HyperlinkedRelatedField(
        source='service_project_link.service',
        view_name='jira-detail',
        read_only=True,
        lookup_field='uuid')

    service_project_link = serializers.HyperlinkedRelatedField(
        view_name='jira-spl-detail',
        queryset=models.JiraServiceProjectLink.objects.all())

    class Meta(structure_serializers.BaseResourceSerializer.Meta):
        model = models.Project
        view_name = 'jira-projects-detail'
        fields = structure_serializers.BaseResourceSerializer.Meta.fields + (
            'key', 'reporter_field', 'default_issue_type',
        )

    def create(self, validated_data):
        validated_data['backend_id'] = validated_data['key']
        return super(ProjectSerializer, self).create(validated_data)


class ProjectImportSerializer(structure_serializers.BaseResourceImportSerializer):

    class Meta(structure_serializers.BaseResourceImportSerializer.Meta):
        model = models.Project
        view_name = 'jira-projects-detail'

    def create(self, validated_data):
        backend = self.context['service'].get_backend()
        try:
            project = backend.get_project(validated_data['backend_id'])
        except JiraBackendError:
            raise serializers.ValidationError(
                {'backend_id': "Can't find project with ID %s" % validated_data['backend_id']})

        validated_data['name'] = project.name
        validated_data['state'] = models.Project.States.OK
        return super(ProjectImportSerializer, self).create(validated_data)


class JiraPropertySerializer(AugmentedSerializerMixin, serializers.HyperlinkedModelSerializer):
    state = serializers.ReadOnlyField(source='get_state_display')

    class Meta(object):
        model = NotImplemented
        view_name = NotImplemented
        fields = (
            'url', 'uuid', 'user', 'user_uuid', 'backend_id', 'state'
        )
        read_only_fields = 'uuid', 'user', 'backend_id'
        extra_kwargs = {
            'url': {'lookup_field': 'uuid'},
            'user': {'lookup_field': 'uuid', 'view_name': 'user-detail'},
        }
        related_paths = {
            'user': ('uuid',),
        }

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super(JiraPropertySerializer, self).create(validated_data)


class IssueSerializer(JiraPropertySerializer):

    class Meta(JiraPropertySerializer.Meta):
        model = models.Issue
        view_name = 'jira-issues-detail'
        fields = JiraPropertySerializer.Meta.fields + (
            'project', 'project_uuid', 'project_name',
            'summary', 'description',
        )
        protected_fields = 'project',
        extra_kwargs = dict(
            project={'lookup_field': 'uuid', 'view_name': 'jira-projects-detail'},
            **JiraPropertySerializer.Meta.extra_kwargs
        )
        related_paths = dict(
            project=('uuid', 'name'),
            **JiraPropertySerializer.Meta.related_paths
        )


class CommentSerializer(JiraPropertySerializer):

    class Meta(JiraPropertySerializer.Meta):
        model = models.Comment
        view_name = 'jira-comments-detail'
        fields = JiraPropertySerializer.Meta.fields + (
            'issue', 'issue_uuid', 'issue_backend_id', 'message'
        )
        protected_fields = 'issue',
        extra_kwargs = dict(
            issue={'lookup_field': 'uuid', 'view_name': 'jira-issues-detail'},
            **JiraPropertySerializer.Meta.extra_kwargs
        )
        related_paths = dict(
            issue=('uuid', 'backend_id'),
            **JiraPropertySerializer.Meta.related_paths
        )
