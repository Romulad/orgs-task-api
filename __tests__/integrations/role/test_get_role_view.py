import uuid

from ...base_classe import BaseTestClass

class TestGetRoleView(BaseTestClass):
    """### Flow
    - user need to be authenticated
    - user get not when ressource does not exist
    - test other user or user in the org without access can not get ressource and get not found error
    - test allow user :
        - org owner
        - org creator and creator of the role
        - user with `can_be_accessed_by` permission on both org and role
        - org members
    can get data successfully
    """
    url_name = "roles-detail"

    def setUp(self):
        self.owner, self.creator, self.org = self.create_new_org()
        self.roles = [self.create_new_role(self.org)[-1] for _ in range(10)]

    def test_only_authenticated_user_can_access(self):
        self.evaluate_method_unauthenticated_request(
            self.HTTP_GET, ["fake-role-id"]
        )
    
    def test_get_role_not_found(self):
        response = self.auth_get(self.owner, [uuid.uuid4()])
        self.assertEqual(response.status_code, self.status.HTTP_404_NOT_FOUND)
        data = self.loads(response.content).get("detail")
        self.assertIsNotNone(data)
    
    def test_no_allowed_user_can_not_get_role(self):
        simple_user = self.create_and_activate_random_user()
        org_owner, _, _ = self.create_new_org()
        self.create_new_role(self.org)

        target_role = self.roles[0]

        for user in [simple_user, org_owner]:
            response = self.auth_get(user, [target_role.id])
            self.assertEqual(response.status_code, self.status.HTTP_404_NOT_FOUND)
            data = self.loads(response.content).get("detail")
            self.assertIsNotNone(data)
    
    def test_allowed_user_can_get_role(self):
        can_access_org_user = self.create_and_activate_random_user()
        self.org.can_be_accessed_by.add(can_access_org_user)

        org_member = self.create_and_activate_random_user()
        self.org.members.add(org_member)

        role_creator = self.create_and_activate_random_user()
        can_access_role_user = self.create_and_activate_random_user()

        for role in self.roles:
            role.can_be_accessed_by.add(can_access_role_user)
            role.created_by = role_creator
            role.save()

        for index, user in enumerate([
            self.owner, 
            self.creator, 
            can_access_org_user, 
            org_member,
            role_creator, 
            can_access_role_user
        ]):
            target_role = self.roles[index]
            response = self.auth_get(user, [target_role.id])
            self.assertEqual(response.status_code, self.status.HTTP_200_OK)
            data = self.loads(response.content)
            self.assertEqual(data.get("id"), str(target_role.id))
            self.assertEqual(data.get("org").get("id"), str(self.org.id))
            self.assertEqual(data.get("name"), target_role.name)
            self.assertEqual(data.get("description"), target_role.description)
            self.assertIsInstance(data.get("perms"), list)
            self.assertIsInstance(data.get("can_be_accessed_by"), list)
            self.assertIsNotNone(data.get("created_at"))

