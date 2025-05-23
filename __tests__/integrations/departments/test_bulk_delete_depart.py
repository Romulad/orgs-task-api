import uuid

from ..base_classe import BaseTestClass
from organization.models import Organization, Department


class TestBulkDeleteOrgDepartMentView(BaseTestClass):
    """### Flow
    - user need to be authenticated
    - request data need to be validate
    - error when user sent request with depart ids that contain id he can not delete
    - ressources are deleted by marking it as is_delete and success response 204
    - when user make request to delete ressource he has access to and some are not found
    success response should be sent containing what was deleted and what was not found, 
    - when user make request with not found ids 404 error message 
    """
    url_name = "departments-delete"
    departs_data = [
        {
            "name": "my depart 1", "description": "some descr"
        },
        {
            "name": "my depart 2", "description": "some descr"
        },
        {
            "name": "my depart 3", "description": "some descr"
        }
    ]

    def setUp(self):
        self.owner_user = self.create_and_active_user(email="owner_user@gmail.com")
        self.org = Organization.objects.create(name="test", owner=self.owner_user)
        departs_data = [*self.departs_data]
        for data in departs_data:
            data["org"] = self.org
        self.created_departs = self.bulk_create_object(Department, departs_data)

    def test_only_authenticated_user_can_access(self):
        self.evaluate_method_unauthenticated_request(
            self.HTTP_DELETE, ["fake-id"]
        )
    
    def test_no_access_allowed_cant_delete_ressources(self):
        user = self.create_and_active_user()
        depart_ids = [created.id for created in self.created_departs]

        response = self.auth_delete(user, {"ids": depart_ids}, [self.org.id])
        self.assertEqual(response.status_code, self.status.HTTP_404_NOT_FOUND)
        # ressources still exist
        [Department.objects.get(id=depart_id) for depart_id in depart_ids]
    
    def test_access_allowed_can_delete_ressources(self):
        user = self.create_and_active_user()
        self.org.can_be_accessed_by.add(user)

        test_datas = [
            {
                "user": self.owner_user, 
                "depart_ids": [self.created_departs[1].id, self.created_departs[2].id]
            },
            {
                "user": user, 
                "depart_ids": [self.created_departs[0].id]
            }
        ]
        
        for test_data in test_datas:
            req_ids = test_data["depart_ids"]
            response = self.auth_delete(test_data["user"], {"ids": req_ids}, [self.org.id])
            self.assertEqual(response.status_code, self.status.HTTP_204_NO_CONTENT)
            # ressources are deleted but with is_deleted attr
            for r_id in req_ids:
                with self.assertRaises(Department.DoesNotExist):
                    Department.objects.get(id=r_id)
                deleted = Department.all_objects.get(id=r_id)
                self.assertTrue(deleted.is_deleted)

    def test_access_allowed_can_delete_ressources_with_not_found(self):
        req_ids = [created.id for created in self.created_departs] + [uuid.uuid4(), uuid.uuid4()]
        
        response = self.auth_delete(self.owner_user, {"ids": req_ids}, [self.org.id])
        self.assertEqual(response.status_code, self.status.HTTP_200_OK)
        # check response data
        data = self.loads(response.content)
        self.assertIsInstance(data.get("deleted"), list)
        self.assertIsInstance(data.get("not_found"), list)
        self.assertEqual(len(data.get("deleted")), 3)
        self.assertEqual(len(data.get("not_found")), 2)
        # ressources are deleted but with is_deleted attr
        for r_id in req_ids[:3]:
            with self.assertRaises(Department.DoesNotExist):
                Department.objects.get(id=r_id)
            deleted = Department.all_objects.get(id=r_id)
            self.assertTrue(deleted.is_deleted)

    def test_not_found_ressources(self):
        req_ids = [uuid.uuid4(), uuid.uuid4()]
        
        response = self.auth_delete(self.owner_user, {"ids": req_ids}, [self.org.id])
        self.assertEqual(response.status_code, self.status.HTTP_404_NOT_FOUND)
        # check response data
        data = self.loads(response.content)
        self.assertIsNotNone(data.get("detail"))

    def test_with_malformatted_data(self):
        response = self.auth_delete(
            self.owner_user, {"ids": ["fake-id", "fake-id2"]}, [self.org.id]
        )
        self.assertEqual(response.status_code, self.status.HTTP_400_BAD_REQUEST)
        # check response data
        data = self.loads(response.content)
        self.assertIsInstance(data.get("ids"), dict)