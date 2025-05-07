
from ..base_classe import BaseTestClass
from organization.models import Organization

class TestListOrgView(BaseTestClass):
    """### Flow
    - user need to be authenticated
    - user can only get orgs he created or have access to
    - user get data with needed field
    - data is paginated
    - data can be filtered and search throught
    """
    url_name = "orgs-list"
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
            self.HTTP_GET
        )
    
    def test_user_get_only_created_data(self):
        other_owner = self.create_and_active_user(email="owner_org@gnail.com")
        user = self.create_and_active_user()

        orgs_data = [*self.orgs_data]
        orgs_data[0]["owner"] = user
        orgs_data[1]["owner"] = other_owner
        orgs_data[2]["owner"] = other_owner
        self.bulk_create_object(Organization, orgs_data)

        response = self.auth_get(user)
        self.assertEqual(response.status_code, self.status.HTTP_200_OK)
        data = self.loads(response.content).get("results")
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["name"], orgs_data[0]["name"])
        self.assertEqual(data[0]["owner"]["id"], str(user.id))
    
    def test_user_get_only_access_true_data(self):
        # create owner a not owner
        owner_user = self.create_and_active_user(email="owner_org@gnail.com")
        user = self.create_and_active_user()

        orgs_data = [*self.orgs_data]
        for data in orgs_data:
            data["owner"] = owner_user 
        orgs = self.bulk_create_object(Organization, orgs_data)
        orgs[0].can_be_accessed_by.add(user)

        response = self.auth_get(user)
        self.assertEqual(response.status_code, self.status.HTTP_200_OK)
        data = self.loads(response.content).get("results")
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["name"], orgs_data[0]["name"])
        self.assertEqual(data[0]["owner"]["id"], str(owner_user.id))
    
    def test_user_get_filtered_data(self):
        owner_user = self.create_and_active_user()
        orgs_data = [*self.orgs_data]
        for data in orgs_data:
            data["owner"] = owner_user 
        self.bulk_create_object(Organization, orgs_data)

        response = self.auth_get(
            owner_user, query_params={"name_contain": "2"}
        )
        self.assertEqual(response.status_code, self.status.HTTP_200_OK)
        data = self.loads(response.content).get("results")
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["name"], "my org 2")
        self.assertEqual(data[0]["owner"]["id"], str(owner_user.id))

