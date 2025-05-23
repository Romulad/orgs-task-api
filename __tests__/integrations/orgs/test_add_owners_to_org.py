import uuid

from ..base_classe import BaseTestClass
from organization.models import Organization

class TestAddOwnerToOrgObjectView(BaseTestClass):
    """### Flow
    - user need to be authenticated
    - user get not found when obj does not exist
    - user without access get not found error
    - user with access allowed cant update obj owner, if try 403 error
    - only creator can update object owners
    - validate owner user ids provide:
        - ids should exist
        - user that is making the request should have a full access over owner user specified
    - owners are successfully added to obj can_be_accessed_by list after request
    """
    url_name = "orgs-change-owners"
    orgs_data = [
        {
            "name": "my org 1", "description": "some descr"
        },
        {
            "name": "my org 2", "description": "some descr"
        },
        {
            "name": "my org 3", "description": "some descr"
        }
    ]

    def setUp(self):
        self.owner = self.create_and_active_user(email="owner@gmail.com")
        orgs_data = [*self.orgs_data]
        for data in orgs_data:
            data["owner"] = self.owner
            data["created_by"] = self.owner
        self.created_data = self.bulk_create_object(Organization, orgs_data)
        
    def test_only_authenticated_user_can_access(self):
        self.evaluate_method_unauthenticated_request(
            self.HTTP_POST, ["fake-id"]
        )
    
    def test_not_found_user(self):
        response = self.auth_post(self.owner, {}, [uuid.uuid4()])
        self.assertEqual(response.status_code, self.status.HTTP_404_NOT_FOUND)
        self.assertIsNotNone(response.data.get("detail", None))
    
    def test_other_cant_update_data(self):
        other_user = self.create_and_active_user(email="other_user@gmaild.com")
        response = self.auth_post(
            other_user,
            {},
            [self.created_data[0].id]
        )
        self.assertEqual(response.status_code, self.status.HTTP_404_NOT_FOUND)
        self.assertIsNotNone(response.data.get("detail", None))
    
    def test_access_allowed_user_cant_update_owner(self):
        target_org = self.created_data[0]
        simple_user = self.create_and_active_user(email="simple_user@gnaiold.com")
        target_org.can_be_accessed_by.add(simple_user)
        response = self.auth_post(simple_user, {}, [target_org.id])
        self.assertEqual(response.status_code, self.status.HTTP_403_FORBIDDEN)
        self.assertIsNotNone(response.data.get("detail", None))
    
    def test_req_data_validation_ids(self):
        simple_user = self.create_and_active_user(email="simple_user@gnaiold.com")
        target_org = self.created_data[0]

        test_datas = [
            {},
            {"owner_ids": []},
            {"owner_ids": [uuid.uuid4(), uuid.uuid4()]},
            {"owner_ids": [simple_user.id]}
        ]

        for test_data in test_datas:
            response = self.auth_post(self.owner, test_data, [target_org.id])
            self.assertEqual(response.status_code, self.status.HTTP_400_BAD_REQUEST)
            self.assertIsNotNone(response.data.get("owner_ids", None))
            self.assertIsInstance(response.data.get("owner_ids"), list)
        self.assertEqual(
            len(Organization.objects.get(id=target_org.id).can_be_accessed_by.all()), 0
        )
    
    def test_creator_can_change_obj_access_user(self):
        simple_user = self.create_and_active_user(email="simple_user@gnaiold.com")
        simple_user.can_be_accessed_by.add(self.owner)
        target_org = self.created_data[0]

        req_data = {
            "owner_ids": [simple_user.id]
        }

        response = self.auth_post(self.owner, req_data, [target_org.id])
        self.assertEqual(response.status_code, self.status.HTTP_204_NO_CONTENT)
        access_allowed = Organization.objects.get(id=target_org.id).can_be_accessed_by.all()
        self.assertEqual(len(access_allowed), 1)
        self.assertIn(simple_user, access_allowed)