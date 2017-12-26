import mock
from django.conf import settings
from rest_framework import test, status

from waldur_core.structure.tests import factories as structure_factories

from . import factories, fixtures
from .. import models


class BaseTest(test.APITransactionTestCase):
    def setUp(self):
        self.fixture = fixtures.JiraFixture()
        self.author = self.fixture.manager
        self.non_author = self.fixture.user

        self.issue = factories.IssueFactory(
            project=self.fixture.jira_project,
            state=models.Issue.States.OK,
            user=self.author
        )
        self.issue_url = factories.IssueFactory.get_url(self.issue)


class IssueGetTest(BaseTest):

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

    def test_author_can_list_its_own_issues(self):
        self.client.force_authenticate(self.author)
        response = self.client.get(factories.IssueFactory.get_list_url())
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertTrue(self.issue.uuid.hex in [issue['uuid'] for issue in response.data])

    def test_non_author_can_not_list_other_issues(self):
        self.client.force_authenticate(self.non_author)
        response = self.client.get(factories.IssueFactory.get_list_url())
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 0)

    def test_staff_can_get_issue(self):
        self.client.force_authenticate(self.fixture.staff)
        response = self.client.get(self.issue_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_author_can_get_issue(self):
        self.client.force_authenticate(self.author)
        response = self.client.get(self.issue_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_non_author_can_not_get_issue(self):
        self.client.force_authenticate(self.non_author)
        response = self.client.get(self.issue_url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class IssueCreateTest(BaseTest):
    def setUp(self):
        super(IssueCreateTest, self).setUp()
        self.resource = structure_factories.TestNewInstanceFactory()
        self.fixture.jira_project.issue_types.add(self.fixture.issue_type)

        self.jira_patcher = mock.patch('waldur_jira.backend.JIRA')
        self.jira_mock = self.jira_patcher.start()
        self.create_issue = self.jira_mock().create_issue
        self.create_issue.return_value = mock.Mock(**{
            'key': '',
            'fields.resolution': '',
            'fields.status.name': ''
        })

    def tearDown(self):
        super(IssueCreateTest, self).tearDown()
        mock.patch.stopall()

    def test_create_issue_with_resource(self):
        self.client.force_authenticate(self.fixture.staff)

        response = self.client.post(factories.IssueFactory.get_list_url(), self._get_issue_payload())
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

        self.assertEqual(self.create_issue.call_count, 1)

    def test_add_resource_info_in_description(self):
        self.client.force_authenticate(self.fixture.staff)

        response = self.client.post(factories.IssueFactory.get_list_url(), self._get_issue_payload())
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

        description_template = settings.WALDUR_JIRA['ISSUE_TEMPLATE']['RESOURCE_INFO']
        expected_description = description_template.format(resource=self.resource)
        actual_description = self.create_issue.call_args[1]['description']

        self.assertTrue(expected_description in actual_description)
        self.assertNotEqual(expected_description, actual_description)

    def test_issue_name_is_passed_to_backend(self):
        self.client.force_authenticate(self.fixture.staff)

        response = self.client.post(factories.IssueFactory.get_list_url(), self._get_issue_payload())
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

        issue_type_name = self.create_issue.call_args[1]['issuetype']['name']
        self.assertEqual(issue_type_name, self.fixture.issue_type.name)

    def test_issue_type_should_belong_to_project(self):
        self.fixture.jira_project.issue_types.remove(self.fixture.issue_type)
        self.client.force_authenticate(self.fixture.staff)

        response = self.client.post(factories.IssueFactory.get_list_url(), self._get_issue_payload())
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def _get_issue_payload(self):
        return {
            'project': self.fixture.jira_project_url,
            'summary': 'Summary',
            'description': 'description test issue',
            'priority': 'Minor',
            'resource': structure_factories.TestNewInstanceFactory.get_url(self.resource),
            'type': self.fixture.issue_type_url,
        }


@mock.patch('waldur_jira.executors.IssueUpdateExecutor.execute')
class IssueUpdateTest(BaseTest):
    def test_author_can_update_issue(self, update_executor):
        self.client.force_authenticate(self.author)
        response = self.client.patch(self.issue_url, {'description': 'do it'})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        update_executor.assert_called_once()

    def test_non_author_can_not_update_issue(self, update_executor):
        self.client.force_authenticate(self.non_author)
        response = self.client.patch(self.issue_url, {'description': 'do it'})

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(update_executor.call_count, 0)


@mock.patch('waldur_jira.executors.IssueDeleteExecutor.execute')
class IssueDeleteTest(BaseTest):

    def test_author_can_delete_issue(self, delete_executor):
        self.client.force_authenticate(self.author)
        response = self.client.delete(self.issue_url)

        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        delete_executor.assert_called_once()

    def test_non_author_can_not_delete_issue(self, delete_executor):
        self.client.force_authenticate(self.non_author)
        response = self.client.delete(self.issue_url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(delete_executor.call_count, 0)
