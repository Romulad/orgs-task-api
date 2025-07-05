from ...base_classe import BaseTestClass
from organization.models import Organization

class TestDeleteOrgView(BaseTestClass):
    """### Flow
    - user need to be authenticated
    - user need to have access to the org or he is the creator
    - no access allowed user can't delete ressource
    - test org member can not delete ressource, 403
    - ressource is deleted by marking it as is_delete and success rsponse
    - user get not found when ressource not found
    """
    url_name = "orgs-detail"
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

    def test_only_authenticated_user_can_access(self):
        self.evaluate_method_unauthenticated_request(
            self.HTTP_DELETE, ["fake-id"]
        )

    def test_no_access_allowed_cant_delete_ressource(self):
        response = self.auth_delete(self.user, {}, [self.first_org.id])
        self.assertEqual(response.status_code, self.status.HTTP_404_NOT_FOUND)
        # obj still exists
        self.assertIsNotNone(Organization.objects.get(id=self.first_org.id))
    
    def test_member_cant_delete_ressource(self):
        self.first_org.members.add(self.user)
        response = self.auth_delete(self.user, {}, [self.first_org.id])
        self.assertEqual(response.status_code, self.status.HTTP_403_FORBIDDEN)
        # obj still exists
        self.assertIsNotNone(Organization.objects.get(id=self.first_org.id))
        
    def test_access_allowed_user_can_delete_ressource(self):
        self.first_org.can_be_accessed_by.add(self.user)

        test_datas = [
            {"user": self.owner, "org": self.created_data[1]},
            {"user": self.creator, "org": self.created_data[2]},
            {"user": self.user, "org": self.first_org}
        ]

        for test_data in test_datas:
            current_org = test_data["org"]
            response = self.auth_delete(test_data["user"], {}, [current_org.id])
            self.assertEqual(response.status_code, self.status.HTTP_204_NO_CONTENT)
            # obj is deleted
            with self.assertRaises(Organization.DoesNotExist):
                Organization.objects.get(id=current_org.id)
            # obj is still available in the db
            deleted_org = Organization.all_objects.get(id=current_org.id)
            self.assertTrue(deleted_org.is_deleted)
    
    def test_user_get_not_found_error(self):
        response = self.auth_delete(self.owner, {}, ["fake-id"])
        self.assertEqual(response.status_code, self.status.HTTP_404_NOT_FOUND)