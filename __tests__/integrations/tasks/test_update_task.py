from ..base_classe import BaseTestClass
from tasks.models import Task


class TestUpdateTaskView(BaseTestClass):
    """### Flow
    - user need to be authenticated
    - test user get not found when ressource doesn't exist
    - test simple user, other depart owner, other can't udpdate the task obj
    - test all field is required
    - test data validation: (here an instance already exist)
        - test `name` field validation:
            - `name` should be unique with the org if new and other than the existed instance name
        - test `org` validation:
            - if org id different from existing intance org id test the user updating the ressource 
            should have a full access over the new org
        - test `assigned_to` if include in data:
            - `assigned_to` should b valid user ids
            - the org owner should have a full access over `assigned_to`
        - test `due_date` is properly validate if included
        - test user can not choose different `priority` value
        - test user can not choose different `status` value
        - test `estimated_duration` if specified can only accept valida data
        - test `actual_duration` if specified can only accept valid data
        - test `allowed_status_update` if specified can only accept valid data
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