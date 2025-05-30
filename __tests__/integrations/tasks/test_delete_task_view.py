import uuid

from ..base_classe import BaseTestClass
from tasks.models import Task


class TestDeleteTaskView(BaseTestClass):
    """### Flow
    - user need to be authenticated
    - test user get not found when ressource doesn't exist
    - test assigned_to user can not delete data they are part of
    - test depart owners, task owners, can not delete task their don't have access to in the org
    - test:
        - org owners can delete data in their org
        - depart owners can delete data in their department
        - task owners can delete data where they are creator or have access to
    - test task is deleted with success response and doesn't exist on objects anymore but available 
    on all_objects with it is_delete set to true
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
            self.HTTP_DELETE, ['fake_id']
        )

    def setUp(self):
        self.owner_user, self.org_creator, self.org = self.create_new_org()
        task_data = [*self.task_data]
        for data in task_data:
            data["org"] = self.org
        self.tasks = self.bulk_create_object(Task, task_data)
        self.simple_user = self.create_and_activate_random_user()
    
    def test_not_found_ressource(self):
        response = self.auth_delete(self.owner_user, {}, [uuid.uuid4()])
        self.assertEqual(response.status_code, self.status.HTTP_404_NOT_FOUND)
        self.assertIsNotNone(response.data.get("detail", None))
    
    def test_other_cant_delete_data(self):
        target_task = self.tasks[0]
        other_user = self.create_and_activate_random_user()
        response = self.auth_delete(
            other_user,
            {},
            [target_task.id]
        )
        self.assertEqual(response.status_code, self.status.HTTP_404_NOT_FOUND)
        self.assertIsNotNone(response.data.get("detail", None))
        # ressource still exists
        Task.objects.get(id=target_task.id)

    def test_assigned_to_user_cant_delete_data(self):
        target_task = self.tasks[0]
        assigned_to = self.create_and_activate_random_user()
        target_task.assigned_to.add(assigned_to)

        response = self.auth_delete(
            assigned_to,
            {},
            [target_task.id]
        )
        self.assertEqual(response.status_code, self.status.HTTP_403_FORBIDDEN)
        self.assertIsNotNone(response.data.get("detail", None))
        # ressource still exists
        Task.objects.get(id=target_task.id)
    
    def test_user_in_org_cant_delete_data(self):
        target_task = self.tasks[0]
        
        depart_creator, depart = self.create_new_depart(self.org)
        can_access_depart = self.create_and_activate_random_user()
        depart.can_be_accessed_by.add(can_access_depart)

        task_creator = self.create_and_activate_random_user()
        can_access_task = self.create_and_activate_random_user()

        for task in self.tasks[1:]:
            task.depart = depart
            task.created_by = task_creator
            task.save()
            task.can_be_accessed_by.add(can_access_task)

        for user in [depart_creator, can_access_depart, task_creator, can_access_task]:
            response = self.auth_delete(
                user,
                {},
                [target_task.id]
            )
            self.assertEqual(response.status_code, self.status.HTTP_404_NOT_FOUND)
            self.assertIsNotNone(response.data.get("detail", None))
        # ressource still exists
        Task.objects.get(id=target_task.id)
    
    def test_org_owner_creator_accessallow_can_delete_data(self):
        # someone who have access to the org
        self.org.can_be_accessed_by.add(self.simple_user)

        next_obj = 0
        for user in [self.org_creator, self.owner_user, self.simple_user]:
            target_obj = self.tasks[next_obj]
            response = self.auth_delete(
                user,
                {},
                [target_obj.id]
            )
            self.assertEqual(response.status_code, self.status.HTTP_204_NO_CONTENT)
            with self.assertRaises(Task.DoesNotExist):
                Task.objects.get(id=target_obj.id)
            Task.all_objects.get(id=target_obj.id)
            next_obj += 1
    
    def test_depart_creator_accessallow_can_delete_data(self):
        depart_creator, depart = self.create_new_depart(self.org)
        can_access_depart = self.create_and_activate_random_user()
        depart.can_be_accessed_by.add(can_access_depart)

        for task in self.tasks[:]:
            task.depart = depart
            task.save()

        next_obj = 0
        for user in [depart_creator, can_access_depart]:
            target_obj = self.tasks[next_obj]
            response = self.auth_delete(
                user,
                {},
                [target_obj.id]
            )
            self.assertEqual(response.status_code, self.status.HTTP_204_NO_CONTENT)
            with self.assertRaises(Task.DoesNotExist):
                Task.objects.get(id=target_obj.id)
            Task.all_objects.get(id=target_obj.id)
            next_obj += 1
    
    def test_task_creator_accessallow_can_delete_data(self):
        task_creator = self.create_and_activate_random_user()
        can_access_task = self.create_and_activate_random_user()

        for task in self.tasks[:]:
            task.created_by = task_creator
            task.save()
            task.can_be_accessed_by.add(can_access_task)

        next_obj = 0
        for user in [task_creator, can_access_task]:
            target_obj = self.tasks[next_obj]
            response = self.auth_delete(
                user,
                {},
                [target_obj.id]
            )
            self.assertEqual(response.status_code, self.status.HTTP_204_NO_CONTENT)
            with self.assertRaises(Task.DoesNotExist):
                Task.objects.get(id=target_obj.id)
            Task.all_objects.get(id=target_obj.id)
            next_obj += 1