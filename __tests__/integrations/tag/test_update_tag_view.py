import uuid

from ...base_classe import BaseTestClass
from django.forms.models import model_to_dict


class TestUpdateTagView(BaseTestClass):
    """### Flow
    - user need to be authenticated
    - test user get not found when ressource does not exist
    - test not access allowed user:
        - other user or org user - 404 not found
        - org member only without permission - 403 forbidden
        - any other user existing in the org but without explicit permission - 404 not found
    should not be able to update data
    - test all fields should be present in the request data
    - test data validation: (instance already exists)
        - name:
            - field is required
            - should not be empty
            - if name in request data different from instance namme it should be validated 
            to be unique for the tag within the org
        - description:
            - field is required
        - org:
            - field is required
            - org id should be a valid id
            - if org id differnt from instance org id user making the request should have permission 
            to act on the new specified org       
    - test user with access:
        - org owner
        - org creator and creator of the tag
        - user with `can_be_accessed_by` permission on both org and tag
    can update tag data successfully.
    - test response data is valid and data is updated
    """
    url_name = "tags-detail"

    def setUp(self):
        self.owner_user, self.org_creator, self.org = self.create_new_org()
        self.tag_creator, self.target_tag = self.create_new_tag(self.org)
        self.tags = [self.create_new_tag(self.org)[-1] for _ in range(10)]
        self.req_data = model_to_dict(
            self.target_tag, 
            fields=["name", "description", "org"]
        )
        self.req_data["description"] = ''

    def test_only_authenticated_user_can_access(self):
        self.evaluate_method_unauthenticated_request(
            self.HTTP_PUT, ["fake-tag-id"]
        )
    
    def test_not_found_when_tag_does_not_exist(self):
        response = self.auth_put(self.owner_user, self.req_data, [uuid.uuid4()])
        self.assertEqual(response.status_code, self.status.HTTP_404_NOT_FOUND)
        data = self.loads(response.content)
        self.assertIsNotNone(data.get("detail"))
    
    def test_not_access_allowed_user_cant_update_tag(self):
        simple_user = self.create_and_activate_random_user()
        another_owner, another_creator, _ = self.create_new_org()

        depart_creator, depart = self.create_new_depart(self.org)
        can_access_depart_user = self.create_and_activate_random_user()
        depart.can_be_accessed_by.add(can_access_depart_user)

        self.req_data["name"] = "new_tag_name"

        for user in [
            simple_user,
            another_owner,
            another_creator,
            depart_creator,
            can_access_depart_user
        ]:
            response = self.auth_put(user, self.req_data, [self.target_tag.id])
            self.assertEqual(response.status_code, self.status.HTTP_404_NOT_FOUND)
            data = self.loads(response.content)
            self.assertIsNotNone(data.get("detail"))
        with self.assertRaises(self.target_tag.__class__.DoesNotExist):
            self.target_tag.__class__.objects.get(name=self.req_data["name"])
    
    def test_org_member_without_permission_cant_update_tag(self):
        org_member = self.create_and_activate_random_user()
        self.org.members.add(org_member)

        self.req_data["name"] = "new_tag_name"

        response = self.auth_put(org_member, self.req_data, [self.target_tag.id])
        self.assertEqual(response.status_code, self.status.HTTP_403_FORBIDDEN)
        data = self.loads(response.content)
        self.assertIsNotNone(data.get("detail"))
        with self.assertRaises(self.target_tag.__class__.DoesNotExist):
            self.target_tag.__class__.objects.get(name=self.req_data["name"])
    
    def test_name_validation(self):
        del self.req_data["name"]

        test_data = [
            {
                **self.req_data,
            },
            {
                **self.req_data,
                "name": "",
            },
            {
                **self.req_data,
                "name": self.tags[0].name, # the tag already exist in the org error test
            }
        ]
        for req_data in test_data:
            response = self.auth_put(self.owner_user, req_data, [self.target_tag.id])
            self.assertEqual(response.status_code, self.status.HTTP_400_BAD_REQUEST)
            errors = self.loads(response.content).get("name")
            self.assertIsInstance(errors, list)
    
    def test_same_name_validation(self):
        self.req_data["perms"] = []
        response = self.auth_put(self.owner_user, self.req_data, [self.target_tag.id])
        self.assertEqual(response.status_code, self.status.HTTP_200_OK)
        data = self.loads(response.content)
        self.assertEqual(data.get("org"), str(self.org.id))
    
    def test_description_validation(self):
        del self.req_data["description"]
        response = self.auth_put(self.owner_user, self.req_data, [self.target_tag.id])
        self.assertEqual(response.status_code, self.status.HTTP_400_BAD_REQUEST)
        errors = self.loads(response.content).get("description")
        self.assertIsInstance(errors, list)
    
    def test_org_validation(self):
        del self.req_data["org"]
        _, _, new_org = self.create_new_org()

        test_data = [
            self.req_data,
            {
                **self.req_data,
                "org": uuid.uuid4()
            },
            {
                **self.req_data,
                "org": new_org.id, # org is valid but user does not have access to it
            }
        ]
        for req_data in test_data:
            response = self.auth_put(self.owner_user, req_data, [self.target_tag.id])
            self.assertEqual(response.status_code, self.status.HTTP_400_BAD_REQUEST)
            errors = self.loads(response.content).get("org")
            self.assertIsInstance(errors, list)
        with self.assertRaises(self.target_tag.__class__.DoesNotExist):
            self.target_tag.__class__.objects.get(org__id=new_org.id)

    def test_only_new_org_specified_is_validated_against_user(self):
        response = self.auth_put(self.tag_creator, self.req_data, [self.target_tag.id])
        self.assertEqual(response.status_code, self.status.HTTP_200_OK)
        data = self.loads(response.content)
        self.assertEqual(data.get("org"), str(self.org.id))
        
    def test_user_with_access_can_update_tag(self):
        can_access_org_user = self.create_and_activate_random_user()
        self.org.can_be_accessed_by.add(can_access_org_user)
 
        tag_creator = self.create_and_activate_random_user()
        can_access_tag_user = self.create_and_activate_random_user()

        for tag in self.tags:
            tag.created_by = tag_creator
            tag.save()
            tag.can_be_accessed_by.add(can_access_tag_user)

        users = [
            self.owner_user,
            self.org_creator,
            can_access_org_user,
            tag_creator,
            can_access_tag_user
        ]

        self.req_data["name"] = "new_tag_name"
        self.req_data["org"] = self.org.id

        for index, user in enumerate(users):
            target_tag = self.tags[index]
            self.req_data["name"] = f"{self.req_data['name']}_{index}"
            response = self.auth_put(user, self.req_data, [target_tag.id])
            self.assertEqual(response.status_code, self.status.HTTP_200_OK)
            data = self.loads(response.content)
            self.assertEqual(data.get("id"), str(target_tag.id))
            self.assertEqual(data.get("name"), self.req_data["name"])
            self.assertEqual(data.get("org"), str(self.org.id))
            self.assertEqual(data.get("description"), self.req_data["description"])
            self.assertIsNotNone(data.get("created_at"))
            self.assertIsInstance(data.get("can_be_accessed_by"), list)
            # tag has been updated with new name
            self.assertIsNotNone(
                target_tag.__class__.objects.get(
                    id=target_tag.id, name=self.req_data["name"], org=self.org
                )
            )