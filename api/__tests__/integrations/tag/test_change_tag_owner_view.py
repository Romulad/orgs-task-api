import uuid

from ...base_classe import BaseTestClass
from app_lib.app_permssions import CAN_CHANGE_RESSOURCES_OWNERS


class TestChangeTagOwnerView(BaseTestClass):
    """### Flow
    - user need to be authenticated
    - test user get not found when ressource doesn't exist
    - test user with:
        - access allowed on org (owner, can_be_accessed_by) can not change tag owner users, 403
        - user with access allowed on tag can't change tag owner users, 403
        - simple org member can not change tag owners, 403
        - test other user can't change tag owners, 404
    - validate owner user ids provide:
        - ids should exist
        - user that is making the request should have a full access over owner users specified
    - test org creator or tag creator can change tag owner users
    - owners are successfully added to obj can_be_accessed_by list after request
    """
    url_name = "tags-change-owners"

    def setUp(self):
        self.owner_user, self.org_creator, self.org = self.create_new_org()
        _, self.tag = self.create_new_tag(self.org)
        self.Tag = self.tag.__class__
        self.simple_user = self.create_and_activate_random_user()
    
    def test_only_authenticated_user_can_access(self):
        self.evaluate_method_unauthenticated_request(
            self.HTTP_POST, ['fake_id']
        )
    
    def test_not_found_tag(self):
        response = self.auth_post(self.owner_user, {}, [uuid.uuid4()])
        self.assertEqual(response.status_code, self.status.HTTP_404_NOT_FOUND)
        # check response data
        data = self.loads(response.content)
        self.assertIsNotNone(data.get("detail"))
    
    def test_no_creator_user_cant_update_tag_access_list(self):
        self.org.can_be_accessed_by.add(self.simple_user)
        
        org_member = self.create_and_activate_random_user()
        self.org.members.add(org_member)

        can_access_tag = self.create_and_activate_random_user()
        self.tag.can_be_accessed_by.add(can_access_tag)

        user_to_add = self.create_and_activate_random_user()
        user_to_add.can_be_accessed_by.add(
            self.owner_user, self.simple_user, can_access_tag, org_member
        )

        for user in [
            self.owner_user,
            self.simple_user,
            org_member,
            can_access_tag
        ]:
            response = self.auth_post(
                user, {"owner_ids": [user_to_add.id]}, [self.tag.id]
            )
            self.assertEqual(response.status_code, self.status.HTTP_403_FORBIDDEN)
            # obj access list still 1
            self.tag.refresh_from_db()
            self.assertEqual(
                len(self.tag.can_be_accessed_by.all()), 1
            )
    
    def test_other_user_cant_update_task_access_list(self):
        depart_creator, depart = self.create_new_depart(self.org)
        can_access_depart_user = self.create_and_activate_random_user()
        depart.can_be_accessed_by.add(can_access_depart_user)

        other_org_owner, other_org_creator, _ = self.create_new_org()

        users = [
            self.simple_user,
            can_access_depart_user,
            depart_creator,
            other_org_owner,
            other_org_creator
        ]

        user_to_add = self.create_and_activate_random_user()
        user_to_add.can_be_accessed_by.add(*users)

        for user in users:
            response = self.auth_post(
                user, {"owner_ids": [user_to_add.id]}, [self.tag.id]
            )
            self.assertEqual(response.status_code, self.status.HTTP_404_NOT_FOUND)
            # check response data
            data = self.loads(response.content)
            self.assertIsNotNone(data.get("detail"))
            # obj access list still empty
            self.tag.refresh_from_db()
            self.assertEqual(
                len(self.tag.can_be_accessed_by.all()), 0
            )
    
    def test_req_data_validation_ids(self):
        test_datas = [
            {},
            {"owner_ids": []},
            {"owner_ids": [uuid.uuid4(), uuid.uuid4()]},
            # this simulate the fact that the user making request to change tag access list
            # does not have access to the user specified
            {"owner_ids": [self.simple_user.id]}
        ]

        for test_data in test_datas:
            response = self.auth_post(self.org_creator, test_data, [self.tag.id])
            self.assertEqual(response.status_code, self.status.HTTP_400_BAD_REQUEST)
            self.assertIsNotNone(response.data.get("owner_ids", None))
            self.assertIsInstance(response.data.get("owner_ids"), list)
        self.assertEqual(
            len(self.Tag.objects.get(id=self.tag.id).can_be_accessed_by.all()), 0
        )

    def test_creators_can_update_access_list(self):
        tag_creator = self.create_and_activate_random_user()
        self.tag.created_by = tag_creator
        self.tag.save()

        self.simple_user.can_be_accessed_by.add(
            self.org_creator, tag_creator
        )

        req_data = {
            "owner_ids": [self.simple_user.id]
        }

        for user in [
            self.org_creator,
            tag_creator,
        ]:
            response = self.auth_post(user, req_data, [self.tag.id])
            self.assertEqual(response.status_code, self.status.HTTP_204_NO_CONTENT)
            self.tag.refresh_from_db()
            access_allowed = self.tag.can_be_accessed_by.all()
            self.assertEqual(len(access_allowed), 1)
            self.assertIn(self.simple_user, access_allowed)
            # reset for next user
            self.tag.can_be_accessed_by.clear()
    
    def test_user_with_perm_can_change_owners(self):
        user_with_perm, _, perm_obj = self.create_new_permission(self.org)
        perm_obj.add_permissions(CAN_CHANGE_RESSOURCES_OWNERS)

        self.simple_user.can_be_accessed_by.add(user_with_perm)

        req_data = {
            "owner_ids": [self.simple_user.id]
        }

        response = self.auth_post(user_with_perm, req_data, [self.tag.id])
        self.assertEqual(response.status_code, self.status.HTTP_204_NO_CONTENT)
        self.tag.refresh_from_db()
        access_allowed = self.tag.can_be_accessed_by.all()
        self.assertEqual(len(access_allowed), 1)
        self.assertIn(self.simple_user, access_allowed)