import uuid

from ...base_classe import BaseTestClass
from perms.models import UserPermissions
from app_lib.app_permssions import get_perm_list


class TestAddPermsToUserView(BaseTestClass):
    """### Flow
    - user need to be authenticated
    - test data validation:
        - `org`:
            - this field is required and should be include - 400 error
            - the org should exists - 400 error
            - the user sending the request should have a full access over the org
        - `user_ids`:
            - this field is a list, is required and can not be empty, 400 error
            - all user ids should be a valid ids, - 400 error
            - the org owner should have a full access over the users - 400 error
        - `perms`:
            - this field is required and should include list of string permission to apply to users
            - the field should not be empty
            - other user than org creator can not add creator level perm to someone
            - only org creator can add creator level permission to users
    - test perms are successfully apply to users and we have success response with added and not found perms
    - test users is automatically add as member of the org when no member already
    - test validate perm string is add to user perm list when invalid perm and valid perm are sent and 
    success response is send including added and not found perms
    - test after multiple request with same user and org, permission model is still one for user and 
    org together
    """
    url_name = "add-perms"

    def setUp(self):
        self.users = [self.create_and_activate_random_user() for _ in range(10)]
        self.owner, self.creator, self.org = self.create_new_org()
        [user.can_be_accessed_by.add(self.owner) for user in self.users]
    
    def assert_permissions_obj_len(self, length=0):
        self.assertEqual(
            len(
                UserPermissions.objects.all()
            ), length
        )

    def test_only_authenticated_user_can_access(self):
        self.evaluate_method_unauthenticated_request(
            self.HTTP_POST,
        )
    
    def test_org_validation(self):
        test_data = [
            {
                "user_ids": self.get_ids_from(self.users),
                "perms": ["some_permissions"]
            },
            {
                "org": uuid.uuid4(),
                "user_ids": self.get_ids_from(self.users),
                "perms": ["some_permissions"]
            },
            {
                "org": self.org.id,
                "user_ids": self.get_ids_from(self.users),
                "perms": ["some_permissions"],
                "current_user": self.create_and_activate_random_user()
            }
        ]

        for req_data in test_data:
            user = req_data.pop('current_user', self.owner)
            response = self.auth_post(user, req_data)
            self.assertEqual(response.status_code, self.status.HTTP_400_BAD_REQUEST)
            errors = self.loads(response.content).get("org")
            self.assertIsInstance(errors, list)
        self.assert_permissions_obj_len()
    
    def test_user_ids_validation(self):
        test_data = [
            {
                "org": self.org.id,
                "perms": ["some_permissions"]
            },
            {
                "org": self.org.id,
                "user_ids": uuid.uuid4(),
                "perms": ["some_permissions"]
            },
            {
                "org": self.org.id,
                "user_ids": [],
                "perms": ["some_permissions"]
            },
            {
                "org": self.org.id,
                "user_ids": [uuid.uuid4()],
                "perms": ["some_permissions"]
            },
            {
                "org": self.org.id,
                "user_ids": self.get_ids_from([
                    self.create_and_activate_random_user()
                    for _ in range(3)
                ]),
                "perms": ["some_permissions"]
            }
        ]

        for req_data in test_data:
            response = self.auth_post(self.owner, req_data)
            self.assertEqual(response.status_code, self.status.HTTP_400_BAD_REQUEST)
            errors = self.loads(response.content).get("user_ids")
            self.assertIsInstance(errors, list)
        self.assert_permissions_obj_len()
    
    def test_perms_validation(self):
        test_data = [
            {
                "org": self.org.id,
                "user_ids": self.get_ids_from(self.users),
            },
            {
                "org": self.org.id,
                "user_ids": self.get_ids_from(self.users),
                "perms": []
            }
        ]

        for req_data in test_data:
            response = self.auth_post(self.owner, req_data)
            self.assertEqual(response.status_code, self.status.HTTP_400_BAD_REQUEST)
            errors = self.loads(response.content).get("perms")
            self.assertIsInstance(errors, list)
        self.assert_permissions_obj_len()

    def test_no_creator_cant_add_creator_perm_to_user(self):
        can_access_org_user = self.create_and_activate_random_user()
        self.org.can_be_accessed_by.add(can_access_org_user)

        creator_granted_perms = get_perm_list()
        req_data = {
            "org": self.org.id,
            "user_ids": self.get_ids_from(self.users),
            "perms": creator_granted_perms
        }

        for user in [
            self.owner,
            can_access_org_user
        ]:
            response = self.auth_post(user, req_data)
            self.assertEqual(response.status_code, self.status.HTTP_400_BAD_REQUEST)
            errors = self.loads(response.content).get("perms")
            self.assertIsInstance(errors, list)
        self.assert_permissions_obj_len()

    def test_creator_can_add_any_perm_to_user(self):
        all_perms = get_perm_list()
        req_data = {
            "org": self.org.id,
            "user_ids": self.get_ids_from(self.users),
            "perms": all_perms
        }
        response = self.auth_post(self.creator, req_data)
        self.assertEqual(response.status_code, self.status.HTTP_200_OK)
        self.assert_permissions_obj_len(len(self.users))
    
    def test_perms_with_invalid_perm_value_should_not_trigger_error(self):
        req_data = {
            "org": self.org.id,
            "user_ids": self.get_ids_from(self.users),
            "perms": ["some_permissions"]
        }
        response = self.auth_post(self.owner, req_data)
        self.assertEqual(response.status_code, self.status.HTTP_200_OK)
        data = self.loads(response.content).get("not_found")
        self.assertIsInstance(data, list)
        self.assertListEqual(["some_permissions"], data)
        self.assert_permissions_obj_len()
    
    def test_sucessfully_add_perm_to_users(self):
        can_access_user = self.create_and_activate_random_user()
        self.org.can_be_accessed_by.add(can_access_user)

        perms = get_perm_list(default_only=True)[:8]
        req_data = {
            "org": self.org.id,
            "user_ids": self.get_ids_from(self.users),
            "perms": perms
        }

        for user in [
            self.owner,
            self.creator,
            can_access_user
        ]:
            response = self.auth_post(user, req_data)
            self.assertEqual(response.status_code, self.status.HTTP_200_OK)
            data = self.loads(response.content)
            found = data.get("added")
            not_found = data.get("not_found")
            self.assertIsInstance(found, list)
            self.assertIsInstance(not_found, list)
            self.assertEqual(len(found), len(perms))
            self.assertEqual(len(not_found), 0)
            [self.assertIn(perm, found) for perm in perms]

        # the same permission model is use for the same user    
        self.assert_permissions_obj_len(len(self.users))

        # permissions successfully added to user
        for user in self.users:
            user_perm = UserPermissions.objects.get(org=self.org, user=user)
            user_str_perms = user_perm.get_perms()
            self.assertEqual(len(user_str_perms), len(perms))
            [self.assertIn(perm, user_str_perms) for perm in perms]
        
        # org members should be updated to include the users
        self.org.refresh_from_db(fields=["members"])
        members = self.org.members.all()
        self.assertEqual(len(members), len(self.users))
        [self.assertIn(user, members) for user in self.users]
    
    def test_successfully_add_perm_with_invalid_perm(self):
        perms = get_perm_list(default_only=True)[:8] 
        wrong_perms = ["somePermission", "NOTFOUND_permission"]
        all_perms = perms + wrong_perms
        req_data = {
            "org": self.org.id,
            "user_ids": self.get_ids_from(self.users),
            "perms": all_perms
        }

        response = self.auth_post(self.owner, req_data)
        self.assertEqual(response.status_code, self.status.HTTP_200_OK)
        data = self.loads(response.content)
        found = data.get("added")
        not_found = data.get("not_found")
        self.assertIsInstance(found, list)
        self.assertIsInstance(not_found, list)
        self.assertEqual(len(found), len(perms))
        self.assertEqual(len(not_found), len(wrong_perms))
        [self.assertIn(perm, found) for perm in perms]
        [self.assertIn(perm.lower(), not_found) for perm in wrong_perms]

        # right permissions successfully added to user
        for user in self.users:
            user_perm = UserPermissions.objects.get(org=self.org, user=user)
            user_str_perms = user_perm.get_perms()
            self.assertEqual(len(user_str_perms), len(perms))
            [self.assertIn(perm, user_str_perms) for perm in perms]