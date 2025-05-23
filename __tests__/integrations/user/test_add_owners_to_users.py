import uuid

from ..base_classe import BaseTestClass
from user.models import AppUser as User

class TestAddOwnerToUserObjectView(BaseTestClass):
    """### Flow
    - user need to be authenticated
    - user get not found when obj does not exist
    - user without access get not found error
    - other user with access but not creator or user itself cant update object owners, 403
    - validate owner user ids provide:
        - ids should exist
        - user that is making the request should have a full access over owner user specified
    - owners are successfully added to obj can_be_accessed_by list after request
    - test user itself can update owner list even without having access over owner users
    """
    url_name = "users-change-owners"
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
    
    def test_access_allowed_user_cant_update_owner(self):
        target_user = self.users[0]
        simple_user = self.create_and_active_user(email="simple_user@gnaiold.com")
        target_user.can_be_accessed_by.add(simple_user)
        response = self.auth_post(simple_user, {}, [target_user.id])
        self.assertEqual(response.status_code, self.status.HTTP_403_FORBIDDEN)
        self.assertIsNotNone(response.data.get("detail", None))
    
    def test_req_data_validation_ids(self):
        simple_user = self.create_and_active_user(email="simple_user@gnaiold.com")
        target_user = self.users[0]

        test_datas = [
            {},
            # {"owner_ids": []},
            {"owner_ids": [uuid.uuid4(), uuid.uuid4()]},
            {"owner_ids": [simple_user.id]}
        ]

        for test_data in test_datas:
            response = self.auth_post(self.owner_user, test_data, [target_user.id])
            self.assertEqual(response.status_code, self.status.HTTP_400_BAD_REQUEST)
            self.assertIsNotNone(response.data.get("owner_ids", None))
            self.assertIsInstance(response.data.get("owner_ids"), list)
        self.assertEqual(
            len(User.objects.get(id=target_user.id).can_be_accessed_by.all()), 0
        )
    
    def test_owner_can_change_obj_access(self):
        simple_user = self.create_and_active_user(email="simple_user@gnaiold.com")
        simple_user.can_be_accessed_by.add(self.owner_user)
        target_user = self.users[0]

        req_data = {
            "owner_ids": [simple_user.id]
        }

        response = self.auth_post(self.owner_user, req_data, [target_user.id])
        self.assertEqual(response.status_code, self.status.HTTP_204_NO_CONTENT)
        access_allowed = User.objects.get(id=target_user.id).can_be_accessed_by.all()
        self.assertEqual(len(access_allowed), 1)
        self.assertIn(simple_user, access_allowed)

    def test_user_can_change_it_own_obj_access(self):
        simple_user = self.create_and_active_user(email="simple_user@gnaiold.com")
        req_data = {
            "owner_ids": [self.owner_user.id]
        }

        response = self.auth_post(simple_user, req_data, [simple_user.id])
        self.assertEqual(response.status_code, self.status.HTTP_204_NO_CONTENT)
        access_allowed = User.objects.get(id=simple_user.id).can_be_accessed_by.all()
        self.assertEqual(len(access_allowed), 1)
        self.assertIn(self.owner_user, access_allowed)

