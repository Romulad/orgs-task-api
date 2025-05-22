from ..base_classe import BaseTestClass

class TestMeView(BaseTestClass):
    """### Flow
    - user need to be authenticated
    - test user can get data with needed fields
    """
    url_name = "users-me"

    def test_only_authenticated_user_can_access(self):
        self.evaluate_method_unauthenticated_request(
            self.HTTP_GET
        )
    
    def test_user_get_needed_data(self):
        user = self.create_and_active_user()
        response = self.auth_get(user)
        self.assertEqual(response.status_code, self.status.HTTP_200_OK)
        self.assertEqual(response.data.get("id", None), user.id)
        self.assertEqual(response.data.get("email", None), user.email)
        self.assertEqual(response.data.get("first_name", None), user.first_name)
        self.assertEqual(response.data.get("last_name", None), user.last_name)