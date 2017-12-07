import mock
from ddt import ddt, data
from django.conf import settings
from rest_framework import test, status

from waldur_core.structure.tests import factories as structure_factories

from . import factories, fixtures, utils
from .. import models


class BaseTest(test.APITransactionTestCase):
    def setUp(self):
        self.fixture = fixtures.JiraFixture()


@utils.override_jira_settings(ISSUE_TEMPLATE={'RESOURCE_INFO': '\nAffected resource: {resource}'})
@utils.jira_sync_issue(enable=True)
@mock.patch('waldur_jira.backend.JIRA')
class IssueCreateTest(BaseTest):
    def setUp(self):
        super(IssueCreateTest, self).setUp()
        self.resource = structure_factories.TestNewInstanceFactory()

    def mock_set_up(self, jira_mock):
        jira_mock.return_value = jira_mock
        m = mock.Mock(**{'key': '', 'fields.resolution': '', 'fields.status.name': ''})
        jira_mock.create_issue.return_value = m

    def test_create_issue_with_resource(self, jira_mock):
        self.mock_set_up(jira_mock)
        self.client.force_authenticate(self.fixture.staff)
        response = self.client.post(
            factories.IssueFactory.get_list_url(),
            self._get_issue_payload())
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(jira_mock.create_issue.call_count, 1)

    def test_add_resource_info_in_description(self, jira_mock):
        self.mock_set_up(jira_mock)
        self.client.force_authenticate(self.fixture.staff)
        tmpl = settings.WALDUR_JIRA['ISSUE_TEMPLATE']['RESOURCE_INFO']
        info = tmpl.format(resource=self.resource)
        response = self.client.post(
            factories.IssueFactory.get_list_url(),
            self._get_issue_payload())
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(info in jira_mock.create_issue.call_args[1]['description'])
        self.assertNotEqual(info, jira_mock.create_issue.call_args[1]['description'])

    def _get_issue_payload(self):
        return {
            'project': factories.ProjectFactory.get_url(),
            'summary': 'Summary',
            'description': 'description test issue',
            'priority': 'Minor',
            'impact': 'Small - Partial loss of service, one person affected',
            'resource': structure_factories.TestNewInstanceFactory.get_url(self.resource)
        }


@utils.jira_sync_issue(enable=False)
@ddt
class IssuePermissionTest(BaseTest):
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
