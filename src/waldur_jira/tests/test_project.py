import mock
from ddt import ddt, data
from rest_framework import test, status

from . import factories, fixtures


class ProjectBaseTest(test.APITransactionTestCase):
    def setUp(self):
        self.fixture = fixtures.JiraFixture()


@ddt
class ProjectGetTest(ProjectBaseTest):

    @data('owner', 'admin', 'manager')
    def test_user_with_access_can_access_project(self, user):
        self.client.force_authenticate(getattr(self.fixture, user))
        response = self.client.get(self.fixture.jira_project_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_user_without_access_cannot_access_project(self):
        self.client.force_authenticate(self.fixture.user)
        response = self.client.get(self.fixture.jira_project_url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


@ddt
@mock.patch('waldur_jira.executors.ProjectCreateExecutor.execute')
class ProjectCreateTest(ProjectBaseTest):

    def test_user_can_create_project(self, executor):
        self.client.force_authenticate(self.fixture.staff)
        response = self.client.post(self.get_url(), self.get_valid_payload())
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        executor.assert_called_once()

    @data('key with spaces', 'T0000LONGKEY')
    def test_user_can_not_create_project_with_invalid_key(self, key, executor):
        self.client.force_authenticate(self.fixture.staff)
        payload = self.get_valid_payload()
        payload.update(dict(key=key))
        response = self.client.post(self.get_url(), payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def get_url(self):
        return factories.ProjectFactory.get_list_url()

    def get_valid_payload(self):
        return {
            'name': 'Test project',
            'key': 'TST',
            'template': self.fixture.jira_project_template_url,
            'service_project_link': self.fixture.service_project_link_url,
        }


@ddt
@mock.patch('waldur_jira.executors.ProjectDeleteExecutor.execute')
class ProjectDeleteTest(ProjectBaseTest):

    @data('staff',)
    def test_staff_can_delete_project(self, user, executor):
        self.client.force_authenticate(getattr(self.fixture, user))
        response = self.client.delete(self.fixture.jira_project_url)
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        executor.assert_called_once()

    @data('owner', 'admin', 'manager')
    def test_other_users_cannot_delete_project(self, user, executor):
        self.client.force_authenticate(getattr(self.fixture, user))
        response = self.client.delete(self.fixture.jira_project_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
