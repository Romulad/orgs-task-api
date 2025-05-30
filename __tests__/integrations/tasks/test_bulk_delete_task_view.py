import uuid

from ..base_classe import BaseTestClass
from tasks.models import Task


class TestBulkDeleteTaskView(BaseTestClass):
    """### Flow
    - user need to be authenticated
    - request data need to be validate and include valid ids
    - test if a task exist in the list and the user has only assigned_to status, anything is deleted
    and it get 403
    - test user without any access to the task get not found error and datas still exist
    - test user with access on tasks can delete them:
        - org owners can delete data in their org
        - depart owners can delete data in their department
        - task owners can delete data where they are creator or have access to
    - test user with assigned_to status but with any owner status can still delete task in the list
    - test ressources are deleted by marking it as is_delete and success response 204
    - when user make request to delete ressources he has access to and some are not found
    success response should be sent containing what was deleted and what was not found, 
    - when user make request with not found ids 404 error message 
    """
    url_name = "tasks-bulk-delete"
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


    def setUp(self):
        self.owner_user, self.org_creator, self.org = self.create_new_org()
        task_data = [*self.task_data]
        for data in task_data:
            data["org"] = self.org
        self.tasks = self.bulk_create_object(Task, task_data)
        self.simple_user = self.create_and_activate_random_user()
    
    def test_only_authenticated_user_can_access(self):
        self.evaluate_method_unauthenticated_request(
            self.HTTP_DELETE, {}
        )
    
    def test_with_malformatted_data(self):
        response = self.auth_delete(self.owner_user, {"ids": ["fake-id", "fake-id2"]})
        self.assertEqual(response.status_code, self.status.HTTP_400_BAD_REQUEST)
        # check response data
        data = self.loads(response.content)
        self.assertIsInstance(data.get("ids"), dict)
    
    def test_not_found_ressources(self):
        req_ids = [uuid.uuid4(), uuid.uuid4()]
        
        response = self.auth_delete(self.owner_user, {"ids": req_ids})
        self.assertEqual(response.status_code, self.status.HTTP_404_NOT_FOUND)
        # check response data
        data = self.loads(response.content)
        self.assertIsNotNone(data.get("detail"))
    
    def test_assigned_to_user_cant_bulk_delete_task(self):
        # where user is only in assigne_to list
        first_task = self.tasks[0]
        first_task.assigned_to.add(self.simple_user)
        # And owner status on other
        for task in self.tasks[1:]:
            task.created_by = self.simple_user
            task.can_be_accessed_by.add(self.simple_user)
            task.save()

        response = self.auth_delete(
            self.simple_user, 
            {"ids": self.get_ids_from(self.tasks)}
        )
        self.assertEqual(response.status_code, self.status.HTTP_403_FORBIDDEN)
        # ressources still exist
        [Task.objects.get(id=task.id) for task in self.tasks]
    
    def test_user_cant_data_they_dont_have_access_to(self):
        depart_creator, depart = self.create_new_depart(self.org)
        
        can_access_depart_user = self.create_and_activate_random_user()
        depart.can_be_accessed_by.add(can_access_depart_user)

        task_creator = self.create_and_activate_random_user()
        can_access_task_user = self.create_and_activate_random_user()

        first_task = self.tasks[0]
        first_task.created_by = task_creator
        first_task.save()
        first_task.can_be_accessed_by.add(can_access_task_user)

        for user in [
            self.simple_user,
            depart_creator,
            can_access_depart_user,
            task_creator,
            can_access_task_user
        ]:
            response = self.auth_delete(user, {'ids': self.get_ids_from(self.tasks[1:])})
            self.assertEqual(response.status_code, self.status.HTTP_404_NOT_FOUND)
        # ressources still exist
        [Task.objects.get(id=task.id) for task in self.tasks]
    
    def test_access_allow_user_can_delete_data(self):
        can_access_org_user = self.create_and_activate_random_user()
        self.org.can_be_accessed_by.add(can_access_org_user)

        depart_creator, depart = self.create_new_depart(self.org)
        can_access_depart_user = self.create_and_activate_random_user()
        depart.can_be_accessed_by.add(can_access_depart_user)

        task_creator = self.create_and_activate_random_user()
        can_access_task_user = self.create_and_activate_random_user()

        for task in self.tasks:
            task.depart = depart
            task.created_by = task_creator
            task.save()
            task.can_be_accessed_by.add(can_access_task_user)
        
        for user in [
            self.org_creator,
            self.owner_user,
            can_access_org_user,
            depart_creator,
            can_access_depart_user,
            task_creator,
            can_access_task_user
        ]:
            ids = self.get_ids_from(self.tasks)
            response = self.auth_delete(user, {"ids": ids})
            self.assertEqual(response.status_code, self.status.HTTP_204_NO_CONTENT)
            for task_id in ids: 
                with self.assertRaises(Task.DoesNotExist):
                    Task.objects.get(id=task_id)
                Task.all_objects.get(id=task_id)
            # reset data for next user
            Task.all_objects.filter(id__in=ids).update(is_deleted=False)
    
    def test_assigned_user_with_access_status_can_still_delete_data(self):
        self.org.can_be_accessed_by.add(self.simple_user)

        # where owner user is in assigne_to list
        first_task = self.tasks[0]
        first_task.assigned_to.add(self.simple_user)

        ids = self.get_ids_from(self.tasks)
        response = self.auth_delete(self.simple_user, {"ids": ids})
        self.assertEqual(response.status_code, self.status.HTTP_204_NO_CONTENT)
        for task_id in ids: 
            with self.assertRaises(Task.DoesNotExist):
                Task.objects.get(id=task_id)

    def test_delete_data_with_no_found(self):
        ids = self.get_ids_from(self.tasks) + [uuid.uuid4()]
        response = self.auth_delete(self.owner_user, {"ids": ids})
        self.assertEqual(response.status_code, self.status.HTTP_200_OK)
        data = self.loads(response.content)
        self.assertIsInstance(data.get("deleted"), list)
        self.assertIsInstance(data.get("not_found"), list)
        self.assertEqual(len(data.get("deleted")), 3)
        self.assertEqual(len(data.get("not_found")), 1)
        for task_id in ids: 
            with self.assertRaises(Task.DoesNotExist):
                Task.objects.get(id=task_id)