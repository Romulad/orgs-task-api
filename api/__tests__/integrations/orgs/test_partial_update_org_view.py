import uuid

from ...base_classe import BaseTestClass
from organization.models import Organization

class TestPartialUpdateOrgView(BaseTestClass):
    """### Flow
    - user need to be authenticated
    - other can't update data including org member only creator or access allowed user can or 404
    - user get not found when obj does not exist
    - name should be validated for unique together with owner
    - member ids should be only user created by owner user otherwise 400 validation error
    - test user can change org owner when he has full member access
    - test user can't change to owner user he doesn't have access to
    - test user can't change to owner user who doesn't have full access over existed members
    - test user can't change to owner user who doesn't have full access over req data members
    - test change owner user with not found error 
    - user can update datas and get good response and updated in db
    - invitation email should be sent to new users added
    """
    url_name = "orgs-detail"
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
        self.simple_user = self.create_and_activate_random_user()
        self.owner = self.create_and_activate_random_user()
        self.creator = self.create_and_activate_random_user()
        orgs_data = [*self.orgs_data]
        for data in orgs_data:
            data["owner"] = self.owner
            data["created_by"] = self.creator
        self.created_data = self.bulk_create_object(Organization, orgs_data)

    def test_only_authenticated_user_can_access(self):
        self.evaluate_method_unauthenticated_request(
            self.HTTP_PATCH, ["fake-id"]
        )
    
    def test_user_cant_update_other_user_org(self):
        response = self.auth_patch(self.simple_user, {"name": "name"}, [self.created_data[1].id])
        self.assertEqual(response.status_code, self.status.HTTP_404_NOT_FOUND)
        self.assertIsNotNone(response.data.get("detail", None))
    
    def test_member_cant_update_org(self):
        org = self.created_data[0]
        org.members.add(self.simple_user)
        response = self.auth_patch(self.simple_user, {"name": "name"}, [org.id])
        self.assertEqual(response.status_code, self.status.HTTP_403_FORBIDDEN)
        self.assertIsNotNone(response.data.get("detail", None))
    
    def test_not_found_error(self):
        response = self.auth_patch(self.owner, {"name": "name"}, ["fake-id"])
        self.assertEqual(response.status_code, self.status.HTTP_404_NOT_FOUND)
        data = self.loads(response.content)
        self.assertIsNotNone(data.get("detail"))
    
    def test_name_validation_error(self):
        response = self.auth_patch(
            self.owner, 
            {"name": self.created_data[1].name}, 
            [self.created_data[0].id]
        )
        self.assertEqual(response.status_code, self.status.HTTP_400_BAD_REQUEST)
        self.assertIsInstance(response.data.get("name"), list)
        # data don't get updated
        updated_data = Organization.objects.get(id=self.created_data[0].id)
        self.assertEqual(updated_data.name, self.created_data[0].name)
    
    def test_members_validation_error(self):
        user = self.create_and_activate_random_user()
        user.created_by = self.owner
        user.save()
        user2 = self.create_and_activate_random_user()
        org_data = self.created_data[0]

        response = self.auth_patch(
            self.owner, 
            {"members": [obj.id for obj in [user, user2]]}, 
            [org_data.id]
        )
        self.assertEqual(response.status_code, self.status.HTTP_400_BAD_REQUEST)
        self.assertIsInstance(response.data.get("members"), list)
        # data don't get updated
        updated_data = Organization.objects.get(id=org_data.id)
        self.assertEqual(updated_data.name, org_data.name)
        self.assertEqual(updated_data.description, org_data.description)
        self.assertEqual(len(updated_data.members.all()), 0)

    def test_user_can_update_data_and_invitation_sent(self):
        user = self.create_and_activate_random_user()
        user.created_by = self.owner
        user.save()
        user2 = self.create_and_activate_random_user()
        user2.can_be_accessed_by.add(self.owner)

        org_data = self.created_data[0]
        org_data.members.add(user)
        
        response = self.auth_patch(
            self.owner,
            {"members": [obj.id for obj in [user, user2]]}, 
            [org_data.id]
        )
        self.assertEqual(response.status_code, self.status.HTTP_200_OK)
        data = self.loads(response.content)
        updated_data = Organization.objects.get(id=org_data.id)
        self.assertEqual(data.get("id"), str(updated_data.id))
        self.assertEqual(len(data.get("members")), 2)
        # data is updated
        updated_data = Organization.objects.get(id=org_data.id)
        members = updated_data.members.all()
        self.assertEqual(len(members), 2)
        self.assertIn(user2, members)
        # invitation email has been sent
        mailbox = self.get_mailbox()
        to_list = [mail.to[0] for mail in mailbox]
        self.assertEqual(len(mailbox), 1)
        self.assertEqual(user2.email, to_list[0])
        self.assertEqual(mailbox[0].subject, "Notification - You have been add to org my org 1")
    
    def test_access_allow_user_can_update_data_and_members(self):
        can_access_org_user = self.create_and_activate_random_user()
        user = self.create_and_activate_random_user()
        user.created_by = self.owner
        user.save()
        user2 = self.create_and_activate_random_user()
        user2.can_be_accessed_by.add(self.owner)

        org_data = self.created_data[0]
        org_data.can_be_accessed_by.add(can_access_org_user)
        
        members_ids = [str(obj.id) for obj in [user, user2]]
        response = self.auth_patch(
            can_access_org_user,
            {"members": members_ids}, 
            [org_data.id]
        )
        self.assertEqual(response.status_code, self.status.HTTP_200_OK)
        data = self.loads(response.content)
        updated_data = Organization.objects.get(id=org_data.id)
        self.assertEqual(data.get("id"), str(updated_data.id))
        self.assertIsInstance(data.get("members"), list)
        self.assertEqual(len(data.get("members")), len(members_ids))
        for data in data.get("members"):
            self.assertIn(data["id"], members_ids)
            self.assertIsNotNone(data["email"])
        # data is updated
        updated_data = Organization.objects.get(id=org_data.id)
        members = updated_data.members.all()
        self.assertEqual(len(members), 2)
        self.assertIn(user2, members)
        # invitation email has been sent
        mailbox = self.get_mailbox()
        to_list = [mail.to[0] for mail in mailbox]
        self.assertEqual(len(mailbox), 2)
        self.assertIn(user2.email, to_list)
        self.assertEqual(mailbox[0].subject, "Notification - You have been add to org my org 1")
    
    def test_change_owner_validation(self):
        new_owner = self.create_and_active_user(
            email="new_owner#@gma.com", created_by=self.owner
        )
        new_owner2 = self.create_and_activate_random_user()
        self.simple_user.can_be_accessed_by.add(self.owner)
        user1 = self.create_and_active_user('user1@gmail.com', created_by=self.owner)
        created_org = self.created_data[0]
        created_org.members.add(self.simple_user)

        test_cases_data = [
            {
               "user": self.owner, 
               "req_data": {
                   "owner": new_owner2.id,
                },
               "field": "owner",
               "contain": "user you didn't create or have access to as owner"
            },
            {
               "user": self.owner, 
               "req_data": {
                   "owner": new_owner.id,
                },
               "field": "members",
               "contain": "user you did not create or do not have access to as a member"
            },
            {
               "user": self.owner, 
               "req_data": {
                   "owner": new_owner.id, 
                   "members": [self.simple_user.id, user1.id],
                },
               "field": "members",
               "contain": "user you did not create or do not have access to as a member",
               "before_req": lambda: self.simple_user.can_be_accessed_by.add(new_owner)
            },
            {
               "user": self.owner, 
               "req_data": {
                   "owner": uuid.uuid4(),
                },
               "field": "owner",
            }
        ]

        for test_data in test_cases_data:
            current_user = test_data["user"]
            req_data = test_data['req_data']
            contain = test_data.get('contain')
            field = test_data['field']
            if (fn := test_data.get("before_req", None)):
                fn()
            response = self.auth_patch(current_user, req_data, [created_org.id])
            self.assertEqual(response.status_code, self.status.HTTP_400_BAD_REQUEST)
            data = self.loads(response.content)
            errors = data.get(field)
            self.assertIsInstance(errors, list)
            if contain:
                self.assertIn(contain, errors[0])
        
    def test_success_owner_update(self):
        new_owner = self.create_and_active_user(
            email="new_owner#@gma.com", created_by=self.owner
        )
        self.simple_user.can_be_accessed_by.add(self.owner, new_owner)
        user1 = self.create_and_active_user('user1@gmail.com', created_by=self.owner)
        user1.can_be_accessed_by.add(new_owner)

        created_org = self.created_data[0]
        created_org.members.add(self.simple_user)

        member_ids = [str(self.simple_user.id), str(user1.id)]
        req_data = {
            "owner": new_owner.id, 
            "members": member_ids,
        }
        response = self.auth_patch(self.owner, req_data, [created_org.id])
        self.assertEqual(response.status_code, self.status.HTTP_200_OK)
        data = self.loads(response.content)
        self.assertIsNotNone(data.get('name'))
        self.assertIsNotNone(data.get('description'))
        self.assertEqual(len(data.get('members')), len(member_ids))
        for obj in data.get('members'):
            self.assertIn(obj["id"], member_ids)
            self.assertIsNotNone(obj["email"])
        self.assertEqual(data.get('owner'), str(new_owner.id))
        self.assertEqual(len(self.get_mailbox()), 1)