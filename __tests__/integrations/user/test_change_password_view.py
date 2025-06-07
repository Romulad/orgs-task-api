import uuid

from ..base_classe import BaseTestClass
from user.models import AppUser as User

class TestChangeUserPasswordView(BaseTestClass):
    """### Flow
    - user need to be authenticated
    - user get not found when obj does not exist
    - other user can't update password only creator or access allowed user can or 404
    - test all field required are include (password, new_password, confirm_new_password)
    - if it the user itself:
        - test new_password validation (include user cant use existing password)
        - test confirm_new_password validation
        - test password is correct compare to the existing password
        - test user can update password and it properly set in the db
    - if it is an owner or access allow user:
        - test new_password validation, including the same password cant be set for the target user
        - test confirm_new_password validation
        - test owner password is correct compare to the existing password (owner itself)
        - test owner can update user password and it properly set in the db
    """
    url_name = "users-change-password"
    user_data_list = [
        {
            "email": "test@somedoa.com",
            "password": "validPaasword1_"
        },
        {
            "email": "test1@somedoa.com",
            "password": "validPaasword1_"
        },
        {
            "email": "test2@somedoa.com",
            "password": "validPaasword1_"
        }
    ]

    def setUp(self):
        self.owner_user = self.create_and_active_user(
            email="owner_user@noway.come", password="testpassword"
        )
        data_list = [*self.user_data_list]
        for data in data_list:
            data["created_by"] = self.owner_user
        self.users = [User.objects.create_user(**data) for data in data_list]
    
    def assert_user_password_same(self, user_id, password=None):
        user_obj = User.objects.get(id=user_id)
        self.assertTrue(
            user_obj.check_password(
                "validPaasword1_" if password is None else password
            )
        )

    def test_only_authenticated_user_can_access(self):
        self.evaluate_method_unauthenticated_request(
            self.HTTP_POST, ["fake-id"]
        )
    
    def test_not_found_user(self):
        response = self.auth_post(self.owner_user, {}, [uuid.uuid4()])
        self.assertEqual(response.status_code, self.status.HTTP_404_NOT_FOUND)
        self.assertIsNotNone(response.data.get("detail", None))
    
    def test_other_cant_update_data(self):
        other_user = self.create_and_active_user(email="other_user@gmaild.com")
        response = self.auth_post(
            other_user,
            {},
            [self.users[0].id]
        )
        self.assertEqual(response.status_code, self.status.HTTP_404_NOT_FOUND)
        self.assertIsNotNone(response.data.get("detail", None))
    
    def test_all_required_fields_are_present(self):
        target_user = self.users[0]
        req_data = {
            "password": "old_password",
            "new_password": "new_password"
        }
        response = self.auth_post(
            self.owner_user, req_data, [target_user.id]
        )
        self.assertEqual(response.status_code, self.status.HTTP_400_BAD_REQUEST)
        errors = self.loads(response.content).get("confirm_new_password")
        self.assertIsInstance(errors, list)
        # password didnt change
        user_obj = User.objects.get(id=target_user.id)
        self.assertTrue(user_obj.check_password("validPaasword1_"))
    
    def test_new_password_validation(self):
        simple_user = self.create_and_active_user(email="simple_user@gmail.comdd")
        target_user = self.users[0]
        target_user.can_be_accessed_by.add(simple_user)

        req_data = {
            "password": "new_password",
            "confirm_new_password": "confirm_new_password"
        }

        test_datas = [
            {
                "user": target_user,
                "req_data": {
                    **req_data, "new_password": "justpassword"
                }
            },
            {
                "user": self.owner_user,
                "req_data": {
                    **req_data, "new_password": "justpassword"
                }
            },
            {
                "user": target_user,
                "req_data": {
                    **req_data, "new_password": "just@1password"
                }
            },
            {
                "user": simple_user,
                "req_data": {
                    **req_data, "new_password": "Just@password"
                }
            },
            {
                "user": target_user,
                "req_data": {
                    **req_data, "new_password": "validPaasword1_"
                }
            },
            {
                "user": self.owner_user,
                "req_data": {
                    **req_data, "new_password": "validPaasword1_"
                }
            },
        ]
        for test_data in test_datas:
            current_user = test_data.get("user")
            error_data = test_data["req_data"]
            response = self.auth_post(current_user, error_data, [target_user.id])
            self.assertEqual(response.status_code, self.status.HTTP_400_BAD_REQUEST)
            errors = self.loads(response.content).get("new_password")
            self.assertIsInstance(errors, list)
            # 
            self.assert_user_password_same(target_user.id)
    
    def test_confirm_new_password_validation(self):
        target_user = self.users[0]

        req_data = {
            "new_password": "justPassword1@",
            "confirm_new_password": "confirm_new_password",
            "password": "validPaasword1_",
        }

        response = self.auth_post(target_user, req_data, [target_user.id])
        self.assertEqual(response.status_code, self.status.HTTP_400_BAD_REQUEST)
        errors = self.loads(response.content).get("confirm_new_password")
        self.assertIsInstance(errors, list)
        # 
        self.assert_user_password_same(target_user.id)
    
    def test_current_user_password_validation(self):
        simple_user = self.create_and_active_user(email="simple_user@gmail.comdd")
        target_user = self.users[0]
        target_user.can_be_accessed_by.add(simple_user)

        req_data = {
            "new_password": "justPassword1@",
            "confirm_new_password": "justPassword1@",
        }

        test_datas = [
            {
                "user": target_user,
                "req_data": {
                    **req_data, "password": "invalidapassw"
                }
            },
            {
                "user": self.owner_user,
                "req_data": {
                    **req_data, "password": "validPaasword1_"
                }
            },
            {
                "user": simple_user,
                "req_data": {
                    **req_data, "password": "validPaasword1_"
                }
            }
        ]
        for test_data in test_datas:
            current_user = test_data.get("user")
            error_data = test_data["req_data"]
            response = self.auth_post(current_user, error_data, [target_user.id])
            self.assertEqual(response.status_code, self.status.HTTP_400_BAD_REQUEST)
            errors = self.loads(response.content).get("password")
            self.assertIsInstance(errors, list)
            # 
            self.assert_user_password_same(target_user.id)

    def test_owners_can_change_user_password(self):
        simple_user = self.create_and_active_user(
            email="simple_user@gmail.comdd", password="testpassword"
        )
        target_user = self.users[0]
        target_user.can_be_accessed_by.add(simple_user)

        req_data = {
            "new_password": "justPassword1@",
            "confirm_new_password": "justPassword1@",
            "password": "testpassword",
        }

        test_datas = [
            {
                "user": simple_user,
                "target_user": target_user
            },
            {
                "user": self.owner_user,
                "target_user": self.users[1]
            }
        ]

        for test_data in test_datas:
            current_target_user = test_data["target_user"]
            response = self.auth_post(test_data["user"], req_data, [current_target_user.id])
            self.assertEqual(response.status_code, self.status.HTTP_204_NO_CONTENT)
            #
            self.assert_user_password_same(current_target_user.id, "justPassword1@")

    def test_user_can_change_it_password(self):
        simple_user = self.create_and_active_user(
            email="simple_user@gmail.comdd", password="testpassword"
        )
    
        req_data = {
            "new_password": "justPassword1@",
            "confirm_new_password": "justPassword1@",
            "password": "testpassword",
        }

        response = self.auth_post(simple_user, req_data, [simple_user.id])
        self.assertEqual(response.status_code, self.status.HTTP_204_NO_CONTENT)
        #
        self.assert_user_password_same(simple_user.id, "justPassword1@")
