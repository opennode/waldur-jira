from django.utils.functional import cached_property

from waldur_core.structure.tests import factories as structure_factories
from waldur_core.structure.tests import fixtures as structure_fixtures

from .. import models
from ..apps import JiraConfig
from . import factories


class JiraFixture(structure_fixtures.ProjectFixture):
    @cached_property
    def service_settings(self):
        return structure_factories.ServiceSettingsFactory(
            type=JiraConfig.service_name,
            backend_url='http://jira/',
            customer=self.customer
        )

    @cached_property
    def service(self):
        return factories.JiraServiceFactory(settings=self.service_settings, customer=self.customer)

    @cached_property
    def service_project_link(self):
        return factories.JiraServiceProjectLinkFactory(service=self.service, project=self.project)

    @cached_property
    def jira_project(self):
        return factories.ProjectFactory(service_project_link=self.service_project_link)

    @cached_property
    def jira_project_url(self):
        return factories.ProjectFactory.get_url(self.jira_project)
