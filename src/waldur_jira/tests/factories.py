import factory

from django.core.urlresolvers import reverse

from waldur_core.structure.tests import factories as structure_factories

from .. import models
from ..apps import JiraConfig


class JiraServiceSettingsFactory(structure_factories.ServiceSettingsFactory):
    type = JiraConfig.service_name
    backend_url = 'http://jira/'


class JiraServiceFactory(factory.DjangoModelFactory):
    class Meta(object):
        model = models.JiraService

    settings = factory.SubFactory(JiraServiceSettingsFactory)
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


class ProjectTemplateFactory(factory.DjangoModelFactory):
    class Meta(object):
        model = models.ProjectTemplate

    name = factory.Sequence(lambda n: 'template-%s' % n)
    backend_id = factory.Sequence(lambda n: 'template-%s' % n)

    @classmethod
    def get_url(cls, project=None, action=None):
        if project is None:
            project = ProjectTemplateFactory()
        url = 'http://testserver' + reverse('jira-project-templates-detail', kwargs={'uuid': project.uuid})
        return url if action is None else url + action + '/'

    @classmethod
    def get_list_url(cls):
        return 'http://testserver' + reverse('jira-project-templates-list')


class ProjectFactory(factory.DjangoModelFactory):
    class Meta(object):
        model = models.Project

    backend_id=factory.Sequence(lambda n: 'PRJ-%s' % n)
    name = factory.Sequence(lambda n: 'JIRA project %s' % n)
    service_project_link = factory.SubFactory(JiraServiceProjectLinkFactory)
    template = factory.SubFactory(ProjectTemplateFactory)
    state = models.Project.States.OK

    @classmethod
    def get_url(cls, project=None, action=None):
        if project is None:
            project = ProjectFactory()
        url = 'http://testserver' + reverse('jira-projects-detail', kwargs={'uuid': project.uuid})
        return url if action is None else url + action + '/'

    @classmethod
    def get_list_url(cls):
        return 'http://testserver' + reverse('jira-projects-list')


class IssueTypeFactory(factory.DjangoModelFactory):
    class Meta(object):
        model = models.IssueType

    settings = factory.SubFactory(JiraServiceSettingsFactory)
    name = factory.Sequence(lambda n: 'issue-type-%s' % n)
    backend_id = factory.Sequence(lambda n: 'issue-type-%s' % n)
    icon_url = factory.Sequence(lambda n: 'http://icon.com/icon_url-%s' % n)

    @classmethod
    def get_url(cls, issue=None, action=None):
        if issue is None:
            issue = IssueTypeFactory()
        url = 'http://testserver' + reverse('jira-issue-types-detail', kwargs={'uuid': issue.uuid})
        return url if action is None else url + action + '/'

    @classmethod
    def get_list_url(cls):
        return 'http://testserver' + reverse('jira-issue-types-list')


class PriorityFactory(factory.DjangoModelFactory):
    class Meta(object):
        model = models.Priority

    settings = factory.SubFactory(JiraServiceSettingsFactory)
    name = factory.Sequence(lambda n: 'priority-%s' % n)
    backend_id = factory.Sequence(lambda n: 'priority-%s' % n)
    icon_url = factory.Sequence(lambda n: 'http://icon.com/icon_url-%s' % n)

    @classmethod
    def get_url(cls, issue=None, action=None):
        if issue is None:
            issue = PriorityFactory()
        url = 'http://testserver' + reverse('jira-priorities-detail', kwargs={'uuid': issue.uuid})
        return url if action is None else url + action + '/'

    @classmethod
    def get_list_url(cls):
        return 'http://testserver' + reverse('jira-priorities-list')


class IssueFactory(factory.DjangoModelFactory):
    class Meta(object):
        model = models.Issue

    type = factory.SubFactory(IssueTypeFactory)
    priority = factory.SubFactory(PriorityFactory)
    backend_id = factory.Sequence(lambda n: 'TST-%s' % n)
    status = factory.Sequence(lambda n: 'STATUS-%s' % n)
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


class CommentFactory(factory.DjangoModelFactory):
    class Meta(object):
        model = models.Comment

    issue = factory.SubFactory(IssueFactory)
    backend_id = factory.Sequence(lambda n: 'TST-%s' % n)

    @classmethod
    def get_url(cls, comment=None, action=None):
        if comment is None:
            comment = CommentFactory()
        url = 'http://testserver' + reverse('jira-comments-detail', kwargs={'uuid': comment.uuid})
        return url if action is None else url + action + '/'

    @classmethod
    def get_list_url(cls):
        return 'http://testserver' + reverse('jira-comments-list')
