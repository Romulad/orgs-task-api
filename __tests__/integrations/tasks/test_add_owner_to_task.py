from ..base_classe import BaseTestClass
from tasks.models import Task


class TestChangeTaskOwnerView(BaseTestClass):
    """### Flow
    - user need to be authenticated
    - test user get not found when ressource doesn't exist
    - test user with access allowed on org (owner, can_be_accessed_by) can not change task owner users, 403
    - test user with access allowed on depart can't change task owner users, 403
    - test user with access allowed on task can't change task owner users, 403
    - test user can only change task owners when he is the org or department creator or he is in the 
    task itself creator or error
    - validate owner user ids provide:
        - ids should exist
        - user that is making the request should have a full access over owner user specified
    - owners are successfully added to obj can_be_accessed_by list after request
    """
    url_name = "tasks-change-owners"

    def test_only_authenticated_user_can_access(self):
        self.evaluate_method_unauthenticated_request(
            self.HTTP_POST, ['fake_id']
        )

    def setUp(self):
        self.user = self.create_and_active_user()