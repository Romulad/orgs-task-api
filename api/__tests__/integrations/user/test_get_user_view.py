import uuid

from ...base_classe import BaseTestClass
from user.models import AppUser as User

class TestRetrieveUserView(BaseTestClass):
    """### Flow
    - user need to be authenticated
    - test not not allowed can not get user data
    - test not found when user does not exist
    - test user can get other created user data with needed fields
    - test user can get his data with needed fields
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
            self.HTTP_GET, ["fake-id"]
        )
    
    def test_user_cant_get_other_user(self):
        wanted_user = self.users[0]
        other_user = self.create_and_active_user()
        response = self.auth_get(other_user, [wanted_user.id])
        self.assertEqual(response.status_code, self.status.HTTP_404_NOT_FOUND)
        self.assertIsNotNone(response.data.get("detail", None))
    
    def test_not_found_user(self):
        response = self.auth_get(self.owner_user, [uuid.uuid4()])
        self.assertEqual(response.status_code, self.status.HTTP_404_NOT_FOUND)
        self.assertIsNotNone(response.data.get("detail", None))
    
    def test_access_allowed_can_get_ressources(self):
        access_allowed_user = self.create_and_active_user(email="access_allowed_user@testjiu.com")
        self.users[0].can_be_accessed_by.add(access_allowed_user)
        test_datas = [
            {
                "user": self.owner_user, 
                "wanted_user": self.users[1]
            },
            {
                "user": access_allowed_user, 
                "wanted_user": self.users[0]
            }
        ]
        for data in test_datas:
            req_user = data["user"]
            wanted_user = data["wanted_user"]
            response = self.auth_get(req_user, [wanted_user.id])
            self.assertEqual(response.status_code, self.status.HTTP_200_OK)
            data = self.loads(response.content)
            self.assertEqual(data.get("id"), str(wanted_user.id))
            self.assertEqual(data.get("email"), wanted_user.email)
            self.assertEqual(data.get("first_name"), wanted_user.first_name)
            self.assertEqual(data.get("last_name"), wanted_user.last_name)
            self.assertIsNotNone(data.get("created_at", None))
            with self.assertRaises(KeyError):
                data["password"]
    
    def test_user_get_his_data(self):
        simple_user = self.create_and_active_user(email="simple_user@gmail.dd.com")
        response = self.auth_get(simple_user, [simple_user.id])
        self.assertEqual(response.status_code, self.status.HTTP_200_OK)
        data = self.loads(response.content)
        self.assertEqual(data.get("id"), str(simple_user.id))
        self.assertEqual(data.get("email"), simple_user.email)