from ..base_classe import BaseTestClass
from tasks.models import Task


class TestBulkDeleteTaskView(BaseTestClass):
    """### Flow
    - user need to be authenticated
    - request data need to be validate and include valid ids
    - test user can only delete tasks when he has access to all the task orgs or departments or he is in the 
    can_be_accessed_by list on the task object or error
    - test ressources are deleted by marking it as is_delete and success response 204
    - when user make request to delete ressources he has access to and some are not found
    success response should be sent containing what was deleted and what was not found, 
    - when user make request with not found ids 404 error message 
    """
    url_name = "tasks-bulk-delete"

    def test_only_authenticated_user_can_access(self):
        self.evaluate_method_unauthenticated_request(
            self.HTTP_DELETE, {}
        )

    def setUp(self):
        self.user = self.create_and_active_user()