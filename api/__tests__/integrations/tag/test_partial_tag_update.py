import uuid

from ...base_classe import BaseTestClass
from app_lib.app_permssions import CAN_CREATE_TAG

class TestPartialUpdateTagView(BaseTestClass):
    """### Flow
    - user need to be authenticated
    - test user get not found when ressource does not exist
    - test not access allowed user:
        - other user or other org user - 404 not found
        - org member only without permission - 403 forbidden
        - any other user existing in the org but without explicit permission - 404 not found
    should not be able to update data
    - test data validation: (instance already exists, field can be sent in any combination)
        - name if specified:
            - should not be empty
            - if name is same as the current instance name, no validation need to take place
            - if name is different:
                - should be validate against the tag org to be unique
                - if new org is included in req data then the name should be validate against the new org
        - org if specified:
            - org id should be a valid id
            - if org id same as the current tag instance org id, no validation needed
            - if different:
                - user making the request should has access to the org
                - if `name`, not in req data, intance tag name should be validate against the new org
                to avoid same tag with same name in the new org
    - test user with access:
        - org owner
        - org creator and tag creator
        - user in `can_be_accessed_by` on both org and tag
    can update tag data successfully
    - test response data is valid
    """
    url_name = "tags-detail"

    def setUp(self):
        self.owner_user, self.org_creator, self.org = self.create_new_org()
        self.tag_creator, self.target_tag = self.create_new_tag(self.org)
        self.tags = [self.create_new_tag(self.org)[-1] for _ in range(10)]

    def test_only_authenticated_user_can_access(self):
        self.evaluate_method_unauthenticated_request(
            self.HTTP_PATCH, ["fake-tag-id"]
        )
    
    def test_not_found_when_tag_does_not_exist(self):
        response = self.auth_patch(self.owner_user, {}, [uuid.uuid4()])
        self.assertEqual(response.status_code, self.status.HTTP_404_NOT_FOUND)
        data = self.loads(response.content)
        self.assertIsNotNone(data.get("detail"))
    
    def test_not_access_allowed_user_cant_update_tag(self):
        user_with_create_perm, _, perm_obj = self.create_new_permission(self.org)
        perm_obj.add_permissions(CAN_CREATE_TAG)

        simple_user = self.create_and_activate_random_user()
        another_owner, another_creator, _ = self.create_new_org()

        depart_creator, depart = self.create_new_depart(self.org)
        can_access_depart_user = self.create_and_activate_random_user()
        depart.can_be_accessed_by.add(can_access_depart_user)

        req_data = {"name": "new_tag_name"}

        for user in [
            simple_user,
            another_owner,
            another_creator,
            depart_creator,
            can_access_depart_user,
            user_with_create_perm
        ]:
            response = self.auth_patch(user, req_data, [self.target_tag.id])
            self.assertEqual(response.status_code, self.status.HTTP_404_NOT_FOUND)
            data = self.loads(response.content)
            self.assertIsNotNone(data.get("detail"))
        with self.assertRaises(self.target_tag.__class__.DoesNotExist):
            self.target_tag.__class__.objects.get(name=req_data["name"])
    
    def test_org_member_without_permission_cant_update_tag(self):
        org_member = self.create_and_activate_random_user()
        self.org.members.add(org_member)

        req_data = {"name": "new_tag_name"}

        response = self.auth_patch(org_member, req_data, [self.target_tag.id])
        self.assertEqual(response.status_code, self.status.HTTP_403_FORBIDDEN)
        data = self.loads(response.content)
        self.assertIsNotNone(data.get("detail"))
        with self.assertRaises(self.target_tag.__class__.DoesNotExist):
            self.target_tag.__class__.objects.get(name=req_data["name"])
        
    def test_name_validation(self):
        _, _, org = self.create_new_org()
        _, new_tag = self.create_new_tag(org, "tag_in_new_org_name")
        # allow the default owner can have access to the new org to allow 
        # to focus on name validation
        org.can_be_accessed_by.add(self.owner_user)

        test_data = [
            {
                "name": ""
            },
            {
                "name": self.tags[0].name # tag name already exist in the target tag org
            },
            {
                "name": new_tag.name, # tag name already exist in the specified org
                "org": org.id
            },
        ]
        for req_data in test_data:
            response = self.auth_patch(self.owner_user, req_data, [self.target_tag.id])
            self.assertEqual(response.status_code, self.status.HTTP_400_BAD_REQUEST)
            errors = self.loads(response.content).get("name")
            self.assertIsInstance(errors, list)

        old_name = self.target_tag.name
        self.target_tag.refresh_from_db()
        self.assertEqual(old_name, self.target_tag.name)
        self.assertEqual(self.target_tag.org.id, self.org.id)

    def test_same_name_validation(self):
        response = self.auth_patch(
            self.owner_user, 
            {"name": self.target_tag.name}, 
            [self.target_tag.id]
        )
        self.assertEqual(response.status_code, self.status.HTTP_200_OK)
        data = self.loads(response.content)
        self.assertEqual(data.get("org"), str(self.org.id))
    
    def test_org_validation(self):
        new_org_owner, _, org = self.create_new_org()
        # create a tag with same name with the target tag in the new org, for name validation at
        # the org level
        self.create_new_tag(org, self.target_tag.name)
        # give the new org owner access to the target tag org so he can be able to act on the tag
        self.org.can_be_accessed_by.add(new_org_owner)

        test_data = [
            {
                "org": uuid.uuid4()
            },
            {
                # simulate the fact that the default tag org owner does not have access to the new org
                # so even if he has access to the tag data he can not change it org to the new org
                "org": org.id
            },
            {
                # here the user making the request has a full access over the tag and even the new
                # specified org as he is the org owner, but the new org specified 
                # already has a tag with a name same as the target tag
                "org": org.id,
                "current_user": new_org_owner
            }
        ]
        for req_data in test_data:
            user = req_data.pop("current_user", self.owner_user)
            response = self.auth_patch(user, req_data, [self.target_tag.id])
            self.assertEqual(response.status_code, self.status.HTTP_400_BAD_REQUEST)
            errors = self.loads(response.content).get("org")
            self.assertIsInstance(errors, list)

        self.target_tag.refresh_from_db()
        self.assertEqual(self.target_tag.org.id, self.org.id)
    
    def test_user_with_access_can_update_tag(self):
        can_access_org_user = self.create_and_activate_random_user()
        self.org.can_be_accessed_by.add(can_access_org_user)

        org_member_with_perm = self.create_and_activate_random_user()
        self.org.members.add(org_member_with_perm)
        self.org.can_be_accessed_by.add(org_member_with_perm)
 
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
            org_member_with_perm,
            tag_creator,
            can_access_tag_user
        ]

        req_data = {
            "org": self.org.id,
            "description": "test"
        }

        for index, user in enumerate(users):
            target_tag = self.tags[index]
            response = self.auth_patch(user, req_data, [target_tag.id])
            self.assertEqual(response.status_code, self.status.HTTP_200_OK)
            data = self.loads(response.content)
            self.assertEqual(data.get("id"), str(target_tag.id))
            self.assertEqual(data.get("name"), target_tag.name)
            self.assertEqual(data.get("org"), str(self.org.id))
            self.assertEqual(data.get("description"), 'test')
            self.assertIsNotNone(data.get("created_at"))
            self.assertIsInstance(data.get("can_be_accessed_by"), list)
            # tag has been updated
            self.assertIsNotNone(
                target_tag.__class__.objects.get(id=target_tag.id, description='test')
            )