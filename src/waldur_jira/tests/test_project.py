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


class BaseProjectImportTest(test.APITransactionTestCase):

    def _generate_backend_projects(self, count=1):
        projects = []
        for i in range(count):
            project = factories.ProjectFactory()
            project.delete()
            projects.append(project)

        return projects


class ProjectImportableResourcesTest(BaseProjectImportTest):

    def setUp(self):
        super(ProjectImportableResourcesTest, self).setUp()
        self.url = factories.ProjectFactory.get_list_url('importable_resources')
        self.fixture = fixtures.JiraFixture()
        self.client.force_authenticate(self.fixture.owner)

    @mock.patch('waldur_jira.backend.JiraBackend.get_resources_for_import')
    def test_importable_volumes_are_returned(self, get_projects_mock):
        backend_projects = self._generate_backend_projects()
        get_projects_mock.return_value = backend_projects
        data = {
            'service_project_link':
                factories.JiraServiceProjectLinkFactory.get_url(self.fixture.service_project_link)
        }

        response = self.client.get(self.url, data=data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEquals(len(response.data), len(backend_projects))
        returned_backend_ids = [item['backend_id'] for item in response.data]
        expected_backend_ids = [item.backend_id for item in backend_projects]
        self.assertItemsEqual(returned_backend_ids, expected_backend_ids)
        get_projects_mock.assert_called()


class ProjectImportResourceTest(BaseProjectImportTest):

    def setUp(self):
        super(ProjectImportResourceTest, self).setUp()
        self.url = factories.ProjectFactory.get_list_url('import_resource')
        self.fixture = fixtures.JiraFixture()
        self.client.force_authenticate(self.fixture.owner)

    @mock.patch('waldur_jira.backend.JiraBackend.import_project')
    def test_backend_project_is_imported(self, import_project_mock):
        backend_id = 'backend_id'

        def import_project(backend_id, service_project_link):
            return self._generate_backend_projects()[0]

        import_project_mock.side_effect = import_project

        payload = {
            'backend_id': backend_id,
            'service_project_link': factories.JiraServiceProjectLinkFactory.get_url(self.fixture.service_project_link),
        }

        response = self.client.post(self.url, payload)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

    @mock.patch('waldur_jira.backend.JiraBackend.import_project')
    def test_backend_project_cannot_be_imported_if_it_is_registered_in_waldur(self, import_snapshot_mock):
        project = factories.ProjectFactory(service_project_link=self.fixture.service_project_link)

        def import_project(backend_id, service_project_link):
            return project

        import_snapshot_mock.side_effect = import_project

        payload = {
            'backend_id': project.backend_id,
            'service_project_link': factories.JiraServiceProjectLinkFactory.get_url(self.fixture.service_project_link),
        }

        response = self.client.post(self.url, payload)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
