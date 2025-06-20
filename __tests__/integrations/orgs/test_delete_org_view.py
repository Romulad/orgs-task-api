from ...base_classe import BaseTestClass
from organization.models import Organization

class TestDeleteOrgView(BaseTestClass):
    """### Flow
    - user need to be authenticated
    - user need to have access to the org or he is the creator
    - no access allowed user can't delete ressource
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

    def test_only_authenticated_user_can_access(self):
        self.evaluate_method_unauthenticated_request(
            self.HTTP_DELETE, ["fake-id"]
        )

    def test_no_access_allowed_cant_delete_ressource(self):
        owner = self.create_and_active_user(email="owner@gmail.com")
        user = self.create_and_active_user()

        orgs_data = [*self.orgs_data]
        for data in orgs_data:
            data["owner"] = owner
        created_data = self.bulk_create_object(Organization, orgs_data)
        first_org = created_data[0]

        response = self.auth_delete(user, {}, [first_org.id])
        self.assertEqual(response.status_code, self.status.HTTP_404_NOT_FOUND)
        # obj still exists
        self.assertIsNotNone(Organization.objects.get(id=first_org.id))
        
    def test_access_allowed_user_can_delete_ressource(self):
        owner = self.create_and_active_user(email="owner@gmail.com")
        user = self.create_and_active_user()

        orgs_data = [*self.orgs_data]
        for data in orgs_data:
            data["owner"] = owner
        created_data = self.bulk_create_object(Organization, orgs_data)
        first_org = created_data[0]
        first_org.can_be_accessed_by.add(user)

        test_datas = [
            {"user": owner, "org": created_data[1]},
            {"user": owner, "org": created_data[2]},
            {"user": user, "org": first_org}
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
        owner = self.create_and_active_user(email="owner@gmail.com")
        orgs_data = [*self.orgs_data]
        for data in orgs_data:
            data["owner"] = owner
        self.bulk_create_object(Organization, orgs_data)
        response = self.auth_delete(owner, {}, ["fake-id"])
        self.assertEqual(response.status_code, self.status.HTTP_404_NOT_FOUND)