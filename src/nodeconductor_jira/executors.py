from django.conf import settings

from nodeconductor.core import tasks, executors


class ProjectCreateExecutor(executors.CreateExecutor):

    @classmethod
    def get_task_signature(cls, project, serialized_project, **kwargs):
        return tasks.BackendMethodTask().si(
            'create_project', project.backend_id, project.name, state_transition='begin_creating')


class ProjectDeleteExecutor(executors.DeleteExecutor):

    @classmethod
    def get_task_signature(cls, project, serialized_project, **kwargs):
        if project.backend_id:
            return tasks.BackendMethodTask().si(
                'delete_project', project.backend_id, state_transition='begin_deleting')
        else:
            return tasks.StateTransitionTask().si(serialized_project, state_transition='begin_deleting')
