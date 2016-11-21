from ddt import ddt, data
from rest_framework import test, status

from nodeconductor_jira import views
from nodeconductor_jira.models import Issue, Project
from nodeconductor_jira.tests import factories
from nodeconductor.structure.models import CustomerRole, ProjectRole, ProjectGroupRole
from nodeconductor.structure.tests import factories as structure_factories


views.ProjectViewSet.async_executor = True
views.IssueViewSet.async_executor = True
views.CommentViewSet.async_executor = True
views.AttachmentViewSet.async_executor = True


class BasePermissionTest(test.APITransactionTestCase):

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
        self.global_project = factories.ProjectFactory(service_project_link=self.spl,
                                                       available_for_all=True,
                                                       state=Project.States.OK)


@ddt
class ProjectPermissionTest(BasePermissionTest):

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

    def _get_issue_payload(self, project):
        return {
            'project': factories.ProjectFactory.get_url(project),
            'summary': 'Summary',
            'description': '',
            'priority': 'Minor',
            'impact': 'Small - Partial loss of service, one person affected',
        }


class IssuePermissionTest(BasePermissionTest):
    def setUp(self):
        super(IssuePermissionTest, self).setUp()
        self.author = self.users['manager']
        self.non_author = self.users['no_role']

        self.issue = factories.IssueFactory(
            project=self.global_project,
            state=Issue.States.OK,
            user=self.author
        )
        self.issue_url = factories.IssueFactory.get_url(self.issue)

    def test_staff_can_list_all_issues(self):
        """
        Issues without author are listed too.
        """
        issue_without_user = factories.IssueFactory()
        self.client.force_authenticate(structure_factories.UserFactory(is_staff=True))
        response = self.client.get(factories.IssueFactory.get_list_url())
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
        self.assertTrue(issue_without_user.uuid.hex in [issue['uuid'] for issue in response.data])
        self.assertTrue(self.issue.uuid.hex in [issue['uuid'] for issue in response.data])

    def test_staff_can_get_issue(self):
        self.client.force_authenticate(structure_factories.UserFactory(is_staff=True))
        response = self.client.get(self.issue_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_author_can_list_its_own_issues(self):
        self.client.force_authenticate(self.author)
        response = self.client.get(factories.IssueFactory.get_list_url())
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertTrue(self.issue.uuid.hex in [issue['uuid'] for issue in response.data])

    def test_author_can_get_issue(self):
        self.client.force_authenticate(self.author)
        response = self.client.get(self.issue_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_author_can_patch_issue(self):
        self.client.force_authenticate(self.author)
        response = self.client.patch(self.issue_url, {'description': 'do it'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_author_can_delete_issue(self):
        self.client.force_authenticate(self.author)
        response = self.client.delete(self.issue_url)
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)

    def test_non_author_can_not_list_other_issues(self):
        self.client.force_authenticate(self.non_author)
        response = self.client.get(factories.IssueFactory.get_list_url())
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 0)

    def test_non_author_can_not_get_issue(self):
        self.client.force_authenticate(self.non_author)
        response = self.client.get(self.issue_url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_non_author_can_not_delete_issue(self):
        self.client.force_authenticate(self.non_author)
        response = self.client.delete(self.issue_url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
