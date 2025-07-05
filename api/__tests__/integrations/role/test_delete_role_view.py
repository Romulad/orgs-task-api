import uuid

from ...base_classe import BaseTestClass

class TestDeleteRoleView(BaseTestClass):
    """### Flow
    - user need to be authenticated
    - test user get not found when ressource doesn't exist
    - test permission:
        - other user or org user - 404 not found
        - org member only without permission - 403 forbidden
        - any other user existing in the org but without explicit permission - 404 not found
    - test user with access:
        - org owner
        - org creator and creator of the role
        - user with `can_be_accessed_by` permission on both org and role
    can delete role
    - test role is deleted with success response and doesn't exist on objects anymore but available 
    on all_objects with it is_delete set to true
    """
    url_name = "roles-detail"

    def test_only_authenticated_user_can_access(self):
        self.evaluate_method_unauthenticated_request(
            self.HTTP_DELETE, ['fake_id']
        )

    def setUp(self):
        self.owner_user, self.org_creator, self.org = self.create_new_org()
        self.role_creator, self.target_role = self.create_new_role(self.org)
        self.Role = self.target_role.__class__
    
    def assert_data_still_exists(self):
        # ensure the data still exists
        self.assertIsNotNone(
            self.Role.objects.get(id=self.target_role.id)
        )

    def test_not_found_ressource(self):
        response = self.auth_delete(self.owner_user, {}, [uuid.uuid4()])
        self.assertEqual(response.status_code, self.status.HTTP_404_NOT_FOUND)
        self.assertIsNotNone(response.data.get("detail", None))
    
    def test_not_access_allowed_user_cant_delete_role(self):
        simple_user = self.create_and_activate_random_user()
        another_owner, another_creator, _ = self.create_new_org()

        depart_creator, depart = self.create_new_depart(self.org)
        can_access_depart_user = self.create_and_activate_random_user()
        depart.can_be_accessed_by.add(can_access_depart_user)

        another_role_creator, _ = self.create_new_role(self.org)

        for user in [
            simple_user,
            another_owner,
            another_creator,
            depart_creator,
            can_access_depart_user,
            another_role_creator
        ]:
            response = self.auth_delete(user, {}, [self.target_role.id])
            self.assertEqual(response.status_code, self.status.HTTP_404_NOT_FOUND)
            data = self.loads(response.content)
            self.assertIsNotNone(data.get("detail"))
        self.assert_data_still_exists()

    def test_org_member_without_permission_cant_delete_role(self):
        org_member = self.create_and_activate_random_user()
        self.org.members.add(org_member)

        response = self.auth_delete(org_member, {}, [self.target_role.id])
        self.assertEqual(response.status_code, self.status.HTTP_403_FORBIDDEN)
        data = self.loads(response.content)
        self.assertIsNotNone(data.get("detail"))
        self.assert_data_still_exists()
    
    def test_user_with_access_can_delete_roles(self):
        roles = [self.create_new_role(self.org)[-1] for _ in range(10)]

        can_access_org_user = self.create_and_activate_random_user()
        self.org.can_be_accessed_by.add(can_access_org_user)
 
        role_creator = self.create_and_activate_random_user()
        can_access_role_user = self.create_and_activate_random_user()

        for role in roles:
            role.created_by = role_creator
            role.save()
            role.can_be_accessed_by.add(can_access_role_user)

        users = [
            self.owner_user,
            self.org_creator,
            can_access_org_user,
            role_creator,
            can_access_role_user
        ]

        for index, user in enumerate(users):
            target_role = roles[index]
            response = self.auth_delete(user, {}, [target_role.id])
            self.assertEqual(response.status_code, self.status.HTTP_204_NO_CONTENT)
            # role has been deleted
            with self.assertRaises(self.Role.DoesNotExist):
                self.Role.objects.get(id=target_role.id)
            # role still exist on all_objects
            self.assertIsNotNone(
                self.Role.all_objects.get(id=target_role.id)
            )
        