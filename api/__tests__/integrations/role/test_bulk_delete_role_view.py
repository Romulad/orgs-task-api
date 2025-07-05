import uuid

from ...base_classe import BaseTestClass

class TestBulkDeleteRoleView(BaseTestClass):
    """### Flow
    - user need to be authenticated
    - request data need to be validate and include valid ids
    - test user get not found when ressource ids do not exist
    - test when user does not have full access over ressource ids:
        - other user or org user - 404 not found
        - org member only without permission - 403 forbidden
        - any other user existing in the org but without explicit permission - 404 not found
   - test user with access:
        - org owner
        - org creator and creator of the role
        - user with `can_be_accessed_by` permission on both org and role
    can delete roles 
    - test ressources are deleted by marking it as is_delete and success response 204
    - when user make request to delete ressources he has access to and some are not found
    success response should be sent containing what was deleted and what was not found 
    """
    url_name = "roles-bulk-delete"

    def setUp(self):
        self.owner_user, self.org_creator, self.org = self.create_new_org()
        self.roles = [self.create_new_role(self.org)[-1] for _ in range(10)]
        self.Role = self.roles[0].__class__
    
    def assert_role_still_exist(self):
        """Assert ressources still exist """
        self.assertTrue(
            all(
                [self.Role.objects.get(id=role.id) for role in self.roles]
            )
        )
    
    def assert_ressources_deleted(self):
        """
        Soft deletion.
        Ressources are deleted from `objects` and still available on `all_objects`"""
        for role in self.roles:
            with self.assertRaises(self.Role.DoesNotExist):
                self.Role.objects.get(id=role.id)
            self.Role.all_objects.get(id=role.id)
    
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
    
    def test_not_access_allowed_user_cant_bulk_delete_role(self):
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
            response = self.auth_delete(user, {"ids": self.get_ids_from(self.roles)})
            self.assertEqual(response.status_code, self.status.HTTP_404_NOT_FOUND)
            # check response data
            data = self.loads(response.content)
            self.assertIsNotNone(data.get("detail"))
        self.assert_role_still_exist()

    def test_org_member_cant_bulk_delete_role(self):
        org_member = self.create_and_activate_random_user()
        self.org.members.add(org_member)
        response = self.auth_delete(org_member, {"ids": self.get_ids_from(self.roles)})
        self.assertEqual(response.status_code, self.status.HTTP_403_FORBIDDEN)
        # check response data
        data = self.loads(response.content)
        self.assertIsNotNone(data.get("detail"))
        # ressources
        self.assert_role_still_exist()
    
    def test_user_with_access_can_bulk_delete_role(self):
        can_access_org_user = self.create_and_activate_random_user()
        self.org.can_be_accessed_by.add(can_access_org_user)
 
        role_creator = self.create_and_activate_random_user()
        can_access_role_user = self.create_and_activate_random_user()

        for role in self.roles:
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
        for user in users:
            role_ids = self.get_ids_from(self.roles)
            response = self.auth_delete(
                user, {"ids": role_ids}
            )
            self.assertEqual(response.status_code, self.status.HTTP_204_NO_CONTENT)
            # data are deleted
            self.assert_ressources_deleted()
            # reset ressources for the next user
            self.Role.all_objects.filter(id__in=role_ids).update(is_deleted=False)

    def test_delete_data_with_no_found(self):
        ids = self.get_ids_from(self.roles) + [uuid.uuid4()]
        response = self.auth_delete(self.owner_user, {"ids": ids})
        self.assertEqual(response.status_code, self.status.HTTP_200_OK)
        # response data
        data = self.loads(response.content)
        self.assertIsInstance(data.get("deleted"), list)
        self.assertIsInstance(data.get("not_found"), list)
        self.assertEqual(len(data.get("deleted")), len(self.roles))
        self.assertEqual(len(data.get("not_found")), 1)
        # data have been deleted
        self.assert_ressources_deleted()