from ..base_classe import BaseTestClass
from tasks.models import Task


class TestListTaskView(BaseTestClass):
    """### Flow
    - user need to be authenticated
    - test user can only get task where is has access to the org or department or his is part of
    the user that the task is assigne_to or he is in the can_be_accessed_by list on a task object or error
    - test user with can get needed data
    - test response is paginated
    - test we can apply filters, e.g a search through filter
    """
    url_name = "tasks-list"

    def test_only_authenticated_user_can_access(self):
        self.evaluate_method_unauthenticated_request(
            self.HTTP_GET
        )

    def setUp(self):
        self.user = self.create_and_active_user()