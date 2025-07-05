import uuid

from ...base_classe import BaseTestClass
from user.models import AppUser as User

class TestUpdateUserView(BaseTestClass):
    """### Flow
    - user need to be authenticated
    - user get not found when obj does not exist
    - other user can't update user data only creator or access allowed user can or 404
    - test all field should be required (email, first_name, last_name)
    - test field validation:
        - email is a valid email
        - user can include current instance email but check existance for new specified email
        - first_name is at leat 3 characters long
    - test data is updated in the db and we get needed data back in the response
    - test user can update it own data
    """
    url_name = "users-detail"
    user_data_list = [
        {
            "email": "test@somedoa.com",
            "password": "password"
        },
        {
            "email": "test1@somedoa.com",
            "password": "password"
        },
        {
            "email": "test2@somedoa.com",
            "password": "password"
        }
    ]

    def setUp(self):
        self.owner_user = self.create_and_active_user(email="owner_user@noway.come")
        data_list = [*self.user_data_list]
        for data in data_list:
            data["created_by"] = self.owner_user
        self.users = self.bulk_create_object(User, data_list)

    def test_only_authenticated_user_can_access(self):
        self.evaluate_method_unauthenticated_request(
            self.HTTP_PUT, ["fake-id"]
        )
    
    def test_not_found_user(self):
        response = self.auth_put(self.owner_user, {}, [uuid.uuid4()])
        self.assertEqual(response.status_code, self.status.HTTP_404_NOT_FOUND)
        self.assertIsNotNone(response.data.get("detail", None))
    
    def test_other_cant_update_data(self):
        other_user = self.create_and_active_user(email="other_user@gmaild.com")
        response = self.auth_put(
            other_user,
            {},
            [self.users[0].id]
        )
        self.assertEqual(response.status_code, self.status.HTTP_404_NOT_FOUND)
        self.assertIsNotNone(response.data.get("detail", None))
    
    def test_all_field_should_be_include(self):
        will_be_update = self.users[0]
        response = self.auth_put(
            self.owner_user,
            {
                "email": 'valideam.@gh.com',
                "first_name": 'testvalid',
            },
            [will_be_update.id]
        )
        self.assertEqual(response.status_code, self.status.HTTP_400_BAD_REQUEST)
        errors = self.loads(response.content)
        self.assertIsInstance(errors.get('last_name'), list)
        # data still same
        user_data = User.objects.get(id=will_be_update.id)
        self.assertEqual(user_data.email, will_be_update.email)
        self.assertEqual(user_data.first_name, will_be_update.first_name)
    
    def test_email_validation(self):
        req_datas = [
            {
                "email": '',
                "first_name": 'testvalid',
                "last_name": ""
            },
            {
                "email": 'invalidemail',
                "first_name": 'testvalid',
                "last_name": "mylastname"
            },
            {
                "email": self.users[1].email,
                "first_name": 'testvalid',
                "last_name": "mylastname"
            },
        ]
        will_be_update = self.users[0]
        for req_data in req_datas:
            response = self.auth_put(
                self.owner_user, req_data, [will_be_update.id]
            )
            self.assertEqual(response.status_code, self.status.HTTP_400_BAD_REQUEST)
            errors = self.loads(response.content)
            self.assertIsInstance(errors.get('email'), list)
            # data still same
            user_data = User.objects.get(id=will_be_update.id)
            self.assertEqual(user_data.email, will_be_update.email)

    def test_first_name_validation(self):
        req_datas = [
            {
                "email": 'validnew@doaid.com',
                "first_name": '',
                "last_name": ""
            },
            {
                "email": 'validnew@doaid.com',
                "first_name": 'te',
                "last_name": "mylastname"
            }
        ]
        will_be_update = self.users[0]
        for req_data in req_datas:
            response = self.auth_put(
                self.owner_user, req_data, [will_be_update.id]
            )
            self.assertEqual(response.status_code, self.status.HTTP_400_BAD_REQUEST)
            errors = self.loads(response.content)
            self.assertIsInstance(errors.get('first_name'), list)
            # data still same
            user_data = User.objects.get(id=will_be_update.id)
            self.assertEqual(user_data.email, will_be_update.email)
    
    def test_only_access_allowed_user_can_update_data(self):
        simple_user = self.create_and_active_user(email="simple_user@gnailmm.com")
        self.users[0].can_be_accessed_by.add(simple_user)
        
        req_data = {
            "first_name": 'new_first_name',
            "last_name": "last_name"
        }
        test_datas = [
            {"user": simple_user, "target_user": self.users[0]},
            {"user": self.owner_user, "target_user": self.users[1]}
        ]

        for test_data in test_datas:
            current_user = test_data.get("user")
            target_user = test_data.get("target_user")
            # add email field to avoid error
            req_data["email"] = target_user.email 
            response = self.auth_put(current_user, req_data, [target_user.id])
            self.assertEqual(response.status_code, self.status.HTTP_200_OK)
            data = self.loads(response.content)
            self.assertIsNotNone(data.get('id'))
            self.assertIsNotNone(data.get('created_at'))
            self.assertEqual(data.get('email'), target_user.email)
            self.assertEqual(data.get('first_name'), 'new_first_name')
            self.assertEqual(data.get('last_name'), 'last_name')
            # data is updated
            user_data = User.objects.get(id=target_user.id)
            self.assertEqual(user_data.email, target_user.email)
            self.assertEqual(user_data.first_name, 'new_first_name')
            self.assertEqual(user_data.last_name, 'last_name')
    
    def test_user_can_update_it_own_data(self):
        simple_user = self.create_and_active_user(email="simple_user@gnahj.com")
        req_data = {
            "email": 'validnew@doaid.com',
            "first_name": 'new_first_name',
            "last_name": "last_name"
        }
        response = self.auth_put(simple_user, req_data, [simple_user.id])
        self.assertEqual(response.status_code, self.status.HTTP_200_OK)
        # data is updated
        user_data = User.objects.get(id=simple_user.id)
        self.assertEqual(user_data.email, 'validnew@doaid.com')
        self.assertEqual(user_data.first_name, 'new_first_name')
        self.assertEqual(user_data.last_name, 'last_name')
    