from ..base_classe import BaseTestClass
from tasks.models import Task


class TestRetrieveTaskView(BaseTestClass):
    """### Flow
    - user need to be authenticated
    - test user get not found when ressource doesn't exist
    - test user can only get task when he has access to the org or department or his is part of
    the user that the task is assigne_to or he is in the can_be_accessed_by list on the task object or error
    - test user with can get needed data after request
    """
    url_name = "tasks-detail"

    def test_only_authenticated_user_can_access(self):
        self.evaluate_method_unauthenticated_request(
            self.HTTP_GET, ['fake_id']
        )

    def setUp(self):
        self.user = self.create_and_active_user()