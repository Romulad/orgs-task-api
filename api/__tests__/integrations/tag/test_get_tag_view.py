import uuid

from ...base_classe import BaseTestClass

class TestGetTagView(BaseTestClass):
    """### Flow
    - user need to be authenticated
    - user get not when ressource does not exist
    - test other user or user in the org without access can not get ressource and get not found error
    - test allow user :
        - org owner
        - org creator and creator of the tag
        - user with `can_be_accessed_by` permission on both org and tag
        - org members
    can get data successfully
    """
    url_name = "tags-detail"

    def setUp(self):
        self.owner, self.creator, self.org = self.create_new_org()
        self.tags = [self.create_new_tag(self.org)[-1] for _ in range(10)]

    def test_only_authenticated_user_can_access(self):
        self.evaluate_method_unauthenticated_request(
            self.HTTP_GET, ["fake-role-id"]
        )
    
    def test_get_tag_not_found(self):
        response = self.auth_get(self.owner, [uuid.uuid4()])
        self.assertEqual(response.status_code, self.status.HTTP_404_NOT_FOUND)
        data = self.loads(response.content).get("detail")
        self.assertIsNotNone(data)
    
    def test_no_allowed_user_can_not_get_tag(self):
        simple_user = self.create_and_activate_random_user()
        another_owner, another_creator, _ = self.create_new_org()

        target_tag = self.tags[0]

        for user in [simple_user, another_owner, another_creator]:
            response = self.auth_get(user, [target_tag.id])
            self.assertEqual(response.status_code, self.status.HTTP_404_NOT_FOUND)
            data = self.loads(response.content).get("detail")
            self.assertIsNotNone(data)
    
    def test_allowed_user_can_get_tag(self):
        can_access_org_user = self.create_and_activate_random_user()
        self.org.can_be_accessed_by.add(can_access_org_user)

        org_member = self.create_and_activate_random_user()
        self.org.members.add(org_member)

        tag_creator = self.create_and_activate_random_user()
        can_access_tag_user = self.create_and_activate_random_user()

        for tag in self.tags:
            tag.can_be_accessed_by.add(can_access_tag_user)
            tag.created_by = tag_creator
            tag.save()

        for index, user in enumerate([
            self.owner, 
            self.creator, 
            can_access_org_user, 
            org_member,
            tag_creator, 
            can_access_tag_user
        ]):
            target_tag = self.tags[index]
            response = self.auth_get(user, [target_tag.id])
            self.assertEqual(response.status_code, self.status.HTTP_200_OK)
            data = self.loads(response.content)
            self.assertEqual(data.get("id"), str(target_tag.id))
            self.assertEqual(data.get("org").get("id"), str(self.org.id))
            self.assertEqual(data.get("name"), target_tag.name)
            self.assertEqual(data.get("description"), target_tag.description)
            self.assertIsInstance(data.get("can_be_accessed_by"), list)
            self.assertIsNotNone(data.get("created_at"))
            self.assertIsNotNone(data.get("created_by"))

