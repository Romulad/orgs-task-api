
from ..base_classe import BaseTestClass
from organization.models import Organization

class TestRetrieveOrgView(BaseTestClass):
    """### Flow
    - user need to be authenticated
    - user need to be the one that create the org or can have access to the org data
    - user get not found when obj does not exist
    - user can get obj with needed data
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
            self.HTTP_GET, ["fake-id"]
        )
    
    def test_user_cant_get_other_org(self):
        user = self.create_and_active_user()
        owner = self.create_and_active_user(email="owner@gmail.com")

        orgs_data = [*self.orgs_data]
        orgs_data[0]["owner"] = user
        for data in orgs_data[1:]:
            data["owner"] = owner
        created_data = self.bulk_create_object(Organization, orgs_data)
        
        response = self.auth_get(user, [created_data[1].id])
        self.assertEqual(response.status_code, self.status.HTTP_404_NOT_FOUND)
        self.assertIsNotNone(response.data.get("detail", None))
    
    def test_user_can_get_created_access_free_data(self):
        user = self.create_and_active_user()
        owner = self.create_and_active_user(email="owner@gmail.com")

        orgs_data = [*self.orgs_data]
        for data in orgs_data:
            data["owner"] = owner
        created_data = self.bulk_create_object(Organization, orgs_data)
        created_data[0].can_be_accessed_by.add(user)
        # for owner
        response = self.auth_get(owner, [created_data[1].id])
        self.assertEqual(response.status_code, self.status.HTTP_200_OK)
        data = self.loads(response.content)
        self.assertEqual(data.get("id"), str(created_data[1].id))
        self.assertEqual(data.get("name"), created_data[1].name)
        self.assertEqual(data.get("owner").get("id"), str(owner.id))
        self.assertIsInstance(data.get("members"), list)
        self.assertIsNotNone(data.get("description"))
        # for access free user
        response = self.auth_get(user, [created_data[0].id])
        self.assertEqual(response.status_code, self.status.HTTP_200_OK)
        data = self.loads(response.content)
        self.assertEqual(data.get("id"), str(created_data[0].id))
    
    def test_not_found_error(self):
        user = self.create_and_active_user()
        response = self.auth_get(user, ["fake-id"])
        self.assertEqual(response.status_code, self.status.HTTP_404_NOT_FOUND)
        data = self.loads(response.content)
        self.assertIsNotNone(data.get("detail"))