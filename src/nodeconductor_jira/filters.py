import django_filters

from .models import Attachment, Comment, Issue, Project


class IssueFilter(django_filters.FilterSet):
    summary = django_filters.CharFilter(lookup_type='icontains')
    description = django_filters.CharFilter(lookup_type='icontains')
    project_key = django_filters.CharFilter(name='project__backend_id')
    user_uuid = django_filters.CharFilter(name='user__uuid')
    key = django_filters.CharFilter(name='backend_id')
    status = django_filters.CharFilter()

    class Meta(object):
        model = Issue
        fields = [
            'key',
            'summary',
            'description',
            'project_key',
            'user_uuid',
            'status',
        ]
        order_by = [
            'created',
            'updated',
            # desc
            '-created',
            '-updated',
        ]


class CommentFilter(django_filters.FilterSet):
    issue_key = django_filters.CharFilter(name='issue__backend_id')
    issue_uuid = django_filters.CharFilter(name='issue__uuid')
    user_uuid = django_filters.CharFilter(name='user__uuid')

    class Meta(object):
        model = Comment
        fields = [
            'issue_key',
            'issue_uuid',
            'user_uuid'
        ]


class AttachmentFilter(django_filters.FilterSet):
    issue_key = django_filters.CharFilter(name='issue__backend_id')

    class Meta(object):
        model = Attachment
        fields = [
            'issue_key',
        ]


class ProjectFilter(django_filters.FilterSet):
    available_for_all = django_filters.BooleanFilter()

    class Meta(object):
        model = Project
        fields = [
            'available_for_all',
        ]
