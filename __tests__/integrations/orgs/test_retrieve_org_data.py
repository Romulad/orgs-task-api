
from ...base_classe import BaseTestClass
from organization.models import Organization

class TestRetrieveOrgView(BaseTestClass):
    """### Flow
    - user need to be authenticated
    - user need to be:
        - the one that create the org or owner 
        - can have access to the org data
        - or he is an org memeber
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

    def setUp(self):
        self.owner = self.create_and_activate_random_user()
        orgs_data = [*self.orgs_data]
        for data in orgs_data:
            data["owner"] = self.owner
        self.created_data = self.bulk_create_object(Organization, orgs_data)
        self.simple_user = self.create_and_activate_random_user()

    def test_only_authenticated_user_can_access(self):
        self.evaluate_method_unauthenticated_request(
            self.HTTP_GET, ["fake-id"]
        )
    
    def test_user_cant_get_other_org(self):
        data = self.created_data[0]
        data.owner = self.simple_user
        data.save()
        response = self.auth_get(self.simple_user, [self.created_data[1].id])
        self.assertEqual(response.status_code, self.status.HTTP_404_NOT_FOUND)
        self.assertIsNotNone(response.data.get("detail", None))
    
    def test_user_can_get_created_access_free_data(self):
        self.created_data[0].can_be_accessed_by.add(self.simple_user)
        # for owner
        response = self.auth_get(self.owner, [self.created_data[1].id])
        self.assertEqual(response.status_code, self.status.HTTP_200_OK)
        data = self.loads(response.content)
        self.assertEqual(data.get("id"), str(self.created_data[1].id))
        self.assertEqual(data.get("name"), self.created_data[1].name)
        self.assertEqual(data.get("owner").get("id"), str(self.owner.id))
        self.assertIsInstance(data.get("members"), list)
        self.assertIsNotNone(data.get("description"))
        # for access free user
        response = self.auth_get(self.simple_user, [self.created_data[0].id])
        self.assertEqual(response.status_code, self.status.HTTP_200_OK)
        data = self.loads(response.content)
        self.assertEqual(data.get("id"), str(self.created_data[0].id))
    
    def test_members_can_get_data(self):
        self.created_data[0].members.add(self.simple_user)
        # for owner
        response = self.auth_get(self.simple_user, [self.created_data[0].id])
        self.assertEqual(response.status_code, self.status.HTTP_200_OK)
        data = self.loads(response.content)
        self.assertEqual(data.get("id"), str(self.created_data[0].id))
        self.assertEqual(data.get("name"), self.created_data[0].name)
        self.assertEqual(data.get("owner").get("id"), str(self.owner.id))
        self.assertIsInstance(data.get("members"), list)
        self.assertIsNotNone(data.get("description"))
    
    def test_not_found_error(self):
        response = self.auth_get(self.owner, ["fake-id"])
        self.assertEqual(response.status_code, self.status.HTTP_404_NOT_FOUND)
        data = self.loads(response.content)
        self.assertIsNotNone(data.get("detail"))