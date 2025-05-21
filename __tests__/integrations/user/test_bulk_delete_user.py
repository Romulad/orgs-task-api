import uuid

from ..base_classe import BaseTestClass
from user.models import AppUser as User
class TestBulkDeleteUserView(BaseTestClass):
    """### Flow
    - user need to be authenticated
    - request data need to be validate
    - error when user sent request with org ids that contain id he can not delete
    - ressources are deleted by marking it as is_delete and success response 204
    - when user make request to delete ressource he has access to and some are not found
    success response should be sent containing what was deleted and what was not found, 
    - when user make request with not found ids 404 error message 
    """
    url_name = "users-bulk-delete"
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
            self.HTTP_DELETE, {}
        )
    
    def test_no_access_allowed_cant_delete_ressources(self):
        user = self.create_and_active_user()
        user_ids = [created.id for created in self.users]
        response = self.auth_delete(user, {"ids": user_ids})
        self.assertEqual(response.status_code, self.status.HTTP_404_NOT_FOUND)
        # ressources still exist
        [User.objects.get(id=user_id) for user_id in user_ids]
    
    def test_access_allowed_can_delete_ressources(self):
        user = self.create_and_active_user()
        first_user = self.users[0]
        first_user.can_be_accessed_by.add(user)

        test_datas = [
            {"user": self.owner_user, "ids": [self.users[1].id, self.users[2].id]},
            {"user": user, "ids": [first_user.id]}
        ]
        
        for test_data in test_datas:
            req_ids = test_data["ids"]
            response = self.auth_delete(test_data["user"], {"ids": req_ids})
            self.assertEqual(response.status_code, self.status.HTTP_204_NO_CONTENT)
            # ressources are deleted but with is_deleted attr
            for r_id in req_ids:
                with self.assertRaises(User.DoesNotExist):
                    User.objects.get(id=r_id)
                deleted = User.all_objects.get(id=r_id)
                self.assertTrue(deleted.is_deleted)

    def test_access_allowed_can_delete_ressources_with_not_found(self):
        req_ids = [created.id for created in self.users] + [uuid.uuid4(), uuid.uuid4()]        
        response = self.auth_delete(self.owner_user, {"ids": req_ids})
        self.assertEqual(response.status_code, self.status.HTTP_200_OK)
        # check response data
        data = self.loads(response.content)
        self.assertIsInstance(data.get("deleted"), list)
        self.assertIsInstance(data.get("not_found"), list)
        self.assertEqual(len(data.get("deleted")), 3)
        self.assertEqual(len(data.get("not_found")), 2)
        # ressources are deleted but with is_deleted attr
        for r_id in req_ids[:3]:
            with self.assertRaises(User.DoesNotExist):
                User.objects.get(id=r_id)
            deleted = User.all_objects.get(id=r_id)
            self.assertTrue(deleted.is_deleted)

    def test_not_found_ressources(self):
        req_ids = [uuid.uuid4(), uuid.uuid4()]
        
        response = self.auth_delete(self.owner_user, {"ids": req_ids})
        self.assertEqual(response.status_code, self.status.HTTP_404_NOT_FOUND)
        # check response data
        data = self.loads(response.content)
        self.assertIsNotNone(data.get("detail"))

    def test_with_malformatted_data(self):
        response = self.auth_delete(self.owner_user, {"ids": ["fake-id", "fake-id2"]})
        self.assertEqual(response.status_code, self.status.HTTP_400_BAD_REQUEST)
        # check response data
        data = self.loads(response.content)
        self.assertIsInstance(data.get("ids"), dict)