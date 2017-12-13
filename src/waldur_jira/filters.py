import django_filters

from waldur_core.structure import filters as structure_filters

from . import models


class ProjectTemplateFilter(structure_filters.BaseServicePropertyFilter):
    class Meta(structure_filters.BaseServicePropertyFilter.Meta):
        model = models.ProjectTemplate


class ProjectFilter(structure_filters.BaseResourceFilter):
    class Meta(structure_filters.BaseResourceFilter.Meta):
        model = models.Project


class IssueFilter(django_filters.FilterSet):
    summary = django_filters.CharFilter(lookup_expr='icontains')
    description = django_filters.CharFilter(lookup_expr='icontains')
    project_key = django_filters.CharFilter(name='project__backend_id')
    user_uuid = django_filters.UUIDFilter(name='user__uuid')
    key = django_filters.CharFilter(name='backend_id')
    status = django_filters.CharFilter()

    class Meta(object):
        model = models.Issue
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
    issue_uuid = django_filters.UUIDFilter(name='issue__uuid')
    user_uuid = django_filters.UUIDFilter(name='user__uuid')

    class Meta(object):
        model = models.Comment
        fields = [
            'issue_key',
            'issue_uuid',
            'user_uuid'
        ]


class AttachmentFilter(django_filters.FilterSet):
    issue_key = django_filters.CharFilter(name='issue__backend_id')

    class Meta(object):
        model = models.Attachment
        fields = [
            'issue_key',
        ]
