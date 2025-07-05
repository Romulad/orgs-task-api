from ...base_classe import BaseTestClass

class TestListRoleView(BaseTestClass):
    """### Flow
    - user need to be authenticated
    - test user without access, simple user, any other user can not get any data
    - test user with access:
        - org owner
        - org creator and creator of the role
        - user with `can_be_accessed_by` permission on both org and role
        - org members
    can get needed role data
    - test response is paginated
    - test we can apply filters, e.g a search through filter
    """
    url_name = "roles-list"

    def setUp(self):
        self.owner_user, self.org_creator, self.org = self.create_new_org()
        self.roles = [self.create_new_role(self.org)[-1] for _ in range(10)]

    def test_only_authenticated_user_can_access(self):
        self.evaluate_method_unauthenticated_request(
            self.HTTP_GET
        )
    
    def test_user_without_access_cant_get_any_ressources(self):
        simple_user = self.create_and_activate_random_user()

        another_owner, another_creator, _ = self.create_new_org()

        depart_creator, depart = self.create_new_depart(self.org)
        can_access_depart_user = self.create_and_activate_random_user()
        depart.can_be_accessed_by.add(can_access_depart_user)

        for user in [
            simple_user,
            another_owner,
            another_creator,
            depart_creator,
            can_access_depart_user
        ]:
            response = self.auth_get(user)
            self.assertEqual(response.status_code, self.status.HTTP_200_OK)
            data = self.loads(response.content).get("results")
            self.assertEqual(len(data), 0)
    
    def test_user_with_access_can_get_data(self):
        can_access_org_user = self.create_and_activate_random_user()
        self.org.can_be_accessed_by.add(can_access_org_user)

        org_member = self.create_and_activate_random_user()
        self.org.members.add(org_member)
        
        role_created_by = self.roles[:5]
        role_creator = self.create_and_activate_random_user()
        can_access_role_user = self.create_and_activate_random_user()

        for role in role_created_by:
            role.can_be_accessed_by.add(can_access_role_user)
            role.created_by = role_creator
            role.save()

        for data in [
            (self.owner_user, self.roles),
            (self.org_creator, self.roles),
            (can_access_org_user, self.roles),
            (org_member, self.roles),
            (role_creator, role_created_by),
            (can_access_role_user, role_created_by)
        ]:
            user, role_data = data
            response = self.auth_get(user)
            self.assertEqual(response.status_code, self.status.HTTP_200_OK)
            data = self.loads(response.content).get("results")
            self.assertEqual(len(data), len(role_data))
            d_ids = [str(obj.id) for obj in role_data]
            for result in data:
                self.assertIn(result["id"], d_ids)
                self.assertIsNotNone(result.get("name"))
                self.assertIsNotNone(result.get("description"))
                self.assertIsInstance(result.get("perms"), list)
                self.assertEqual(result.get("org").get("id"), str(self.org.id))
                self.assertIsNotNone(result.get("created_at"))
    
    def test_data_can_be_filtered(self):
        target_role = self.roles[0]
        target_role.name = "test_role"
        target_role.save()

        response = self.auth_get(self.owner_user, query_params={"name": "test_role"})
        self.assertEqual(response.status_code, self.status.HTTP_200_OK)
        data = self.loads(response.content).get("results")
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0].get("id"), str(target_role.id))
        self.assertEqual(data[0].get("name"), target_role.name)
    
    def test_can_be_filtered_with_search(self):
        target_role = self.roles[0]
        target_role.name = "google_role"
        target_role.save()

        response = self.auth_get(self.owner_user, query_params={"search": "google"})
        self.assertEqual(response.status_code, self.status.HTTP_200_OK)
        data = self.loads(response.content).get("results")
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0].get("id"), str(target_role.id))
        self.assertEqual(data[0].get("name"), target_role.name)