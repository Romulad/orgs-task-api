from ...base_classe import BaseTestClass

class TestListTagView(BaseTestClass):
    """### Flow
    - user need to be authenticated
    - test user without access, simple user, any other user can not get any data
    - test user with access:
        - org owner
        - org creator and creator of the tag
        - user with `can_be_accessed_by` permission on both org and tag
        - org members
    can get needed tag data
    - test response is paginated
    - test we can apply filters, e.g a search through filter
    """
    url_name = "tags-list"

    def setUp(self):
        self.owner_user, self.org_creator, self.org = self.create_new_org()
        self.tags = [self.create_new_tag(self.org)[-1] for _ in range(10)]

    def test_only_authenticated_user_can_access(self):
        self.evaluate_method_unauthenticated_request(
            self.HTTP_GET
        )
    
    def test_user_without_access_cant_get_any_ressources(self):
        simple_user = self.create_and_activate_random_user()
        another_owner, another_creator, _ = self.create_new_org()

        for user in [
            simple_user,
            another_owner,
            another_creator,
        ]:
            response = self.auth_get(user)
            self.assertEqual(response.status_code, self.status.HTTP_200_OK)
            data = self.loads(response.content).get("results")
            self.assertEqual(len(data), 0)
    
    def test_user_with_access_can_get_data(self):
        can_access_org_user = self.create_and_activate_random_user()
        self.org.can_be_accessed_by.add(can_access_org_user)

        org_member = self.create_and_activate_random_user()
        self.org.members.add(org_member)
        
        tag_created_by = self.tags[:5]
        tag_creator = self.create_and_activate_random_user()
        can_access_tag_user = self.create_and_activate_random_user()

        for tag in tag_created_by:
            tag.can_be_accessed_by.add(can_access_tag_user)
            tag.created_by = tag_creator
            tag.save()

        for data in [
            (self.owner_user, self.tags),
            (self.org_creator, self.tags),
            (can_access_org_user, self.tags),
            (org_member, self.tags),
            (tag_creator, tag_created_by),
            (can_access_tag_user, tag_created_by)
        ]:
            user, tag_data = data
            response = self.auth_get(user)
            self.assertEqual(response.status_code, self.status.HTTP_200_OK)
            data = self.loads(response.content).get("results")
            self.assertEqual(len(data), len(tag_data))
            d_ids = [str(obj.id) for obj in tag_data]
            for result in data:
                self.assertIn(result["id"], d_ids)
                self.assertIsNotNone(result.get("name"))
                self.assertIsNone(result.get("description", 'none'))
                self.assertIsNotNone(result.get("created_at"))
                self.assertIsNotNone(result.get("created_by"))
    
    def test_data_can_be_filtered(self):
        target_tag = self.tags[0]
        target_tag.name = "test_tag"
        target_tag.save()

        response = self.auth_get(self.owner_user, query_params={"name": "test_tag"})
        self.assertEqual(response.status_code, self.status.HTTP_200_OK)
        data = self.loads(response.content).get("results")
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0].get("id"), str(target_tag.id))
        self.assertEqual(data[0].get("name"), target_tag.name)
    
    def test_can_be_filtered_with_search(self):
        target_tag = self.tags[0]
        target_tag.name = "google_tag"
        target_tag.save()

        response = self.auth_get(self.owner_user, query_params={"search": "google"})
        self.assertEqual(response.status_code, self.status.HTTP_200_OK)
        data = self.loads(response.content).get("results")
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0].get("id"), str(target_tag.id))
        self.assertEqual(data[0].get("name"), target_tag.name)