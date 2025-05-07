
from ..base_classe import BaseTestClass
from organization.models import Organization

class TestCreateOrgView(BaseTestClass):
    """### Flow
    - user need to be authenticated
    - user can create an org with required field:
        - name (should be unique for that user among his orgs)
    - name field should be validate when not specified or not unique together with the owner
    - org is created and has the proper owner, name, descr if specied and created_by attr set
    - view return proper response after creation
    """
    url_name = "orgs-list"

    def test_only_authenticated_user_can_access(self):
        self.evaluate_method_unauthenticated_request(
            self.HTTP_POST
        )
    
    def test_user_can_create_orgs(self):
        user = self.create_and_active_user()
        data = {
            "name": "my org mame",
            "description": "my org description",
        }
        response = self.auth_post(user, data)
        self.assertEqual(response.status_code, self.status.HTTP_201_CREATED)
        data = self.loads(response.content)
        self.assertEqual(data.get("name"), "my org mame")
        self.assertEqual(data.get("description"), "my org description")
        self.assertEqual(data.get("owner").get("id"), str(user.id))
        Organization.objects.get(name="my org mame", owner=user, created_by=user)
    
    def test_validate_name_field(self):
        user = self.create_and_active_user()
        Organization.objects.create(name="my org mame", owner=user)
        datas = [
            { "description": "" },
            { "name": "" },
            { "name": "my org mame" },
        ]
        for data in datas:
            response = self.auth_post(user, data)
            self.assertEqual(response.status_code, self.status.HTTP_400_BAD_REQUEST)
            data = self.loads(response.content)
            self.assertIsInstance(data.get("name"), list)