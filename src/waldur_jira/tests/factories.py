import factory

from django.core.urlresolvers import reverse

from waldur_core.structure.tests import factories as structure_factories

from .. import models
from ..apps import JiraConfig


class JiraServiceFactory(factory.DjangoModelFactory):
    class Meta(object):
        model = models.JiraService

    settings = factory.SubFactory(structure_factories.ServiceSettingsFactory, type=JiraConfig.service_name, backend_url='http://jira/')
    customer = factory.SubFactory(structure_factories.CustomerFactory)

    @classmethod
    def get_url(cls, service=None):
        if service is None:
            service = JiraServiceFactory()
        return 'http://testserver' + reverse('jira-detail', kwargs={'uuid': service.uuid})

    @classmethod
    def get_list_url(cls):
        return 'http://testserver' + reverse('jira-list')


class JiraServiceProjectLinkFactory(factory.DjangoModelFactory):
    class Meta(object):
        model = models.JiraServiceProjectLink

    service = factory.SubFactory(JiraServiceFactory)
    project = factory.SubFactory(structure_factories.ProjectFactory)

    @classmethod
    def get_url(cls, spl=None, action=None):
        if spl is None:
            spl = JiraServiceProjectLinkFactory()
        url = 'http://testserver' + reverse('jira-spl-detail', kwargs={'pk': spl.pk})
        return url if action is None else url + action + '/'

    @classmethod
    def get_list_url(cls):
        return 'http://testserver' + reverse('jira-spl-list')


class ProjectFactory(factory.DjangoModelFactory):
    class Meta(object):
        model = models.Project

    name = factory.Sequence(lambda n: 'instance%s' % n)
    service_project_link = factory.SubFactory(JiraServiceProjectLinkFactory)

    @classmethod
    def get_url(cls, project=None, action=None):
        if project is None:
            project = ProjectFactory()
        url = 'http://testserver' + reverse('jira-projects-detail', kwargs={'uuid': project.uuid})
        return url if action is None else url + action + '/'

    @classmethod
    def get_list_url(cls):
        return 'http://testserver' + reverse('jira-projects-list')


class IssueFactory(factory.DjangoModelFactory):
    class Meta(object):
        model = models.Issue

    backend_id = factory.Sequence(lambda n: 'TST-%s' % n)
    project = factory.SubFactory(ProjectFactory)

    @classmethod
    def get_url(cls, issue=None, action=None):
        if issue is None:
            issue = IssueFactory()
        url = 'http://testserver' + reverse('jira-issues-detail', kwargs={'uuid': issue.uuid})
        return url if action is None else url + action + '/'

    @classmethod
    def get_list_url(cls):
        return 'http://testserver' + reverse('jira-issues-list')