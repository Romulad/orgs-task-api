import uuid

from ..base_classe import BaseTestClass
from tasks.models import Task
from organization.models import (
    Organization,
    Department
)


class TestRetrieveTaskView(BaseTestClass):
    """### Flow
    - user need to be authenticated
    - test user get not found when ressource doesn't exist
    - test user can only get task when he has access to the task org or department or his is part of
    the user that the task is assigne_to or he is the task creator or he is in the can_be_accessed_by 
    list on the task object or 404 error
    - test user with access can get needed data after request
    """
    url_name = "tasks-detail"
    task_data = [
        {
            "name": "first_task"
        },
        {
            "name": "second_task"
        },
        {
            "name": "third_task"
        }
    ]

    def test_only_authenticated_user_can_access(self):
        self.evaluate_method_unauthenticated_request(
            self.HTTP_GET, ['fake_id']
        )

    def setUp(self):
        self.owner_user = self.create_and_active_user(email="owner_user@dshgd.com")
        self.org = Organization.objects.create(
            name="owner_org",
            owner=self.owner_user, 
            created_by=self.owner_user
        )
        task_data = [*self.task_data]
        for data in task_data:
            data["org"] = self.org
        self.tasks = self.bulk_create_object(Task, task_data)
        self.simple_user = self.create_and_active_user(email="simple_user@gamail.com")
    
    def test_not_found_ressource(self):
        response = self.auth_get(self.owner_user, [uuid.uuid4()])
        self.assertEqual(response.status_code, self.status.HTTP_404_NOT_FOUND)
        self.assertIsNotNone(response.data.get("detail", None))
    
    def test_user_cant_get_other_user(self):
        target_ressource = self.tasks[0]
        response = self.auth_get(self.simple_user, [target_ressource.id])
        self.assertEqual(response.status_code, self.status.HTTP_404_NOT_FOUND)
        self.assertIsNotNone(response.data.get("detail", None))
    
    def test_access_allowed_can_get_ressource(self):
        new_depart = Department.objects.create(
            name="new_department",
            org=self.org,
        )
        target_ressource = self.tasks[0]
        target_ressource.depart = new_depart
        target_ressource.save()

        # user that has access to the org the task belongs to
        self.org.can_be_accessed_by.add(self.simple_user)

        # for depart owner
        depart_owner = self.create_and_active_user(email="access_allowed_user@testjiu.com")
        new_depart.created_by = depart_owner
        new_depart.save()

        # user that has access to depart the task belongs to
        depart_access_allowed = self.create_and_active_user(email="depart_access_allowed@testjiu.com")
        new_depart.can_be_accessed_by.add(depart_access_allowed)

        # for user who create the task, the user in any way will need a permission before being
        # able to create a task for the org
        task_creator = self.create_and_active_user(email="task_creator@dhsj.com")
        target_ressource.created_by = task_creator
        target_ressource.save()

        # for users who have access to the task
        can_access_task = self.create_and_active_user(email="can_access_task@dhsj.com")
        target_ressource.can_be_accessed_by.add(can_access_task)

        # user that is assigned to the task
        assigned_user = self.create_and_active_user(email="assigned_user@dhsj.com")
        target_ressource.assigned_to.add(assigned_user)

        users = [
            self.owner_user,
            self.simple_user,
            depart_owner,
            depart_access_allowed,
            task_creator,
            can_access_task,
            assigned_user
        ]

        for user in users:
            response = self.auth_get(user, [target_ressource.id])
            self.assertEqual(response.status_code, self.status.HTTP_200_OK)
            data = self.loads(response.content)
            self.assertEqual(data.get("id"), str(target_ressource.id))
            self.assertEqual(data.get("name"), target_ressource.name)
            self.assertEqual(data.get("description"), target_ressource.description)
            self.assertEqual(data.get("assigned_to")[0]["id"], str(assigned_user.id))
            self.assertEqual(data.get("assigned_to")[0]["email"], assigned_user.email)
            self.assertEqual(data.get("org")["id"], str(target_ressource.org.id))
            self.assertEqual(data.get("depart")["id"], str(new_depart.id))


            