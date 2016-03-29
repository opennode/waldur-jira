import django_filters

from .models import Issue


class IssueFilter(django_filters.FilterSet):
    summary = django_filters.CharFilter(lookup_type='icontains')
    description = django_filters.CharFilter(lookup_type='icontains')
    backend_id = django_filters.CharFilter(lookup_type='icontains')
    user_uuid = django_filters.CharFilter(name='user__uuid')

    class Meta(object):
        model = Issue
        fields = [
            'summary',
            'description',
            'backend_id',
            'user_uuid'
        ]
