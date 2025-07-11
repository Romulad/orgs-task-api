import uuid

from ...base_classe import BaseTestClass
from organization.models import Organization

class TestBulkDeleteOrgView(BaseTestClass):
    """### Flow
    - user need to be authenticated
    - request data need to be validate
    - error when user sent request with org ids that contain id he can not delete
    - org member can not bulk delete ressources
    - ressources are deleted by marking it as is_delete and success response 204
    - when user make request to delete ressource he has access to and some are not found
    success response should be sent containing what was deleted and what was not found, 
    - when user make request with not found ids 404 error message 
    """
    url_name = "orgs-bulk-delete"
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
        self.creator = self.create_and_activate_random_user()
        self.user = self.create_and_active_user()
        orgs_data = [*self.orgs_data]
        for data in orgs_data:
            data["owner"] = self.owner
            data["created_by"] = self.creator
        self.created_data = self.bulk_create_object(Organization, orgs_data)
        self.first_org = self.created_data[0]
        self.org_ids = [created.id for created in self.created_data]

    def test_only_authenticated_user_can_access(self):
        self.evaluate_method_unauthenticated_request(
            self.HTTP_DELETE,
        )
    
    def test_no_access_allowed_cant_delete_ressources(self):
        response = self.auth_delete(self.user, {"ids": self.org_ids})
        self.assertEqual(response.status_code, self.status.HTTP_404_NOT_FOUND)
        # ressources still exist
        [Organization.objects.get(id=org_id) for org_id in self.org_ids]
    

    def test_member_cant_bulk_delete_ressource(self):
        [org.members.add(self.user) for org in self.created_data]
        response = self.auth_delete(self.user, {"ids": self.org_ids})
        self.assertEqual(response.status_code, self.status.HTTP_403_FORBIDDEN)
        # ressources still exist
        [Organization.objects.get(id=org_id) for org_id in self.org_ids]
    
    def test_access_allowed_can_delete_ressources(self):
        self.first_org.can_be_accessed_by.add(self.user)

        test_datas = [
            {"user": self.owner, "org": [self.created_data[1].id]},
            {"user": self.creator, "org": [self.created_data[2].id]},
            {"user": self.user, "org": [self.first_org.id]}
        ]
        
        for test_data in test_datas:
            req_ids = test_data["org"]
            response = self.auth_delete(test_data["user"], {"ids": req_ids})
            self.assertEqual(response.status_code, self.status.HTTP_204_NO_CONTENT)
            # ressources are deleted but with is_deleted attr
            for r_id in req_ids:
                with self.assertRaises(Organization.DoesNotExist):
                    Organization.objects.get(id=r_id)
                deleted = Organization.all_objects.get(id=r_id)
                self.assertTrue(deleted.is_deleted)

    def test_access_allowed_can_delete_ressources_with_not_found(self):
        req_ids = self.org_ids + [uuid.uuid4(), uuid.uuid4()]
        
        response = self.auth_delete(self.owner, {"ids": req_ids})
        self.assertEqual(response.status_code, self.status.HTTP_200_OK)
        # check response data
        data = self.loads(response.content)
        self.assertIsInstance(data.get("deleted"), list)
        self.assertIsInstance(data.get("not_found"), list)
        self.assertEqual(len(data.get("deleted")), 3)
        self.assertEqual(len(data.get("not_found")), 2)
        # ressources are deleted but with is_deleted attr
        for r_id in req_ids[:3]:
            with self.assertRaises(Organization.DoesNotExist):
                Organization.objects.get(id=r_id)
            deleted = Organization.all_objects.get(id=r_id)
            self.assertTrue(deleted.is_deleted)

    def test_not_found_ressources(self):
        req_ids = [uuid.uuid4(), uuid.uuid4()]
        response = self.auth_delete(self.owner, {"ids": req_ids})
        self.assertEqual(response.status_code, self.status.HTTP_404_NOT_FOUND)
        # check response data
        data = self.loads(response.content)
        self.assertIsNotNone(data.get("detail"))

    def test_with_malformatted_data(self):
        response = self.auth_delete(self.owner, {"ids": ["fake-id", "fake-id2"]})
        self.assertEqual(response.status_code, self.status.HTTP_400_BAD_REQUEST)
        # check response data
        data = self.loads(response.content)
        self.assertIsInstance(data.get("ids"), dict)