import uuid

from ...base_classe import BaseTestClass

class TestUpdateTaskStatusView(BaseTestClass):
    """### Flow
    - test user need to be authenticated
    - test user get not found when ressource does not exist
    - test other user in the org or outside not related to the task can not update status and get
    not found error
    - test field validation:
        - field `status` is required
        - field `status` can not be an empty string 
        - field should have a valid value
    - test users:
        - task creator, access allowed, assigne_to can update task status
        - org creator, owner, access allowed can update task status
        - depart creator, access allowed can update task status
    - test status is successfully updated
    """
    url_name = 'tasks-update-status'

    def setUp(self):
        self.owner_user, self.org_creator, self.org = self.create_new_org()
        self.task_creator, self.target_task = self.create_new_task(self.org)
        self.Task = self.target_task.__class__
        self.simple_user = self.create_and_activate_random_user()
    
    def test_only_authenticated_user_can_access(self):
        self.evaluate_method_unauthenticated_request(
            self.HTTP_PATCH, ["fake-id"]
        )
    
    def test_not_found_ressource(self):
        response = self.auth_patch(self.owner_user, {}, [uuid.uuid4()])
        self.assertEqual(response.status_code, self.status.HTTP_404_NOT_FOUND)
        self.assertIsNotNone(response.data.get("detail", None))
    
    def test_user_without_access_to_the_task_cant_update_it_status(self):
        org_member = self.create_and_activate_random_user()
        self.org.members.add(org_member)

        depart_creator, depart = self.create_new_depart(self.org)
        can_access_depart_user = self.create_and_activate_random_user()
        depart.can_be_accessed_by.add(can_access_depart_user)

        for user in [
            depart_creator,
            can_access_depart_user,
            self.simple_user,
            org_member
        ]:
            response = self.auth_patch(user, {}, [self.target_task.id])
            self.assertEqual(response.status_code, self.status.HTTP_404_NOT_FOUND)
            self.assertIsNotNone(response.data.get("detail", None))
    
    def test_status_validation(self):
        test_datas = [
            {},
            {'status': ""},
            {"status": "inavlid-status"}
        ]
        for req_data in test_datas:
            response = self.auth_patch(self.owner_user, req_data, [self.target_task.id])
            self.assertEqual(response.status_code, self.status.HTTP_400_BAD_REQUEST)
            errors = self.loads(response.content).get('status')
            self.assertIsInstance(errors, list)
        self.target_task.refresh_from_db()
        self.assertNotEqual(self.target_task.status, "inavlid-status")
        self.assertNotEqual(self.target_task.status, "")
    
    def test_user_can_update_task_status(self):
        self.target_task.assigned_to.add(self.simple_user)

        can_access_org_user = self.create_and_activate_random_user()
        self.org.can_be_accessed_by.add(can_access_org_user)

        can_access_task_user = self.create_and_activate_random_user()
        self.target_task.can_be_accessed_by.add(can_access_task_user)

        depart_creator, depart = self.create_new_depart(self.org)
        can_access_depart_user = self.create_and_activate_random_user()
        self.target_task.depart = depart
        self.target_task.save()
        depart.can_be_accessed_by.add(can_access_depart_user)

        users = [
            self.task_creator,
            can_access_task_user,
            self.simple_user,
            self.org_creator,
            self.owner_user,
            can_access_org_user,
            depart_creator,
            can_access_depart_user
        ]

        for user in users:
            response = self.auth_patch(
                user, 
                {"status": self.Task.Status.COMPLETED},
                [self.target_task.id]
            )
            self.assertEqual(response.status_code, self.status.HTTP_200_OK)
            data = self.loads(response.content).get("status")
            self.assertEqual(data, self.Task.Status.COMPLETED.value)
            self.target_task.refresh_from_db()
            self.assertEqual(self.target_task.status, self.Task.Status.COMPLETED.value)
            # reset for next user
            self.target_task.status = self.Task.Status.PENDING
            self.target_task.save()
    