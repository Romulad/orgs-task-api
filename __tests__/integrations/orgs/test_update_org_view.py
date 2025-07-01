import uuid

from ...base_classe import BaseTestClass
from organization.models import Organization

class TestUpdateOrgView(BaseTestClass):
    """### Flow
    - user need to be authenticated
    - other can't update org data only creator or access allowed user can or 404
    - test member can not update data, 403
    - user get not found when obj does not exist
    - name should be validated for unique together with owner
    - test user can't update to owner he has not access to
    - test can't update to owner who doesn't have full access over members
    - test can't update to owner that doesn't exist
    - test can't update to member that doesn't exist
    - test all field should be include
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
    data = {
        "name": "updatename",
        "description": "updatedescription",   
    }

    def setUp(self):
        self.user = self.create_and_activate_random_user()
        self.owner = self.create_and_active_user(email="owner@gmail.com")
        self.creator = self.create_and_activate_random_user()
        orgs_data = [*self.orgs_data]
        for data in orgs_data:
            data["owner"] = self.owner
            data["created_by"] = self.creator
        self.created_data = self.bulk_create_object(Organization, orgs_data)

    def test_only_authenticated_user_can_access(self):
        self.evaluate_method_unauthenticated_request(
            self.HTTP_PUT, ["fake-id"]
        )
    
    def test_user_cant_update_other_user_org(self):
        org = self.created_data[0]
        org.owner = self.user
        org.save()
        response = self.auth_put(self.user, self.data, [self.created_data[1].id])
        self.assertEqual(response.status_code, self.status.HTTP_404_NOT_FOUND)
        self.assertIsNotNone(response.data.get("detail", None))

    def test_member_can_not_update_data(self):
        org = self.created_data[0]
        org.members.add(self.user)
        response = self.auth_put(self.user, self.data, [org.id])
        self.assertEqual(response.status_code, self.status.HTTP_403_FORBIDDEN)
        self.assertIsNotNone(response.data.get("detail", None))
    
    def test_not_found_error(self):
        response = self.auth_put(self.user, self.data, ["fake-id"])
        self.assertEqual(response.status_code, self.status.HTTP_404_NOT_FOUND)
        data = self.loads(response.content)
        self.assertIsNotNone(data.get("detail"))
    
    def test_name_validation_error(self):
        created_org = self.created_data[1]
        
        response = self.auth_put(
            self.owner, 
            {**self.data, "name": created_org.name,
            "members": self.get_ids_from(created_org.members.all()),
            "owner": created_org.owner.id}, 
            [self.created_data[0].id]
        )
        self.assertEqual(response.status_code, self.status.HTTP_400_BAD_REQUEST)
        self.assertIsInstance(response.data.get("name"), list)
        # data don't get updated
        updated_data = Organization.objects.get(id=self.created_data[0].id)
        self.assertEqual(updated_data.name, self.created_data[0].name)
    
    def test_members_validation_error(self):
        self.user.created_by = self.owner
        self.user.save()
        user2 = self.create_and_active_user(email="user2@gmail.com")
        org_data = self.created_data[0]
        
        req_data = {**self.data}
        req_data["members"] = [obj.id for obj in [self.user, user2]]
        req_data["owner"] = org_data.owner.id
        response = self.auth_put(
            self.owner, 
            req_data, 
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
        user = self.create_and_active_user(email="user1@gmail.com", created_by=self.owner)
        user2 = self.create_and_active_user(email="user2@gmail.com")
        user2.can_be_accessed_by.add(self.owner)

        created_data = self.created_data[0]

        req_data = {
            **self.data, "name": created_data.name,
            "members": [obj.id for obj in [user, user2]],
            "owner" : created_data.owner.id
        }
        response = self.auth_put(
            self.owner, 
            req_data, 
            [created_data.id]
        )
        self.assertEqual(response.status_code, self.status.HTTP_200_OK)
        data = self.loads(response.content)
        updated_data = Organization.objects.get(id=created_data.id)
        self.assertEqual(data.get("id"), str(updated_data.id))
        self.assertEqual(data.get("name"), req_data.get("name"))
        self.assertEqual(data.get("description"), req_data.get("description"))
        self.assertEqual(len(data.get("members")), 2)
        # data is updated
        updated_data = Organization.objects.get(id=created_data.id)
        members = updated_data.members.all()
        self.assertEqual(updated_data.name, req_data.get("name"))
        self.assertEqual(updated_data.description, req_data.get("description"))
        self.assertEqual(len(members), 2)
        self.assertIn(user, members)
        # invitation email has been sent
        mailbox = self.get_mailbox()
        to_list = [mail.to[0] for mail in mailbox]
        self.assertEqual(len(mailbox), 2)
        self.assertIn(user.email, to_list)
        self.assertIn(user2.email, to_list)
        self.assertEqual(mailbox[0].subject, "Notification - You have been add to org my org 1")
        
    def test_access_allow_user_can_update_data_and_members(self):
        can_access_user = self.create_and_active_user(email="canaccess@gnail.com")
        user = self.create_and_active_user(
            email="user1@gmail.com", created_by=self.owner)
        user2 = self.create_and_active_user(email="user2@gmail.com")
        user2.can_be_accessed_by.add(self.owner)

        self.created_data[0].members.add(user)
        self.created_data[0].can_be_accessed_by.add(can_access_user)
        
        req_data = {**self.data}
        req_data["members"] = [obj.id for obj in [user, user2]]
        req_data['owner'] = self.created_data[0].owner.id
        response = self.auth_put(
            can_access_user,
            req_data, 
            [self.created_data[0].id]
        )
        self.assertEqual(response.status_code, self.status.HTTP_200_OK)
        data = self.loads(response.content)
        updated_data = Organization.objects.get(id=self.created_data[0].id)
        self.assertEqual(data.get("id"), str(updated_data.id))
        self.assertEqual(data.get("name"), req_data.get("name"))
        self.assertEqual(data.get("description"), req_data.get("description"))
        self.assertEqual(len(data.get("members")), 2)
        # data is updated
        updated_data = Organization.objects.get(id=self.created_data[0].id)
        members = updated_data.members.all()
        self.assertEqual(updated_data.name, req_data.get("name"))
        self.assertEqual(updated_data.description, req_data.get("description"))
        self.assertEqual(len(members), 2)
        self.assertIn(user, members)
        # invitation email has been sent
        mailbox = self.get_mailbox()
        to_list = [mail.to[0] for mail in mailbox]
        self.assertEqual(len(mailbox), 1)
        self.assertEqual(user2.email, to_list[0])
        self.assertEqual(mailbox[0].subject, "Notification - You have been add to org updatename")
    
    def test_change_owner_validation(self):
        new_owner = self.create_and_active_user(
            email="new_owner#@gma.com", created_by=self.owner)
        new_owner2 = self.create_and_active_user(email="new_owner2#@gma.com")
        user = self.create_and_active_user()
        user.can_be_accessed_by.add(self.owner)

        created_org = self.created_data[0]
        created_org.members.add(user)

        test_cases_data = [
            {
               "user": self.owner, 
               "req_data": {
                   "name": "test", 
                   "owner": new_owner2.id,
                   'description': created_org.description,
                    "members": self.get_ids_from(created_org.members.all())
                },
               "field": "owner",
               "contain": "user you didn't create or have access to as owner"
            },
            {
               "user": self.owner, 
               "req_data": {
                   "name": "test", 
                   "owner": new_owner.id,
                   'description': created_org.description,
                    "members": self.get_ids_from(created_org.members.all())
                },
               "field": "members",
               "contain": "user you did not create or do not have access to as a member"
            },
            {
               "user": self.owner, 
               "req_data": {
                   "name": "test", "owner": uuid.uuid4(),
                   'description': created_org.description,
                    "members": self.get_ids_from(created_org.members.all())
                },
               "field": "owner",
            }
        ]

        for test_data in test_cases_data:
            current_user = test_data["user"]
            req_data = test_data['req_data']
            contain = test_data.get('contain')
            field = test_data['field']
            response = self.auth_put(current_user, req_data, [created_org.id])
            self.assertEqual(response.status_code, self.status.HTTP_400_BAD_REQUEST)
            data = self.loads(response.content)
            errors = data.get(field)
            self.assertIsInstance(errors, list)
            if contain:
                self.assertIn(contain, errors[0])
        
    def test_update_data(self):
        new_owner = self.create_and_active_user(
            email="new_owner#@gma.com", created_by=self.owner)
        self.user.can_be_accessed_by.add(self.owner, new_owner)

        created_org = self.created_data[0]
        created_org.members.add(self.user)

        req_data = {
            "name": "test", 
            "owner": new_owner.id,
            'description': created_org.description,
            "members": self.get_ids_from(created_org.members.all())
        }

        response = self.auth_put(self.owner, req_data, [created_org.id])
        self.assertEqual(response.status_code, self.status.HTTP_200_OK)
        data = self.loads(response.content)
        self.assertEqual(data.get('name'), "test")
        self.assertIsNotNone(data.get('description'))
        self.assertEqual(len(data.get('members')), 1)
        self.assertIn(str(self.user.id), data.get('members'))
        self.assertEqual(data.get('owner'), str(new_owner.id))
        self.assertEqual(len(self.get_mailbox()), 0)
    
    def test_all_field_should_be_include(self):
        created_org = self.created_data[0]

        req_data = {
            "name": "test", 
            'description': created_org.description,
            "members": self.get_ids_from(created_org.members.all())
        }

        response = self.auth_put(self.owner, req_data, [created_org.id])
        self.assertEqual(response.status_code, self.status.HTTP_400_BAD_REQUEST)
        data = self.loads(response.content)
        self.assertIsInstance(data.get('owner'), list)
        with self.assertRaises(Organization.DoesNotExist):
            Organization.objects.get(name="test")