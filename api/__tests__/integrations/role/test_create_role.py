import uuid

from ...base_classe import BaseTestClass
from perms.models import Role
from app_lib.app_permssions import get_perm_list


class TestCreateRoleView(BaseTestClass):
    """### Flow
    - user need to be authenticated
    - test data validation:
        - name:
            - field is required
            - should a valid name
            - role name should be unique within the org
        - org:
            - field is required
            - org id should be a valid id
            - user making the request should have permission to act on the org
        - perms:
            - field is optional and can be empty list
            - if exist:
                - no org creator user can not create role with creator level permission
                - only creator can create role with creator level permission
        - users if specified:
            - should be a valid value
            - user ids should be valid user ids
            - org owner should have a full access over specified user
    - test org `owner`, `creator` or `can_be_accessed_by` can create role within 
    the org successfully and if `perms` specified, valid perm value are added to the role 
    successfully and `created_by` is set. 
    - test users are added to org as members if not yet
    """
    url_name = "roles-list"

    def setUp(self):
        self.owner, self.creator, self.org = self.create_new_org()
    
    def assert_no_more_role_created(self, should_exist_count=0):
        self.assertEqual(
            len(
                Role.objects.all()
            ),
            should_exist_count
        )

    def test_only_authenticated_user_can_access(self):
        self.evaluate_method_unauthenticated_request(
            self.HTTP_POST
        )
    
    def test_name_field_validation(self):
        _, role = self.create_new_role(self.org)
        test_data = [
            {
                "org": self.org.id
            },
            {
                "org": self.org.id,
                "name": "",
            },
            {
                "org": self.org.id,
                "name": role.name,
            }
        ]
        for req_data in test_data:
            response = self.auth_post(self.owner, req_data)
            self.assertEqual(response.status_code, self.status.HTTP_400_BAD_REQUEST)
            errors = self.loads(response.content).get("name")
            self.assertIsInstance(errors, list)
        self.assert_no_more_role_created(1)
    
    def test_org_validation(self):
        test_data = [
            {
                "name": "Manager"
            },
            {
                "name": "Manager",
                "org": uuid.uuid4()
            },
            {
                "name": "Manager",
                "org": self.org.id,
                'current_user': self.create_and_activate_random_user()
            }
        ]
        for req_data in test_data:
            user = req_data.pop("current_user", self.owner)
            response = self.auth_post(user, req_data)
            self.assertEqual(response.status_code, self.status.HTTP_400_BAD_REQUEST)
            errors = self.loads(response.content).get("org")
            self.assertIsInstance(errors, list)
        self.assert_no_more_role_created(0)
    
    def test_users_validation(self):
        test_data = test_data = [
            {
                "name": "Manager",
                "org": self.org.id,
                "users": "",
            },
            {
                "name": "Manager",
                "org": self.org.id,
                "users": [uuid.uuid4()],
            },
            {
                "name": "Manager",
                "org": self.org.id,
                "users": [self.create_and_activate_random_user().id],
            },
        ]

        for req_data in test_data:
            response = self.auth_post(self.creator, req_data)
            self.assertEqual(response.status_code, self.status.HTTP_400_BAD_REQUEST)
            errors = self.loads(response.content).get("users")
            self.assertIsInstance(errors, list)
        self.assert_no_more_role_created(0)

    def test_no_creator_can_not_create_role_with_creator_level_perm(self):
        creator_granted_perms = get_perm_list()

        can_access_org_user = self.create_and_activate_random_user()
        self.org.can_be_accessed_by.add(can_access_org_user)

        req_data = {
            "name": "Manager",
            "org": self.org.id,
            "perms": creator_granted_perms
        }

        for user in [
            can_access_org_user,
            self.owner,
        ]:
            response = self.auth_post(user, req_data)
            self.assertEqual(response.status_code, self.status.HTTP_400_BAD_REQUEST)
            errors = self.loads(response.content).get("perms")
            self.assertIsInstance(errors, list)
        self.assert_no_more_role_created(0)

    def test_creator_can_create_role_creator_level_perm(self):
        creator_granted_perms = get_perm_list(creator_only=True)[:5]

        req_data = {
            "name": "Manager",
            "org": self.org.id,
            "perms": creator_granted_perms
        }
        response = self.auth_post(self.creator, req_data)
        self.assertEqual(response.status_code, self.status.HTTP_201_CREATED)
        self.assert_no_more_role_created(1)

    def test_successfull_role_creation(self):
        real_perm = get_perm_list(default_only=True)[:5]
        role_perms = real_perm + ["fake_perm_", "random_PERM"]

        can_access_org_user = self.create_and_activate_random_user()
        self.org.can_be_accessed_by.add(can_access_org_user)

        perm_was_included = False
        for user in [
            can_access_org_user,
            self.owner,
            self.creator
        ]:
            req_data = {
                "name": user.email,
                "org": self.org.id
            }
            if not perm_was_included:
                req_data["perms"] = role_perms
            response = self.auth_post(user, req_data)
            self.assertEqual(response.status_code, self.status.HTTP_201_CREATED)
            data = self.loads(response.content)
            self.assertEqual(data.get("name"), user.email)
            self.assertEqual(data.get("org"), str(self.org.id))
            self.assertIsInstance(data.get("perms"), list)
            self.assertIsNotNone(data.get("description", None))
            self.assertIsInstance(data.get("can_be_accessed_by"), list)
            self.assertIsInstance(data.get("users"), list)
            # role has been created with created_by set
            created = Role.objects.get(name=user.email, org=self.org, created_by=user)
            if req_data.get("perms"):
                role_perms = created.get_perms()
                self.assertEqual(len(role_perms), len(real_perm))
                [self.assertIn(perm, role_perms) for perm in real_perm]                
            perm_was_included = not perm_was_included
    
    def test_users_are_added_to_org_when_not_member_yet(self):
        users = [self.create_and_activate_random_user() for _ in range(4)]
        [user.can_be_accessed_by.add(self.owner) for user in users]

        req_data = {
            "name": "Manager",
            "org": self.org.id,
            "users": self.get_ids_from(users)
        }
        response = self.auth_post(self.owner, req_data)
        self.assertEqual(response.status_code, self.status.HTTP_201_CREATED)
        data = self.loads(response.content)
        self.assertIsInstance(data.get("users"), list)
        self.assertEqual(len(data.get("users")), len(users))
        # Role has been created with users
        assert len(Role.objects.filter(name="Manager", users__in=users).distinct()) == 1
        # org members have been updated
        self.org.refresh_from_db()
        members = self.org.members.all()
        self.assertEqual(len(members), len(users))
        [self.assertIn(new_member, members) for new_member in users]