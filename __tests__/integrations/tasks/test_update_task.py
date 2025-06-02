from ..base_classe import BaseTestClass
from tasks.models import Task


class TestUpdateTaskView(BaseTestClass):
    """### Flow
    - user need to be authenticated
    - test user get not found when ressource doesn't exist
    - other depart owners, other user can't udpdate the task obj - 404
    - test assigned to users that has access to the task and it not owner can't update task - 403
    - test all field is required - 400
    - test data validation: (here an instance already exist)
        - test `name` field validation:
            - `name` should be unique with the org if new and other than the existed instance name
        - test `org` validation:
            - if org id different from existing intance org id test the user updating the ressource 
            has a full access over the new org
        - test `assigned_to`:
            - `assigned_to` can be empty but should be include
            - `assigned_to` should be valid user ids
            - the org owner should have a full access over `assigned_to`
        - test `due_date`:
            - can be empty but should be include
            - test it is properly validate if not null
        - test `priority`:
            - `priority` field should be include
            - user can not choose different `priority` value
        - test `status`:
            - `status` field should be include
            - user can not choose different `status` value
        - test `estimated_duration` can only accept valida data
        - test `actual_duration` can only accept valid data
        - test `tags` validation if specified:
            - test the tags should exist
            - test the tags specified for the task should all belongs to the task org, we should
            not include a tag from another org
        - test `depart` vaidation if specified:
            - test depart exist first
            - test the depart specified and the task been created has the same org
    - test assigned_to get automatically added to org if not existed by default
    - test task is successfully created with needed data and needed response is returned
    - test user can only update task when he has access to the org or department or he is in the 
    can_be_accessed_by list on the task object or error
    """
    url_name = "tasks-detail"

    def test_only_authenticated_user_can_access(self):
        self.evaluate_method_unauthenticated_request(
            self.HTTP_PUT, ["fake-id"]
        )

    def setUp(self):
        self.user = self.create_and_active_user()