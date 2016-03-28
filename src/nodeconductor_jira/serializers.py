import re

from rest_framework import serializers

from nodeconductor.structure import serializers as structure_serializers

from .backend import JiraBackendError
from . import models


class ServiceSerializer(structure_serializers.BaseServiceSerializer):

    SERVICE_ACCOUNT_FIELDS = {
        'backend_url': '',
        'username': '',
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


class UserSerializer(serializers.Serializer):
    displayName = serializers.CharField()
    emailAddress = serializers.EmailField()


class IssueSerializer(serializers.Serializer):
    url = serializers.HyperlinkedIdentityField(view_name='issue-detail')
    key = serializers.ReadOnlyField()
    summary = serializers.CharField()
    description = serializers.CharField(required=False, style={'base_template': 'textarea.html'})
    assignee = UserSerializer(read_only=True)
    created = serializers.DateTimeField(read_only=True)
    comments = serializers.HyperlinkedIdentityField(view_name='issue-comments-list')
    status = serializers.CharField(source='status.name', read_only=True)
    resolution = serializers.CharField(source='resolution.name', read_only=True)

    def save(self, client, reporter):
        self.client = client
        self.reporter = reporter
        return super(IssueSerializer, self).save()

    def create(self, validated_data):
        return self.client.issues.create(
            validated_data.get('summary'),
            validated_data.get('description'),
            reporter=self.reporter)

    def to_representation(self, obj):
        obj.pk = obj.key
        for field in self.fields:
            if hasattr(obj.fields, field):
                setattr(obj, field, getattr(obj.fields, field))

        return super(IssueSerializer, self).to_representation(obj)


class CommentSerializer(serializers.Serializer):
    author = UserSerializer(read_only=True)
    created = serializers.DateTimeField(read_only=True)
    body = serializers.CharField()

    AUTHOR_RE = re.compile("Comment posted by user ([\w.@+-]+) \(([0-9a-z]{32})\)")
    AUTHOR_TEMPLATE = "Comment posted by user {username} ({uuid})\n{body}"

    def save(self, client, issue):
        self.client = client
        self.issue = issue
        return super(CommentSerializer, self).save()

    def create(self, validated_data):
        return self.client.comments.create(self.issue, self.serialize_body())

    def to_representation(self, obj):
        """
        Try to extract injected author information.
        Use original author otherwise.
        """
        data = super(CommentSerializer, self).to_representation(obj)
        author, body = self.parse_body(data['body'])
        data['author'] = author or data['author']
        data['body'] = body
        return data

    def serialize_body(self):
        """
        Inject author's name and UUID into comment's body
        """
        body = self.validated_data['body']
        user = self.context['request'].user
        return self.AUTHOR_TEMPLATE.format(username=user.username, uuid=user.uuid.hex, body=body)

    def parse_body(self, body):
        """
        Extract author's name and UUID from comment's body
        """
        match = re.match(self.AUTHOR_RE, body)
        if match:
            username = match.group(1)
            uuid = match.group(2)
            body = body[match.end(2) + 2:]
            author = {'displayName': username, 'uuid': uuid}
            return author, body
        else:
            return None, body
