from ...base_classe import BaseTestClass
from app_lib.app_permssions import ALL_PERMS


class TestGetPermsDataView(BaseTestClass):
    """### Flow
    - user need to be authenticated
    - user all permission data
    """
    url_name = "perm-list"

    def test_only_authenticated_user_can_access(self):
        self.evaluate_method_unauthenticated_request(
            self.HTTP_GET,
        )

    def test_user_get_perm_data(self):
        user = self.create_and_activate_random_user()
        response = self.auth_get(user)
        self.assertEqual(response.status_code, self.status.HTTP_200_OK)
        data = self.loads(response.content)
        self.assertDictEqual(data, ALL_PERMS)