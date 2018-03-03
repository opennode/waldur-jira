import logging
import re
from datetime import datetime

from django.core import validators as django_validators
from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers

from waldur_core.core import serializers as core_serializers
from waldur_core.structure import serializers as structure_serializers, models as structure_models, SupportedServices

from . import models
from .backend import JiraBackendError

logger = logging.getLogger(__name__)


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


class BaseJiraPropertySerializer(structure_serializers.BasePropertySerializer):

    class Meta(object):
        model = NotImplemented
        fields = ('url', 'uuid', 'name', 'description', 'icon_url')
        extra_kwargs = {
            'url': {'lookup_field': 'uuid'},
        }


class ProjectTemplateSerializer(BaseJiraPropertySerializer):

    class Meta(BaseJiraPropertySerializer.Meta):
        model = models.ProjectTemplate


class IssueTypeSerializer(BaseJiraPropertySerializer):

    class Meta(BaseJiraPropertySerializer.Meta):
        model = models.IssueType
        fields = BaseJiraPropertySerializer.Meta.fields + ('subtask',)


class PrioritySerializer(BaseJiraPropertySerializer):

    class Meta(BaseJiraPropertySerializer.Meta):
        model = models.Priority


class ProjectSerializer(structure_serializers.BaseResourceSerializer):
    key = serializers.CharField(write_only=True, validators=[
        django_validators.RegexValidator(
            regex=re.compile('[A-Z][A-Z0-9]+'),
            message=_('Project keys must start with an uppercase letter, '
                      'followed by one or more uppercase alphanumeric characters.'),
        ),
        django_validators.MaxLengthValidator(
            limit_value=10,
            message=_('The project key must not exceed 10 characters in length.')
        ),
    ])

    service = serializers.HyperlinkedRelatedField(
        source='service_project_link.service',
        view_name='jira-detail',
        read_only=True,
        lookup_field='uuid')

    service_project_link = serializers.HyperlinkedRelatedField(
        view_name='jira-spl-detail',
        queryset=models.JiraServiceProjectLink.objects.all())

    template = serializers.HyperlinkedRelatedField(
        view_name='jira-project-templates-detail',
        queryset=models.ProjectTemplate.objects.all(),
        lookup_field='uuid'
    )

    template_name = serializers.ReadOnlyField(source='template.name')
    template_description = serializers.ReadOnlyField(source='template.description')
    issue_types = IssueTypeSerializer(many=True, read_only=True)
    priorities = PrioritySerializer(many=True, read_only=True)

    class Meta(structure_serializers.BaseResourceSerializer.Meta):
        model = models.Project
        view_name = 'jira-projects-detail'
        protected_fields = structure_serializers.BaseResourceSerializer.Meta.protected_fields + (
            'key', 'template',
        )
        fields = structure_serializers.BaseResourceSerializer.Meta.fields + (
            'key', 'template', 'template_name', 'template_description',
            'issue_types', 'priorities',
        )

    def create(self, validated_data):
        validated_data['backend_id'] = validated_data['key']
        return super(ProjectSerializer, self).create(validated_data)


class ProjectImportSerializer(structure_serializers.BaseResourceImportSerializer):

    class Meta(structure_serializers.BaseResourceImportSerializer.Meta):
        model = models.Project
        view_name = 'jira-projects-detail'
        fields = structure_serializers.BaseResourceImportSerializer.Meta.fields

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


class JiraPropertySerializer(core_serializers.RestrictedSerializerMixin,
                             core_serializers.AugmentedSerializerMixin,
                             serializers.HyperlinkedModelSerializer):
    state = serializers.ReadOnlyField(source='get_state_display')

    class Meta(object):
        model = NotImplemented
        fields = (
            'url', 'uuid', 'user', 'user_uuid', 'user_name', 'user_email', 'state', 'error_message'
        )
        read_only_fields = 'uuid', 'user', 'error_message'
        extra_kwargs = {
            'user': {'lookup_field': 'uuid', 'view_name': 'user-detail'},
        }
        related_paths = {
            'user': ('uuid', 'name', 'email'),
        }

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super(JiraPropertySerializer, self).create(validated_data)


class CommentSerializer(JiraPropertySerializer):

    class Meta(JiraPropertySerializer.Meta):
        model = models.Comment
        fields = JiraPropertySerializer.Meta.fields + (
            'issue', 'issue_uuid', 'issue_key', 'message', 'created',
        )
        protected_fields = 'issue',
        extra_kwargs = dict(
            url={'lookup_field': 'uuid', 'view_name': 'jira-comments-detail'},
            issue={'lookup_field': 'uuid', 'view_name': 'jira-issues-detail'},
            **JiraPropertySerializer.Meta.extra_kwargs
        )
        related_paths = dict(
            issue=('uuid', 'key'),
            **JiraPropertySerializer.Meta.related_paths
        )


class AttachmentSerializer(JiraPropertySerializer):

    class Meta(JiraPropertySerializer.Meta):
        model = models.Attachment
        fields = JiraPropertySerializer.Meta.fields + (
            'issue', 'issue_uuid', 'issue_key', 'file'
        )
        protected_fields = 'issue',
        extra_kwargs = dict(
            url={'lookup_field': 'uuid', 'view_name': 'jira-attachments-detail'},
            issue={'lookup_field': 'uuid', 'view_name': 'jira-issues-detail'},
            **JiraPropertySerializer.Meta.extra_kwargs
        )
        related_paths = dict(
            issue=('uuid', 'key'),
            **JiraPropertySerializer.Meta.related_paths
        )


class IssueSerializer(JiraPropertySerializer):
    priority = serializers.HyperlinkedRelatedField(
        view_name='jira-priorities-detail',
        queryset=models.Priority.objects.all(),
        lookup_field='uuid',
    )
    access_url = serializers.ReadOnlyField(source='get_access_url')
    comments = CommentSerializer(many=True, read_only=True)

    scope = core_serializers.GenericRelatedField(
        source='resource',
        related_models=structure_models.ResourceMixin.get_all_models(),
        required=False
    )
    scope_type = serializers.SerializerMethodField()
    scope_name = serializers.ReadOnlyField(source='resource.name')

    parent = serializers.HyperlinkedRelatedField(
        view_name='jira-issues-detail',
        queryset=models.Issue.objects.all(),
        lookup_field='uuid',
        required=False,
        allow_null=True,
    )

    # For consistency with resource serializer render
    # Waldur project as project and JIRA project as jira_project
    project = serializers.HyperlinkedRelatedField(
        source='project.service_project_link.project',
        view_name='project-detail',
        read_only=True,
        lookup_field='uuid'
    )

    project_name = serializers.ReadOnlyField(source='project.service_project_link.project.name')
    project_uuid = serializers.ReadOnlyField(source='project.service_project_link.project.uuid')

    jira_project = serializers.HyperlinkedRelatedField(
        queryset=models.Project.objects.all(),
        source='project',
        view_name='jira-projects-detail',
        lookup_field='uuid'
    )

    jira_project_name = serializers.ReadOnlyField(source='project.name')
    jira_project_uuid = serializers.ReadOnlyField(source='project.uuid')

    resource_type = serializers.SerializerMethodField()
    service_settings_state = serializers.SerializerMethodField()

    def get_resource_type(self, obj):
        return 'JIRA.Issue'

    def get_service_settings_state(self, obj):
        return 'OK'

    def get_scope_type(self, obj):
        if obj.resource:
            return SupportedServices.get_name_for_model(obj.resource_content_type.model_class())

    class Meta(JiraPropertySerializer.Meta):
        model = models.Issue
        fields = JiraPropertySerializer.Meta.fields + (
            'project', 'project_uuid', 'project_name',
            'jira_project', 'jira_project_uuid', 'jira_project_name',
            'key', 'summary', 'description', 'resolution', 'status',
            'priority', 'priority_name', 'priority_icon_url', 'priority_description',
            'created', 'updated',
            'creator_username', 'creator_name', 'creator_email',
            'assignee_username', 'assignee_name', 'assignee_email',
            'reporter_username', 'reporter_name', 'reporter_email',
            'resolution_date',
            'access_url', 'comments', 'resource_type', 'service_settings_state',
            'type', 'type_name', 'type_description', 'type_icon_url',
            'scope', 'scope_type', 'scope_name',
            'parent', 'parent_uuid', 'parent_summary', 'resolution_sla'
        )
        read_only_fields = 'status', 'resolution', 'updated_username', 'error_message', 'resolution_sla'
        protected_fields = 'jira_project', 'key', 'type', 'scope',
        extra_kwargs = dict(
            url={'lookup_field': 'uuid', 'view_name': 'jira-issues-detail'},
            type={'lookup_field': 'uuid', 'view_name': 'jira-issue-types-detail'},
            parent={'lookup_field': 'uuid', 'view_name': 'jira-issues-detail'},
            **JiraPropertySerializer.Meta.extra_kwargs
        )
        related_paths = dict(
            type=('icon_url', 'name', 'description'),
            parent=('uuid', 'summary'),
            priority=('icon_url', 'name', 'description'),
            **JiraPropertySerializer.Meta.related_paths
        )

    def create(self, validated_data):
        project = validated_data['project']
        issue_type = validated_data['type']
        if issue_type not in project.issue_types.all():
            valid_choices = ', '.join(project.issue_types.values_list('name', flat=True))
            raise serializers.ValidationError({
                'type': _('Invalid issue type. Please select one of following: %s') % valid_choices
            })

        priority = validated_data['priority']
        if priority.settings != project.service_project_link.service.settings:
            raise serializers.ValidationError({
                'parent': _('Priority should belong to the same JIRA provider.')
            })

        parent_issue = validated_data.get('parent')
        if parent_issue:
            if not issue_type.subtask:
                raise serializers.ValidationError({
                    'parent': _('Issue type is not subtask, parent issue is not allowed.')
                })

            if parent_issue.project != project:
                raise serializers.ValidationError({
                    'parent': _('Parent issue should belong to the same JIRA project.')
                })

        return super(IssueSerializer, self).create(validated_data)


#
# Serializers below are used by webhook only
#

class UnixTimeField(serializers.IntegerField):

    def to_representation(self, value):
        try:
            value = datetime.fromtimestamp(value / 1000)
        except ValueError as e:
            raise serializers.ValidationError(e)
        return value


class JiraCommentSerializer(serializers.Serializer):
    id = serializers.CharField()


class JiraFieldSerializer(serializers.Serializer):
    id = serializers.CharField()
    name = serializers.CharField()


class JiraIssueProjectSerializer(JiraFieldSerializer):
    key = serializers.CharField()


class JiraIssueFieldsSerializer(serializers.Serializer):
    project = JiraIssueProjectSerializer()


class JiraIssueSerializer(serializers.Serializer):
    key = serializers.CharField()
    fields = JiraIssueFieldsSerializer()


class WebHookReceiverSerializer(serializers.Serializer):
    class Event:
        ISSUE_CREATE = 1
        ISSUE_UPDATE = 2
        ISSUE_DELETE = 4
        COMMENT_CREATE = 5
        COMMENT_UPDATE = 6
        COMMENT_DELETE = 7

        ISSUE_ACTIONS = (ISSUE_CREATE, ISSUE_UPDATE, ISSUE_DELETE)
        COMMENT_ACTIONS = (COMMENT_CREATE, COMMENT_UPDATE, COMMENT_DELETE)

        CHOICES = {
            ('jira:issue_created', ISSUE_CREATE),
            ('jira:issue_updated', ISSUE_UPDATE),
            ('jira:issue_deleted', ISSUE_DELETE),
            ('comment_created', COMMENT_CREATE),
            ('comment_updated', COMMENT_UPDATE),
            ('comment_deleted', COMMENT_DELETE),
        }

    webhookEvent = serializers.ChoiceField(choices=Event.CHOICES)
    issue = JiraIssueSerializer()
    comment = JiraCommentSerializer(required=False)

    def create(self, validated_data):
        event_type = dict(self.Event.CHOICES).get(validated_data['webhookEvent'])
        fields = validated_data['issue']['fields']
        key = validated_data['issue']['key']
        project_key = fields['project']['key']

        try:
            project = models.Project.objects.get(backend_id=project_key)
        except models.Project.DoesNotExist as e:
            raise serializers.ValidationError('Project with id %s does not exist.' % project_key)

        backend = project.get_backend()
        issue = None

        try:
            issue = models.Issue.objects.get(project=project, backend_id=key)
        except models.Issue.DoesNotExist as e:
            if event_type != self.Event.ISSUE_CREATE:
                raise serializers.ValidationError('Issue with id %s does not exist.' % key)

        if event_type in self.Event.ISSUE_ACTIONS:
            if not issue and event_type == self.Event.ISSUE_CREATE:
                backend.create_issue_from_jira(project, key)

            if event_type == self.Event.ISSUE_UPDATE:
                backend.update_issue_from_jira(issue)

            if event_type == self.Event.ISSUE_DELETE:
                backend.delete_issue_from_jira(issue)

        if event_type in self.Event.COMMENT_ACTIONS:
            comment = None

            try:
                comment_backend_id = validated_data['comment']['id']
                comment = models.Comment.objects.get(issue=issue, backend_id=comment_backend_id)
            except KeyError:
                raise serializers.ValidationError('Request not include fields.comment.id')
            except models.Comment.DoesNotExist as e:
                if event_type != self.Event.COMMENT_CREATE:
                    raise serializers.ValidationError('Comment with id %s does not exist.' % comment_backend_id)

            if not comment and event_type == self.Event.COMMENT_CREATE:
                backend.create_comment_from_jira(issue, comment_backend_id)

            if event_type == self.Event.COMMENT_UPDATE:
                backend.update_comment_from_jira(comment)

            if event_type == self.Event.COMMENT_DELETE:
                backend.delete_comment_from_jira(comment)

        return validated_data
