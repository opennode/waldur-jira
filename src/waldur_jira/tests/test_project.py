from ddt import ddt, data
from rest_framework import test, status

from . import fixtures, utils


@ddt
@utils.jira_sync_project(enable=False)
class ProjectPermissionTest(test.APITransactionTestCase):
    def setUp(self):
        self.fixture = fixtures.JiraFixture()

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
