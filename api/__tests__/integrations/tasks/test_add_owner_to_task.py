import uuid

from ...base_classe import BaseTestClass
from tasks.models import Task
from app_lib.app_permssions import CAN_CHANGE_RESSOURCES_OWNERS


class TestChangeTaskOwnerView(BaseTestClass):
    """### Flow
    - user need to be authenticated
    - test user get not found when ressource doesn't exist
    - test user with access allowed on org (owner, can_be_accessed_by) can not change task owner users, 403
    - test user with access allowed on depart can't change task owner users, 403
    - test user with access allowed on task can't change task owner users, 403
    - test assigned to user can change task owners 403
    - test other user can't change task owners 404
    - validate owner user ids provide:
        - ids should exist
        - user that is making the request should have a full access over owner user specified
    - test user can only change task owners when he is the org or department creator or he is the 
    task itself creator
    - owners are successfully added to obj can_be_accessed_by list after request
    """
    url_name = "tasks-change-owners"

    def setUp(self):
        self.owner_user, self.org_creator, self.org = self.create_new_org()
        task_data = [{"name": "first_task", "org": self.org}]
        self.task = self.bulk_create_object(Task, task_data)[0]
        self.simple_user = self.create_and_activate_random_user()
    
    def test_only_authenticated_user_can_access(self):
        self.evaluate_method_unauthenticated_request(
            self.HTTP_POST, ['fake_id']
        )
    
    def test_not_found_task(self):
        response = self.auth_post(self.owner_user, {}, [uuid.uuid4()])
        self.assertEqual(response.status_code, self.status.HTTP_404_NOT_FOUND)
        # check response data
        data = self.loads(response.content)
        self.assertIsNotNone(data.get("detail"))
    
    def test_no_creator_user_cant_update_task_access_list(self):
        self.org.can_be_accessed_by.add(self.simple_user)

        _, depart = self.create_new_depart(self.org)
        can_access_depart_user = self.create_and_activate_random_user()
        depart.can_be_accessed_by.add(can_access_depart_user)
        self.task.depart = depart
        self.task.save()

        can_access_task = self.create_and_activate_random_user()
        self.task.can_be_accessed_by.add(can_access_task)

        assigned_to_user = self.create_and_activate_random_user()
        self.task.assigned_to.add(assigned_to_user)

        user_to_add = self.create_and_activate_random_user()

        for user in [
            self.owner_user,
            self.simple_user,
            can_access_depart_user,
            can_access_task,
            assigned_to_user
        ]:
            response = self.auth_post(
                user, {"owner_ids": [user_to_add.id]}, [self.task.id]
            )
            self.assertEqual(response.status_code, self.status.HTTP_403_FORBIDDEN)
            # obj access list still 1
            self.task.refresh_from_db()
            self.assertEqual(
                len(self.task.can_be_accessed_by.all()), 1
            )
    
    def test_other_user_cant_update_task_access_list(self):
        depart_creator, depart = self.create_new_depart(self.org)
        can_access_depart_user = self.create_and_activate_random_user()
        depart.can_be_accessed_by.add(can_access_depart_user)

        user_to_add = self.create_and_activate_random_user()

        for user in [
            self.simple_user,
            can_access_depart_user,
            depart_creator,
        ]:
            response = self.auth_post(
                user, {"owner_ids": [user_to_add.id]}, [self.task.id]
            )
            self.assertEqual(response.status_code, self.status.HTTP_404_NOT_FOUND)
            # check response data
            data = self.loads(response.content)
            self.assertIsNotNone(data.get("detail"))
            # obj access list still empty
            self.task.refresh_from_db()
            self.assertEqual(
                len(self.task.can_be_accessed_by.all()), 0
            )
    
    def test_req_data_validation_ids(self):
        test_datas = [
            {},
            {"owner_ids": []},
            {"owner_ids": [uuid.uuid4(), uuid.uuid4()]},
            {"owner_ids": [self.simple_user.id]}
        ]

        for test_data in test_datas:
            response = self.auth_post(self.org_creator, test_data, [self.task.id])
            self.assertEqual(response.status_code, self.status.HTTP_400_BAD_REQUEST)
            self.assertIsNotNone(response.data.get("owner_ids", None))
            self.assertIsInstance(response.data.get("owner_ids"), list)
        self.assertEqual(
            len(Task.objects.get(id=self.task.id).can_be_accessed_by.all()), 0
        )

    def test_creators_can_update_access_list(self):
        depart_creator, depart = self.create_new_depart(self.org)
        self.task.depart = depart
        self.task.save()

        task_creator = self.create_and_activate_random_user()
        self.task.created_by = task_creator
        self.task.save()

        self.simple_user.can_be_accessed_by.add(
            self.org_creator, depart_creator, task_creator
        )

        req_data = {
            "owner_ids": [self.simple_user.id]
        }

        for user in [
            self.org_creator,
            depart_creator,
            task_creator
        ]:
            response = self.auth_post(user, req_data, [self.task.id])
            self.assertEqual(response.status_code, self.status.HTTP_204_NO_CONTENT)
            updated_obj = Task.objects.get(id=self.task.id)
            access_allowed = updated_obj.can_be_accessed_by.all()
            self.assertEqual(len(access_allowed), 1)
            self.assertIn(self.simple_user, access_allowed)
            # reset for next user
            updated_obj.can_be_accessed_by.clear()
    
    def test_user_with_perm_can_change_owners(self):
        user_with_perm, _, perm_obj = self.create_new_permission(self.org)
        perm_obj.add_permissions(CAN_CHANGE_RESSOURCES_OWNERS)

        self.simple_user.can_be_accessed_by.add(user_with_perm)

        req_data = {
            "owner_ids": [self.simple_user.id]
        }

        response = self.auth_post(user_with_perm, req_data, [self.task.id])
        self.assertEqual(response.status_code, self.status.HTTP_204_NO_CONTENT)
        updated_obj = Task.objects.get(id=self.task.id)
        access_allowed = updated_obj.can_be_accessed_by.all()
        self.assertEqual(len(access_allowed), 1)
        self.assertIn(self.simple_user, access_allowed)