import uuid

from ...base_classe import BaseTestClass
from tags.models import Tag

class TestCreateTagView(BaseTestClass):
    """### Flow
    - user need to be authenticated
    - test data validation:
        - name:
            - field is required
            - should a valid name
            - tag name should be unique within the org
        - org:
            - field is required
            - org id should be a valid id
            - user making the request should have permission to act on the org
    - test org `owner`, `creator` or `can_be_accessed_by` can create tag within 
    the org successfully with `created_by` attr set.
    """
    url_name = "tags-list"

    def setUp(self):
        self.owner, self.creator, self.org = self.create_new_org()
    
    def assert_no_more_role_created(self, should_exist_count=0):
        self.assertEqual(
            len(
                Tag.objects.all()
            ),
            should_exist_count
        )

    def test_only_authenticated_user_can_access(self):
        self.evaluate_method_unauthenticated_request(
            self.HTTP_POST
        )
    
    def test_name_field_validation(self):
        _, tag = self.create_new_tag(self.org)
        test_data = [
            {
                "org": self.org.id
            },
            {
                "org": self.org.id,
                "name": "",
            },
            {
                "org": self.org.id,
                "name": tag.name,
            }
        ]
        for req_data in test_data:
            response = self.auth_post(self.owner, req_data)
            self.assertEqual(response.status_code, self.status.HTTP_400_BAD_REQUEST)
            errors = self.loads(response.content).get("name")
            self.assertIsInstance(errors, list)
        self.assert_no_more_role_created(1)
    
    def test_org_validation(self):
        test_data = [
            {
                "name": "test"
            },
            {
                "name": "test",
                "org": uuid.uuid4()
            },
            {
                "name": "test",
                "org": self.org.id,
                'current_user': self.create_and_activate_random_user()
            }
        ]
        for req_data in test_data:
            user = req_data.pop("current_user", self.owner)
            response = self.auth_post(user, req_data)
            self.assertEqual(response.status_code, self.status.HTTP_400_BAD_REQUEST)
            errors = self.loads(response.content).get("org")
            self.assertIsInstance(errors, list)
        self.assert_no_more_role_created(0)

    def test_successfull_tag_creation(self):
        can_access_org_user = self.create_and_activate_random_user()
        self.org.can_be_accessed_by.add(can_access_org_user)

        for user in [
            can_access_org_user,
            self.owner,
            self.creator
        ]:
            req_data = {
                "name": user.email,
                "org": self.org.id
            }
            response = self.auth_post(user, req_data)
            self.assertEqual(response.status_code, self.status.HTTP_201_CREATED)
            data = self.loads(response.content)
            self.assertEqual(data.get("name"), user.email)
            self.assertEqual(data.get("org"), str(self.org.id))
            self.assertIsNone(data.get("description", "None"))
            self.assertIsInstance(data.get("can_be_accessed_by"), list)
            # tag has been created with created_by set
            self.assertIsNotNone(
                Tag.objects.get(name=user.email, org=self.org, created_by=user)
            )