from ..base_classe import BaseTestClass
from user.models import AppUser as User


class TestListUserView(BaseTestClass):
    """### Flow
    - user need to be authenticated
    - user can only get data he created or have access to
    - user get data with needed field, user own data should not be included
    - data is paginated
    - data can be filtered and search throught
    """
    url_name = "users-list"
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
            self.HTTP_GET
        )
    
    def test_user_get_only_created_data(self):
        user = self.create_and_active_user()
        response = self.auth_get(user)
        self.assertEqual(response.status_code, self.status.HTTP_200_OK)
        data = self.loads(response.content).get("results")
        self.assertEqual(len(data), 0)
    
    def test_user_get_only_access_true_data(self):
        simple_user = self.create_and_active_user(email="simple_user@gmaddil.com")

        for user in self.users:
            user.can_be_accessed_by.add(simple_user)

        for curr_user in [simple_user, self.owner_user]:
            response = self.auth_get(curr_user)
            self.assertEqual(response.status_code, self.status.HTTP_200_OK)
            data = self.loads(response.content).get("results")
            self.assertEqual(len(data), 3)
            self.assertIsNotNone(data[0]["email"])
            self.assertIsNotNone(data[0]["first_name"])
            self.assertIsNotNone(data[0]["id"])
            self.assertIsNotNone(data[0]["created_at"])
            self.assertIsNotNone(data[0]["last_name"])
            with self.assertRaises(KeyError):
                data[0]["password"]
    
    def test_user_get_filtered_data(self):
        response = self.auth_get(
            self.owner_user, query_params={"email_contains": "1"}
        )
        self.assertEqual(response.status_code, self.status.HTTP_200_OK)
        data = self.loads(response.content).get("results")
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["email"], "test1@somedoa.com")