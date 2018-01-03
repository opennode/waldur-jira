import re

from datetime import datetime
from django.conf import settings
from django.core import validators as django_validators
from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers

from waldur_core.core import serializers as core_serializers
from waldur_core.structure import serializers as structure_serializers, models as structure_models, SupportedServices

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
            'created', 'updated', 'updated_username',
            'access_url', 'comments', 'resource_type', 'service_settings_state',
            'type', 'type_name', 'type_description', 'type_icon_url',
            'scope', 'scope_type', 'scope_name',
            'parent', 'parent_uuid', 'parent_summary',
        )
        read_only_fields = 'status', 'resolution', 'updated_username', 'error_message'
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
    body = serializers.CharField()
    created = serializers.DateTimeField()
    updated = serializers.DateTimeField()


class JiraFieldSerializer(serializers.Serializer):
    id = serializers.CharField()
    name = serializers.CharField()


class JiraIssueCommentSerializer(serializers.Serializer):
    total = serializers.IntegerField()
    comments = JiraCommentSerializer(many=True)


class JiraIssueProjectSerializer(JiraFieldSerializer):
    key = serializers.CharField()


class JiraIssueFieldsSerializer(serializers.Serializer):
    summary = serializers.CharField()
    description = serializers.CharField(allow_null=True)
    resolution = serializers.CharField(allow_null=True)
    issuetype = JiraFieldSerializer()
    priority = JiraFieldSerializer()
    status = JiraFieldSerializer()
    project = JiraIssueProjectSerializer()
    created = serializers.DateTimeField()
    updated = serializers.DateTimeField()
    comment = JiraIssueCommentSerializer()


class JiraIssueSerializer(serializers.Serializer):
    key = serializers.CharField()
    fields = JiraIssueFieldsSerializer()


class JiraChangeSerializer(serializers.Serializer):
    field = serializers.CharField()
    fromString = serializers.CharField(allow_null=True)
    toString = serializers.CharField(allow_null=True)


class JiraChangelogSerializer(serializers.Serializer):
    items = JiraChangeSerializer(many=True)


class JiraUserSerializer(serializers.Serializer):
    key = serializers.CharField()
    displayName = serializers.CharField()
    emailAddress = serializers.EmailField()


class WebHookReceiverSerializer(serializers.Serializer):

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
    user = JiraUserSerializer()

    def create(self, validated_data):
        fields = validated_data['issue']['fields']
        event_type = dict(self.Event.CHOICES).get(validated_data['webhookEvent'])

        try:
            project = models.Project.objects.get(backend_id=fields['project']['key'])
        except models.Project.DoesNotExist as e:
            raise serializers.ValidationError(e)

        backend = project.get_backend()

        try:
            priority = models.Priority.objects.get(
                settings=project.settings,
                backend_id=fields.priority.id
            )
        except models.Priority.DoesNotExist:
            priority = self.import_priority(fields['priority'])
            priority.save()

        try:
            issue_type = models.IssueType.objects.get(
                settings=project.settings,
                backend_id=fields['issuetype']['id']
            )
        except models.IssueType.DoesNotExist:
            issue_type = backend.import_issue_type(fields['issuetype'])
            issue_type.save()
            project.issue_types.add(issue_type)

        try:
            issue = models.Issue.objects.get(backend_id=validated_data['issue']['key'])
        except models.Issue.DoesNotExist as e:
            if event_type == self.Event.CREATE:
                project.issues.create(
                    type=issue_type,
                    status=fields['status']['name'],
                    summary=fields['summary'],
                    priority=priority,
                    description=fields['description'] or '',
                    resolution=fields['resolution'] or '',
                    updated_username=validated_data['user']['displayName'],
                    backend_id=validated_data['issue']['key'],
                    state=models.Issue.States.OK)

            else:
                raise serializers.ValidationError({'issue': e})

        else:
            if event_type == self.Event.UPDATE:
                # comment update
                if 'comment' in validated_data:
                    message = models.Comment().clean_message(validated_data['comment']['body'])
                    issue.comments.update_or_create(
                        backend_id=validated_data['comment']['id'],
                        defaults={
                            'message': message,
                            'state': models.Comment.States.OK,
                        })

                # issue update
                else:
                    issue.priority = priority
                    issue.summary = fields['summary']
                    issue.description = fields['description'] or ''
                    issue.resolution = fields['resolution'] or ''
                    issue.status = fields['status']['name']
                    issue.type = issue_type
                    issue.updated_username = validated_data['user']['displayName']
                    issue.save()

                    # XXX: there's no JIRA comment deletion callback in JIRA 6.4
                    #      hence remove stale comments on general issue update
                    total_comments = fields['comment']['total']
                    if total_comments < issue.comments.count():
                        ids = [c['id'] for c in fields['comment']['comments']]
                        issue.comments.exclude(backend_id__in=ids).delete()

            if event_type == self.Event.DELETE:
                issue.delete()

        return validated_data
