from datetime import datetime
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
        view_name = 'jira-project-detail'

    def create(self, validated_data):
        backend = self.context['service'].get_backend()
        try:
            project = backend.projects.get(validated_data['backend_id'])
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

    access_url = serializers.ReadOnlyField(source='get_access_url')

    class Meta(JiraPropertySerializer.Meta):
        model = models.Issue
        view_name = 'jira-issues-detail'
        fields = JiraPropertySerializer.Meta.fields + (
            'project', 'project_uuid', 'project_name',
            'summary', 'description', 'access_url',
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


class UnixTimeField(serializers.IntegerField):

    def to_representation(self, value):
        try:
            value = datetime.fromtimestamp(value / 1000)
        except ValueError as e:
            raise serializers.ValidationError(e)
        return value


class JiraCommentSerializer(serializers.Serializer):
    id = serializers.CharField()
    body = serializers.CharField()
    created = serializers.DateTimeField()
    updated = serializers.DateTimeField()


class JiraIssueCommentSerializer(serializers.Serializer):
    total = serializers.IntegerField()
    comments = JiraCommentSerializer(many=True)


class JiraIssueStatusSerializer(serializers.Serializer):
    id = serializers.CharField()
    name = serializers.CharField()


class JiraIssueProjectSerializer(serializers.Serializer):
    id = serializers.CharField()
    key = serializers.CharField()
    name = serializers.CharField()


class JiraIssueFieldsSerializer(serializers.Serializer):
    summary = serializers.CharField()
    description = serializers.CharField(allow_null=True)
    resolution = serializers.CharField(allow_null=True)
    status = JiraIssueStatusSerializer()
    project = JiraIssueProjectSerializer()
    created = serializers.DateTimeField()
    updated = serializers.DateTimeField()
    comment = JiraIssueCommentSerializer()


class JiraIssueSerializer(serializers.Serializer):
    key = serializers.CharField()
    fields = JiraIssueFieldsSerializer()


class JiraChangeSerializer(serializers.Serializer):
    field = serializers.CharField()
    fromString = serializers.CharField()
    toString = serializers.CharField()


class JiraChangelogSerializer(serializers.Serializer):
    items = JiraChangeSerializer(many=True)


class WebHookSerializer(serializers.Serializer):

    class Event:
        CREATE = 1
        UPDATE = 2
        DELETE = 4

        CHOICES = {
            ('jira:issue_created', CREATE),
            ('jira:issue_updated', UPDATE),
            ('jira:issue_deleted', DELETE),
        }

    webhookEvent = serializers.ChoiceField(choices=Event.CHOICES)
    timestamp = UnixTimeField()
    changelog = JiraChangelogSerializer(required=False)
    comment = JiraCommentSerializer(required=False)
    issue = JiraIssueSerializer()

    def create(self, validated_data):
        event_type = dict(self.Event.CHOICES).get(validated_data['webhookEvent'])

        try:
            request = self.context['request']
            issue_key = request.query_params.get('issue') or validated_data['issue']['key']
            issue = models.Issue.objects.get(backend_id=issue_key)
        except models.Issue.DoesNotExist as e:
            if event_type == self.Event.CREATE:
                fields = validated_data['issue']['fields']
                try:
                    project = models.Project.objects.get(backend_id=fields['project']['key'])
                except models.Project.DoesNotExist as e:
                    raise serializers.ValidationError(e)
                else:
                    project.issues.create(
                        status=fields['status'],
                        summary=fields['summary'],
                        description=fields['description'] or '',
                        resolution=fields['resolution'] or '',
                        backend_id=validated_data['issue']['key'],
                        state=models.Issue.States.OK)

            else:
                raise serializers.ValidationError({'issue': e})

        else:
            if event_type == self.Event.UPDATE:
                # comment update
                if 'comment' in validated_data:
                    issue.comments.update_or_create(
                        backend_id=validated_data['comment']['id'],
                        defaults={'message': validated_data['comment']['body']})

                # issue update
                else:
                    fields = ('summary', 'status', 'description', 'resolution')
                    for field in fields:
                        setattr(issue, field, validated_data['issue']['fields'][field] or '')

                    issue.save(update_fields=fields)

                    total_comments = validated_data['issue']['comment']['total']
                    if total_comments < issue.comments.count():
                        ids = [c['id'] for c in validated_data['issue']['comment']['comments']]
                        issue.comments.exclude(backend_id__in=ids).delete()

            if event_type == self.Event.DELETE:
                issue.delete()

        return validated_data
