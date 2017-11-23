from ddt import ddt, data
from rest_framework import test, status

from .. import models, views
from . import factories, fixtures

views.ProjectViewSet.async_executor = True
views.IssueViewSet.async_executor = True
views.CommentViewSet.async_executor = True
views.AttachmentViewSet.async_executor = True


class BasePermissionTest(test.APITransactionTestCase):

    def setUp(self):
        self.fixture = fixtures.JiraFixture()


@ddt
class ProjectPermissionTest(BasePermissionTest):

    @data('owner', 'admin', 'manager')
    def test_user_with_access_can_access_project(self, user):
        self.client.force_authenticate(getattr(self.fixture, user))
        response = self.client.get(self.fixture.jira_project_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_user_without_access_cannot_access_project(self):
        self.client.force_authenticate(self.fixture.user)
        response = self.client.get(self.fixture.jira_project_url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    @data('owner', 'admin', 'manager', 'user')
    def test_any_user_can_access_global_project(self, user):
        self.client.force_authenticate(getattr(self.fixture, user))
        response = self.client.get(self.fixture.jira_global_project_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @data('manager', 'user')
    def test_any_user_cannot_delete_global_project(self, user):
        self.client.force_authenticate(getattr(self.fixture, user))
        response = self.client.delete(self.fixture.jira_global_project_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @data('owner', 'admin', 'manager', 'user')
    def test_any_user_can_create_issue_in_global_project(self, user):
        self.client.force_authenticate(getattr(self.fixture, user))
        response = self.client.post(
            factories.IssueFactory.get_list_url(),
            self._get_issue_payload(self.fixture.jira_global_project))
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
        self.author = self.fixture.manager
        self.non_author = self.fixture.user

        self.issue = factories.IssueFactory(
            project=self.fixture.jira_global_project,
            state=models.Issue.States.OK,
            user=self.author
        )
        self.issue_url = factories.IssueFactory.get_url(self.issue)

    def test_staff_can_list_all_issues(self):
        """
        Issues without author are listed too.
        """
        issue_without_user = factories.IssueFactory()
        self.client.force_authenticate(self.fixture.staff)
        response = self.client.get(factories.IssueFactory.get_list_url())
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
        self.assertTrue(issue_without_user.uuid.hex in [issue['uuid'] for issue in response.data])
        self.assertTrue(self.issue.uuid.hex in [issue['uuid'] for issue in response.data])

    def test_staff_can_get_issue(self):
        self.client.force_authenticate(self.fixture.staff)
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
