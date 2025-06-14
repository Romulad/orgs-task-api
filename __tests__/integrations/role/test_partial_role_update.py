import uuid

from ..base_classe import BaseTestClass
from django.forms.models import model_to_dict

from app_lib.app_permssions import get_perm_list

class TestPartialUpdateRoleView(BaseTestClass):
    """### Flow
    - user need to be authenticated
    - test user get not found when ressource does not exist
    - test not access allowed user:
        - other user or other org user - 404 not found
        - org member only without permission - 403 forbidden
        - any other user existing in the org but without explicit permission - 404 not found
    should not be able to update data
    - test data validation: (instance already exists, field can be sent in any combination)
        - name if specified:
            - should not be empty
            - if name is same as the current instance name, no validation need to take place
            - if name is different:
                - should be validate against the role org to be unique
                - if new org is included in req data then the name should be validate against the new org
        - org if specified:
            - org id should be a valid id
            - if org id same as the current role instance org id, no validation needed
            - if different:
                - user making the request should has access to the org
                - if `name`, not in req data, intance role name should be validate against the new org
                to avoid same role with same name in the new org
                - if `users`, not in request data, ensure the new org owner has full access over 
                existing role users
        - users if specified:
            - field should contain a valid value
            - user ids should be valid
            - if org in request data, org specified owner should have a full access over users
            - otherwise existing role org owner should have a full access over users
    - test user with access:
        - org owner
        - org creator and role creator
        - user in `can_be_accessed_by` on both org and role
    can update role data successfully with permission list containing invalid or valid permissions
    - test response data is valid and perms set
    - test user is automatically added as member when not org member yet
    """
    url_name = "roles-detail"

    def setUp(self):
        self.owner_user, self.org_creator, self.org = self.create_new_org()
        self.role_creator, self.target_role = self.create_new_role(self.org)
        self.roles = [self.create_new_role(self.org)[-1] for _ in range(10)]

    def test_only_authenticated_user_can_access(self):
        self.evaluate_method_unauthenticated_request(
            self.HTTP_PATCH, ["fake-role-id"]
        )
    
    def test_not_found_when_role_does_not_exist(self):
        response = self.auth_patch(self.owner_user, {}, [uuid.uuid4()])
        self.assertEqual(response.status_code, self.status.HTTP_404_NOT_FOUND)
        data = self.loads(response.content)
        self.assertIsNotNone(data.get("detail"))
    
    def test_not_access_allowed_user_cant_update_role(self):
        simple_user = self.create_and_activate_random_user()
        another_owner, another_creator, _ = self.create_new_org()

        depart_creator, depart = self.create_new_depart(self.org)
        can_access_depart_user = self.create_and_activate_random_user()
        depart.can_be_accessed_by.add(can_access_depart_user)

        req_data = {"name": "new_role_name"}

        for user in [
            simple_user,
            another_owner,
            another_creator,
            depart_creator,
            can_access_depart_user
        ]:
            response = self.auth_patch(user, req_data, [self.target_role.id])
            self.assertEqual(response.status_code, self.status.HTTP_404_NOT_FOUND)
            data = self.loads(response.content)
            self.assertIsNotNone(data.get("detail"))
        with self.assertRaises(self.target_role.__class__.DoesNotExist):
            self.target_role.__class__.objects.get(name=req_data["name"])
    
    def test_org_member_without_permission_cant_update_role(self):
        org_member = self.create_and_activate_random_user()
        self.org.members.add(org_member)

        req_data = {"name": "new_role_name"}

        response = self.auth_patch(org_member, req_data, [self.target_role.id])
        self.assertEqual(response.status_code, self.status.HTTP_403_FORBIDDEN)
        data = self.loads(response.content)
        self.assertIsNotNone(data.get("detail"))
        with self.assertRaises(self.target_role.__class__.DoesNotExist):
            self.target_role.__class__.objects.get(name=req_data["name"])
        
    def test_name_validation(self):
        self.new_owner, _, org = self.create_new_org()
        _, new_role = self.create_new_role(org, "role_in_new_org_name")
        org.can_be_accessed_by.add(self.owner_user)

        test_data = [
            {
                "name": ""
            },
            {
                "name": self.roles[0].name
            },
            {
                "name": new_role.name,
                "org": org.id
            },
        ]
        for req_data in test_data:
            response = self.auth_patch(self.owner_user, req_data, [self.target_role.id])
            self.assertEqual(response.status_code, self.status.HTTP_400_BAD_REQUEST)
            errors = self.loads(response.content).get("name")
            self.assertIsInstance(errors, list)

        old_name = self.target_role.name
        self.target_role.refresh_from_db()
        self.assertEqual(old_name, self.target_role.name)
        self.assertEqual(self.target_role.org.id, self.org.id)

    def test_same_name_validation(self):
        response = self.auth_patch(
            self.owner_user, 
            {"name": self.target_role.name}, 
            [self.target_role.id]
        )
        self.assertEqual(response.status_code, self.status.HTTP_200_OK)
        data = self.loads(response.content)
        self.assertEqual(data.get("org"), str(self.org.id))
    
    def test_org_validation(self):
        new_org_owner, _, org = self.create_new_org()
        self.create_new_role(org, self.target_role.name)
        self.org.can_be_accessed_by.add(new_org_owner)

        test_data = [
            {
                "org": uuid.uuid4()
            },
            {
                "org": org.id
            },
            {
                "org": org.id,
                "current_user": new_org_owner
            }
        ]
        for req_data in test_data:
            user = req_data.pop("current_user", self.owner_user)
            response = self.auth_patch(user, req_data, [self.target_role.id])
            self.assertEqual(response.status_code, self.status.HTTP_400_BAD_REQUEST)
            errors = self.loads(response.content).get("org")
            self.assertIsInstance(errors, list)

        self.target_role.refresh_from_db()
        self.assertEqual(self.target_role.org.id, self.org.id)
    
    def test_new_org_validation_against_existing_role_users(self):
        _, _, new_org = self.create_new_org()
        new_org.can_be_accessed_by.add(self.owner_user)

        # the role has users already that the existing role org owner has access over
        users = [self.create_and_activate_random_user() for _ in range(4)]
        [user.can_be_accessed_by.add(self.owner_user) for user in users]
        self.target_role.users.set(users)

        # this request data simulate the fact that the new org owner does not have access over
        # the existing role users
        req_data = {
            "org": new_org.id
        }

        response = self.auth_patch(self.owner_user, req_data, [self.target_role.id])
        self.assertEqual(response.status_code, self.status.HTTP_400_BAD_REQUEST)
        errors = self.loads(response.content).get("org")
        self.assertIsInstance(errors, list)
        self.target_role.refresh_from_db()
        self.assertEqual(self.target_role.org.id, self.org.id)
    
    def test_users_validation(self):
        _, _, new_org = self.create_new_org()
        new_org.can_be_accessed_by.add(self.owner_user)

        users = [
            self.create_and_activate_random_user(), self.create_and_activate_random_user()
        ]
        [user.can_be_accessed_by.add(self.owner_user) for user in users]

        test_data = [
            {
                "users": ""
            },
            {
                "users": [uuid.uuid4()]
            },
            {
                "users": [self.create_and_activate_random_user().id]
            },
            {
                "users": self.get_ids_from(users),
                "org": new_org.id
            },
        ]

        for req_data in test_data:
            response = self.auth_patch(self.owner_user, req_data, [self.target_role.id])
            self.assertEqual(response.status_code, self.status.HTTP_400_BAD_REQUEST)
            errors = self.loads(response.content).get("users")
            self.assertIsInstance(errors, list)
        self.target_role.refresh_from_db()
        self.assertEqual(self.target_role.org.id, self.org.id)
        self.assertEqual(len(self.target_role.users.all()), 0)
    
    def test_user_with_access_can_update_role(self):
        can_access_org_user = self.create_and_activate_random_user()
        self.org.can_be_accessed_by.add(can_access_org_user)

        org_member_with_perm = self.create_and_activate_random_user()
        self.org.members.add(org_member_with_perm)
        self.org.can_be_accessed_by.add(org_member_with_perm)
 
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
            org_member_with_perm,
            role_creator,
            can_access_role_user
        ]

        real_perms = get_perm_list()[:5]
        req_data = {
            "org": self.org.id,
            "perms": real_perms + ["fake_perm_", "random_PERM"]
        }

        for index, user in enumerate(users):
            target_role = self.roles[index]
            response = self.auth_patch(user, req_data, [target_role.id])
            self.assertEqual(response.status_code, self.status.HTTP_200_OK)
            data = self.loads(response.content)
            self.assertEqual(data.get("id"), str(target_role.id))
            self.assertEqual(data.get("name"), target_role.name)
            self.assertEqual(data.get("org"), str(self.org.id))
            self.assertEqual(data.get("description"), target_role.description)
            self.assertIsInstance(data.get("perms"), list)
            self.assertEqual(len(real_perms), len(data.get("perms")))
            self.assertIsNotNone(data.get("created_at"))
            self.assertIsInstance(data.get("can_be_accessed_by"), list)
            # role has been updated
            updated = target_role.__class__.objects.get(id=target_role.id)

            role_perms = updated.get_perms()
            self.assertEqual(len(role_perms), len(real_perms))
            for perm in real_perms:
                self.assertIn(perm, role_perms)
    
    def test_users_are_added_to_org_when_not_member_yet(self):
        users = [self.create_and_activate_random_user() for _ in range(4)]
        [user.can_be_accessed_by.add(self.owner_user) for user in users]

        req_data = {
            "users": self.get_ids_from(users),
        }
        response = self.auth_patch(self.owner_user, req_data, [self.target_role.id])
        self.assertEqual(response.status_code, self.status.HTTP_200_OK)
        data = self.loads(response.content)
        self.assertIsInstance(data.get("users"), list)
        self.assertEqual(len(data.get("users")), len(users))
        # Role has been updated with users
        self.target_role.refresh_from_db()
        [self.assertIn(user, self.target_role.users.all()) for user in users]
        # org members have been updated
        self.org.refresh_from_db()
        members = self.org.members.all()
        self.assertEqual(len(members), len(users))
        [self.assertIn(new_member, members) for new_member in users]

    
    