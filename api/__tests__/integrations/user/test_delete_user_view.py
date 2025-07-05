import uuid

from ...base_classe import BaseTestClass
from user.models import AppUser as User

class TestDeleteUserView(BaseTestClass):
    """### Flow
    - user need to be authenticated
    - user get not found when obj does not exist
    - other user can't delete user data even access allowed user can not only creator can or 404
    - only creator user can delete user, and data should not be totaly deleted but is_delete attr set to True
    - test user can delete itself
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
            self.HTTP_DELETE, ["fake-id"]
        )
    
    def test_not_found_user(self):
        response = self.auth_delete(self.owner_user, {}, [uuid.uuid4()])
        self.assertEqual(response.status_code, self.status.HTTP_404_NOT_FOUND)
        self.assertIsNotNone(response.data.get("detail", None))
    
    def test_other_cant_delete_data(self):
        target_user = self.users[0]
        other_user = self.create_and_active_user(email="other_user@gmaild.com")
        response = self.auth_delete(
            other_user,
            {},
            [target_user.id]
        )
        self.assertEqual(response.status_code, self.status.HTTP_404_NOT_FOUND)
        self.assertIsNotNone(response.data.get("detail", None))
        # user still exists
        User.objects.get(id=target_user.id)
    
    def test_access_allow_user_cant_delete_data(self):
        target_user = self.users[0]
        simple_user = self.create_and_active_user(email="simple_user@gmsil.com")
        target_user.can_be_accessed_by.add(simple_user)
        response = self.auth_delete(
            simple_user,
            {},
            [target_user.id]
        )
        self.assertEqual(response.status_code, self.status.HTTP_403_FORBIDDEN)
        self.assertIsNotNone(response.data.get("detail", None))
        # user still exists
        User.objects.get(id=target_user.id)
    
    def test_creator_can_delete_user_data(self):
        target_user = self.users[0]
        response = self.auth_delete(self.owner_user, {}, [target_user.id])
        self.assertEqual(response.status_code, self.status.HTTP_204_NO_CONTENT)
        with self.assertRaises(User.DoesNotExist):
            User.objects.get(id=target_user.id)
        User.all_objects.get(id=target_user.id)
    
    def test_user_can_delete_itself(self):
        simple_user = self.create_and_active_user(email='simple_user@gmail.cjc.com')
        response = self.auth_delete(simple_user, {}, [simple_user.id])
        self.assertEqual(response.status_code, self.status.HTTP_204_NO_CONTENT)
        with self.assertRaises(User.DoesNotExist):
            User.objects.get(id=simple_user.id)
        User.all_objects.get(id=simple_user.id)
     
            
