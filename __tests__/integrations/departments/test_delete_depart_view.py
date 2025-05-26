import uuid

from ..base_classe import BaseTestClass
from organization.models import Organization, Department


class TestDeleteOrgDepartMentView(BaseTestClass):
    """### Flow
    - user need to be authenticated
    - user need to have access to the org or he is the creator
    - user in the department can_be_accessed_by attr an delete the depart
    - no access allowed user can't delete ressource
    - ressource is deleted by marking it as is_delete and success response
    - user get not found when ressource not found
    """
    url_name = "departments-detail"
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
            self.HTTP_DELETE, ["fake-id", "fake-id"]
        )

    def test_no_access_allowed_cant_delete_ressource(self):
        user = self.create_and_active_user()
        first_depart = self.created_departs[0]

        response = self.auth_delete(user, {}, [self.org.id, first_depart.id])
        self.assertEqual(response.status_code, self.status.HTTP_403_FORBIDDEN)
        # obj still exists
        self.assertIsNotNone(Department.objects.get(id=first_depart.id))
        
    def test_access_allowed_user_can_delete_ressource(self):
        user = self.create_and_active_user()
        first_depart = self.created_departs[0]
        self.org.can_be_accessed_by.add(user)

        test_datas = [
            {"user": self.owner_user, "depart": self.created_departs[1]},
            {"user": self.owner_user, "depart": self.created_departs[2]},
            {"user": user, "depart": first_depart}
        ]

        for test_data in test_datas:
            current_depart = test_data["depart"]
            response = self.auth_delete(
                test_data["user"], {}, [self.org.id, current_depart.id]
            )
            self.assertEqual(response.status_code, self.status.HTTP_204_NO_CONTENT)
            # obj is deleted
            with self.assertRaises(Department.DoesNotExist):
                Department.objects.get(id=current_depart.id)
            # obj is still available in the db
            deleted_depart = Department.all_objects.get(id=current_depart.id)
            self.assertTrue(deleted_depart.is_deleted)
    
    def test_access_allowed_user_on_depart_can_delete_ressource(self):
        user = self.create_and_active_user()
        first_depart = self.created_departs[0]
        first_depart.can_be_accessed_by.add(user)

        response = self.auth_delete(
            user, {}, [self.org.id, first_depart.id]
        )
        self.assertEqual(response.status_code, self.status.HTTP_204_NO_CONTENT)
        # obj is deleted
        with self.assertRaises(Department.DoesNotExist):
            Department.objects.get(id=first_depart.id)
        # obj is still available in the db
        deleted_depart = Department.all_objects.get(id=first_depart.id)
        self.assertTrue(deleted_depart.is_deleted)
    
    def test_user_get_not_found_error(self):
        response = self.auth_delete(self.owner_user, {}, [uuid.uuid4(), uuid.uuid4()])
        self.assertEqual(response.status_code, self.status.HTTP_404_NOT_FOUND)