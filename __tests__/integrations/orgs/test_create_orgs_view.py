import uuid

from ...base_classe import BaseTestClass
from organization.models import Organization

class TestCreateOrgView(BaseTestClass):
    """### Flow
    - user need to be authenticated
    - user can create an org with required field:
        - name (should be unique for that user among his orgs)
    - name field should be validate when not specified or not unique together with the owner
    - test user can not created org with owner user that he has not access to -> bad request
    - test user can not created org with not found owner
    - test user can't create org with members he has not access to
    - test user can't create org with members the owner has not access to even if the creator has access
    - test user can't create org with not found members
    - test send create org req with full data and check db state
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
        self.assertEqual(data.get("owner"), str(user.id))
        self.assertIsInstance(data.get("members"), list)
        self.assertIsNotNone(data.get("id", None))
        self.assertIsNotNone(data.get("created_at"))
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
    
    def test_optional_validation(self):
        user = self.create_and_active_user()
        own_owner = self.create_and_active_user(email="own_owner@ganil.com", created_by=user)
        access_free_owner = self.create_and_active_user(email="access_free_owner@ganil.com")
        access_free_owner.can_be_accessed_by.add(user)
        not_access_user = self.create_and_active_user(email='not_access_user@gan.com')

        test_datas = [
            {
                "user": user, 
                'req_data': {"name": "test", "owner": not_access_user.id}, 
                'field': "owner",
                'contain': "create or have access to"
            },
            {
                "user": user, 
                'req_data': {"name": "test", "owner": uuid.uuid4()}, 
                'field': "owner"
            },
            {
                "user": user, 
                'req_data': {"name": "test", "members": [not_access_user.id]}, 
                'field': "members",
                'contain': "create or do not have access to as a member"
            },
            {
                "user": user, 
                'req_data': {"name": "test", "owner": access_free_owner.id, "members": [own_owner.id]}, 
                'field': "members",
                'contain': "create or do not have access to as a member"
            },
            {
                "user": user, 
                'req_data': {"name": "test", "members": [uuid.uuid4()]}, 
                'field': "members",
            },
        ]

        for test_data in test_datas:
            current_user = test_data["user"]
            req_data = test_data["req_data"]
            field = test_data["field"]
            contain = test_data.get("contain")
            response = self.auth_post(current_user, req_data)
            self.assertEqual(response.status_code, self.status.HTTP_400_BAD_REQUEST)
            data = self.loads(response.content)
            errors = data.get(field)
            self.assertIsInstance(errors, list)
            if contain:
                self.assertIn(contain, errors[0])
        self.assertEqual(len(Organization.objects.all()), 0)
    
    def test_create_org_with_full_data(self):
        user = self.create_and_active_user()
        own_owner = self.create_and_active_user(email="own_owner@ganil.com", created_by=user)
        access_free_owner = self.create_and_active_user(email="access_free_owner@ganil.com")
        access_free_owner.can_be_accessed_by.add(own_owner)

        data = {
            "name": "test", 
            "owner": own_owner.id, 
            "members": [access_free_owner.id] 
        }

        response = self.auth_post(user, data)
        self.assertEqual(response.status_code, self.status.HTTP_201_CREATED)
        Organization.objects.get(
            name='test', owner=own_owner, created_by=user, members__in=[access_free_owner.id]
        )
        self.assertEqual(len(Organization.objects.all()), 1)
        self.assertEqual(len(self.get_mailbox()), 1)