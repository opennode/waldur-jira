from ddt import ddt, data
from rest_framework import test, status

from nodeconductor_jira.models import Issue
from nodeconductor_jira.tests import factories
from nodeconductor.structure.models import CustomerRole, ProjectRole, ProjectGroupRole
from nodeconductor.structure.tests import factories as structure_factories


@ddt
class ProjectPermissionTest(test.APITransactionTestCase):

    def setUp(self):
        self.users = {
            'owner': structure_factories.UserFactory(),
            'admin': structure_factories.UserFactory(),
            'manager': structure_factories.UserFactory(),
            'group_manager': structure_factories.UserFactory(),
            'no_role': structure_factories.UserFactory(),
        }

        # a single customer
        self.customer = structure_factories.CustomerFactory()
        self.customer.add_user(self.users['owner'], CustomerRole.OWNER)

        # that has 3 users connected: admin, manager, group_manager
        self.project = structure_factories.ProjectFactory(customer=self.customer)
        self.project.add_user(self.users['admin'], ProjectRole.ADMINISTRATOR)
        self.project.add_user(self.users['manager'], ProjectRole.MANAGER)
        project_group = structure_factories.ProjectGroupFactory()
        project_group.projects.add(self.project)
        project_group.add_user(self.users['group_manager'], ProjectGroupRole.MANAGER)

        service = factories.JiraServiceFactory(customer=self.customer)
        self.spl = factories.JiraServiceProjectLinkFactory(service=service, project=self.project)
        self.project = factories.ProjectFactory(service_project_link=self.spl)
        self.global_project = factories.ProjectFactory(service_project_link=self.spl, available_for_all=True)

    @data('owner', 'admin', 'manager', 'group_manager')
    def test_user_with_access_can_access_project(self, user):
        self.client.force_authenticate(self.users[user])
        response = self.client.get(factories.ProjectFactory.get_url(self.project))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_user_without_access_cannot_access_project(self):
        self.client.force_authenticate(self.users['no_role'])
        response = self.client.get(factories.ProjectFactory.get_url(self.project))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    @data('owner', 'admin', 'manager', 'group_manager', 'no_role')
    def test_any_user_can_access_global_project(self, user):
        self.client.force_authenticate(self.users[user])
        response = self.client.get(factories.ProjectFactory.get_url(self.global_project))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @data('manager', 'group_manager', 'no_role')
    def test_any_user_cannot_delete_global_project(self, user):
        self.client.force_authenticate(self.users[user])
        response = self.client.delete(factories.ProjectFactory.get_url(self.global_project))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @data('owner', 'admin', 'manager', 'group_manager', 'no_role')
    def test_any_user_can_create_issue_in_global_project(self, user):
        self.client.force_authenticate(self.users[user])
        response = self.client.post(
            factories.IssueFactory.get_list_url(),
            self._get_issue_payload(self.global_project))
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_issue_permissions_in_global_project(self):
        self.client.force_authenticate(self.users['manager'])

        response = self.client.post(
            factories.IssueFactory.get_list_url(),
            self._get_issue_payload(self.global_project))
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        issue_url = response.data['url']
        issue = Issue.objects.get(uuid=response.data['uuid'])
        issue.state = Issue.States.OK
        issue.save()

        self.client.force_authenticate(self.users['manager'])
        response = self.client.patch(issue_url, {'description': 'do it'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.client.force_authenticate(self.users['no_role'])
        response = self.client.get(issue_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.client.force_authenticate(self.users['no_role'])
        response = self.client.delete(issue_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        issue.state = Issue.States.OK
        issue.save()

        self.client.force_authenticate(self.users['owner'])
        response = self.client.delete(issue_url)
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)

    def _get_issue_payload(self, project):
        return {
            'project': factories.ProjectFactory.get_url(project),
            'summary': 'Summary',
            'description': '',
            'priority': 'Minor',
            'impact': 'Small - Partial loss of service, one person affected',
        }
