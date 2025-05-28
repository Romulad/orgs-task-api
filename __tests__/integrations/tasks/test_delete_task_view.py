from ..base_classe import BaseTestClass
from tasks.models import Task


class TestDeleteTaskView(BaseTestClass):
    """### Flow
    - user need to be authenticated
    - test user get not found when ressource doesn't exist
    - test user can only delete task when he has access to the org or department or he is in the 
    can_be_accessed_by list on the task object or error
    - test task is deleted with success response and doesn't exist on objects anymore but available 
    on all_object with it is_delete set to true
    """
    url_name = "tasks-detail"

    def test_only_authenticated_user_can_access(self):
        self.evaluate_method_unauthenticated_request(
            self.HTTP_DELETE, ['fake_id']
        )

    def setUp(self):
        self.user = self.create_and_active_user()