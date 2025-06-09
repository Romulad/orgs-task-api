import uuid

from ..base_classe import BaseTestClass
from perms.models import UserPermissions
from app_lib.app_permssions import get_perm_list


class TestRemovePermsFromUserView(BaseTestClass):
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
        - `perms`:
            - this field is required and should include list of string permission to apply to users
            - the field should not be empty
    - test perms are successfully remove from users and we have success response with removed and not found perms
    - test view can handle case with no existed user perm obj without error, and these perm objs don't 
    get created for user without perm obj
    """
    url_name = "remove-perms"

    def setUp(self):
        self.users = [self.create_and_activate_random_user() for _ in range(10)]
        self.user_with_perms = self.users[:5]
        self.added_perms = get_perm_list()[:8]
        self.owner, self.creator, self.org = self.create_new_org()
        for user in self.user_with_perms:
            perm_obj = UserPermissions.objects.create(
                org=self.org,
                user=user,
            )
            perm_obj.save_perms(self.added_perms)
    
    def assert_permissions_obj_len(self, length=0):
        self.assertEqual(
            len(
                UserPermissions.objects.all()
            ), len(self.user_with_perms)
        )

    def test_only_authenticated_user_can_access(self):
        self.evaluate_method_unauthenticated_request(
            self.HTTP_POST,
        )
    
    def tecst_org_validation(self):
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
    
    def test_perm_successfully_removed(self):
        can_access_org_user = self.create_and_activate_random_user()
        self.org.can_be_accessed_by.add(can_access_org_user)

        req_data = {
            "org": self.org.id,
            "user_ids": self.get_ids_from(self.users),
            "perms": self.added_perms
        }

        # ensure users have the permissions
        for user in self.user_with_perms:
            perm_obj = UserPermissions.objects.get(org=self.org, user=user)
            existed_perms = perm_obj.get_perms()
            self.assertEqual(len(existed_perms), len(self.added_perms))
            [self.assertIn(added_perm, existed_perms) for added_perm in self.added_perms]
        
        for user in [
            self.creator,
            self.owner,
            can_access_org_user
        ]:
            response = self.auth_post(user, req_data)
            self.assertEqual(response.status_code, self.status.HTTP_200_OK)
            data = self.loads(response.content)
            removed = data.get("removed")
            not_found = data.get("not_found")
            self.assertIsInstance(removed, list)
            self.assertIsInstance(not_found, list)
            self.assertEqual(len(removed), len(self.added_perms))
            self.assertEqual(len(not_found), 0)
            [self.assertIn(perm, removed) for perm in self.added_perms]
        
        # we still have the same number of perm obj in the db
        self.assert_permissions_obj_len()

        # ensure permissions are remove from users
        for user in self.user_with_perms:
            perm_obj = UserPermissions.objects.get(org=self.org, user=user)
            user_perms = perm_obj.get_perms()
            self.assertEqual(len(user_perms), 0)        
    