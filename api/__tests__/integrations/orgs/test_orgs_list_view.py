
from ...base_classe import BaseTestClass
from organization.models import Organization

class TestListOrgView(BaseTestClass):
    """### Flow
    - user need to be authenticated
    - user can only get orgs he created or have access to
    - user get data with needed field:
        - org owner
        - org creator
        - can_be_accessed_by
        - members
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

    def setUp(self):
        self.owner_user = self.create_and_activate_random_user()
        self.creator = self.create_and_activate_random_user()
        orgs_data = [*self.orgs_data]
        for data in orgs_data:
            data["owner"] = self.owner_user
            data["created_by"] = self.creator
        self.orgs = self.bulk_create_object(Organization, orgs_data)

    def test_only_authenticated_user_can_access(self):
        self.evaluate_method_unauthenticated_request(
            self.HTTP_GET
        )
    
    def test_user_get_only_created_data(self):
        new_owner, new_creator, org = self.create_new_org()
        for user in [new_owner, new_creator]:
            response = self.auth_get(user)
            self.assertEqual(response.status_code, self.status.HTTP_200_OK)
            data = self.loads(response.content).get("results")
            self.assertEqual(len(data), 1)
            self.assertEqual(data[0]["name"], org.name)
    
    def test_user_get_only_access_true_data(self):
        target_org = self.orgs[0]
        user = self.create_and_activate_random_user()
        target_org.can_be_accessed_by.add(user)
        response = self.auth_get(user)
        self.assertEqual(response.status_code, self.status.HTTP_200_OK)
        data = self.loads(response.content).get("results")
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["name"], target_org.name)
        self.assertEqual(data[0]["owner"]["id"], str(self.owner_user.id))
        self.assertEqual(data[0]["created_by"]["id"], str(self.creator.id))
    
    def test_members_can_get_org_data(self):
        target_org = self.orgs[0]
        user = self.create_and_activate_random_user()
        target_org.members.add(user)
        response = self.auth_get(user)
        self.assertEqual(response.status_code, self.status.HTTP_200_OK)
        data = self.loads(response.content).get("results")
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["name"], target_org.name)
        self.assertEqual(data[0]["owner"]["id"], str(self.owner_user.id))
    
    def test_user_get_filtered_data(self):
        response = self.auth_get(
            self.owner_user, query_params={"name_contain": "2"}
        )
        self.assertEqual(response.status_code, self.status.HTTP_200_OK)
        data = self.loads(response.content).get("results")
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["name"], "my org 2")
        self.assertEqual(data[0]["owner"]["id"], str(self.owner_user.id))

