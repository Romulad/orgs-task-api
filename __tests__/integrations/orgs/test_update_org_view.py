
from ..base_classe import BaseTestClass
from organization.models import Organization

class TestUpdateOrgView(BaseTestClass):
    """### Flow
    - user need to be authenticated
    - other can't update user data only creator or access allowed user can or 404
    - user get not found when obj does not exist
    - name should be validated for unique together with owner
    - member ids should be only user created by owner user otherwise 400 validation error
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

    def test_only_authenticated_user_can_access(self):
        self.evaluate_method_unauthenticated_request(
            self.HTTP_PUT, ["fake-id"]
        )
    
    def test_user_cant_update_other_user_org(self):
        user = self.create_and_active_user()
        owner = self.create_and_active_user(email="owner@gmail.com")

        orgs_data = [*self.orgs_data]
        orgs_data[0]["owner"] = user
        for data in orgs_data[1:]:
            data["owner"] = owner
        created_data = self.bulk_create_object(Organization, orgs_data)
        
        response = self.auth_put(user, self.data, [created_data[1].id])
        self.assertEqual(response.status_code, self.status.HTTP_404_NOT_FOUND)
        self.assertIsNotNone(response.data.get("detail", None))
    
    def test_not_found_error(self):
        user = self.create_and_active_user()
        response = self.auth_put(user, self.data, ["fake-id"])
        self.assertEqual(response.status_code, self.status.HTTP_404_NOT_FOUND)
        data = self.loads(response.content)
        self.assertIsNotNone(data.get("detail"))
    
    def test_name_validation_error(self):
        user = self.create_and_active_user()
        orgs_data = [*self.orgs_data]
        for data in orgs_data:
            data["owner"] = user
        created_data = self.bulk_create_object(Organization, orgs_data)
        
        response = self.auth_put(
            user, 
            {"name": created_data[1].name}, 
            [created_data[0].id]
        )
        self.assertEqual(response.status_code, self.status.HTTP_400_BAD_REQUEST)
        self.assertIsInstance(response.data.get("name"), list)
        # data don't get updated
        updated_data = Organization.objects.get(id=created_data[0].id)
        self.assertEqual(updated_data.name, created_data[0].name)
    
    def test_members_validation_error(self):
        owner = self.create_and_active_user()
        user = self.create_and_active_user(email="user1@gmail.com", created_by=owner)
        user2 = self.create_and_active_user(email="user2@gmail.com")
        org_data = self.orgs_data[0]
        org_data["owner"] = owner
        created_data = self.bulk_create_object(Organization, [org_data])
        
        req_data = {**self.data}
        req_data["members"] = [obj.id for obj in [user, user2]]
        response = self.auth_put(
            owner, 
            req_data, 
            [created_data[0].id]
        )
        self.assertEqual(response.status_code, self.status.HTTP_400_BAD_REQUEST)
        self.assertIsInstance(response.data.get("members"), list)
        # data don't get updated
        updated_data = Organization.objects.get(id=created_data[0].id)
        self.assertEqual(updated_data.name, created_data[0].name)
        self.assertEqual(updated_data.description, created_data[0].description)
        self.assertEqual(len(updated_data.members.all()), 0)

    def test_user_can_update_data_and_invitation_sent(self):
        owner = self.create_and_active_user()
        user = self.create_and_active_user(email="user1@gmail.com", created_by=owner)
        user2 = self.create_and_active_user(email="user2@gmail.com")
        user2.can_be_accessed_by.add(owner)

        org_data = self.orgs_data[0]
        org_data["owner"] = owner
        created_data = self.bulk_create_object(Organization, [org_data])
        
        req_data = {**self.data}
        req_data["members"] = [obj.id for obj in [user, user2]]
        response = self.auth_put(
            owner, 
            req_data, 
            [created_data[0].id]
        )
        self.assertEqual(response.status_code, self.status.HTTP_200_OK)
        updated_data = Organization.objects.get(id=created_data[0].id)
        self.assertEqual(response.data.get("id"), str(updated_data.id))
        self.assertEqual(response.data.get("name"), req_data.get("name"))
        self.assertEqual(response.data.get("description"), req_data.get("description"))
        self.assertEqual(len(response.data.get("members")), 2)
        # data is updated
        updated_data = Organization.objects.get(id=created_data[0].id)
        members = updated_data.members.all()
        self.assertEqual(updated_data.name, req_data.get("name"))
        self.assertEqual(updated_data.description, req_data.get("description"))
        self.assertEqual(len(members), 2)
        self.assertIn(user.id, members)
        # invitation email has been sent
        mailbox = self.get_mailbox()
        to_list = [mail.to[0] for mail in mailbox]
        self.assertEqual(len(mailbox), 2)
        self.assertIn(user.email, to_list)
        self.assertIn(user2.email, to_list)
        self.assertEqual(mailbox[0].subject, "Notification - You have been add to org updatename")
    
    def test_access_allow_user_can_update_data_and_members(self):
        owner = self.create_and_active_user()
        can_access_user = self.create_and_active_user(email="canaccess@gnail.com")
        user = self.create_and_active_user(email="user1@gmail.com", created_by=owner)
        user2 = self.create_and_active_user(email="user2@gmail.com")
        user2.can_be_accessed_by.add(owner)

        org_data = self.orgs_data[0]
        org_data["owner"] = owner
        created_data = self.bulk_create_object(Organization, [org_data])
        created_data[0].members.add(user)
        created_data[0].can_be_accessed_by.add(can_access_user)
        
        req_data = {**self.data}
        req_data["members"] = [obj.id for obj in [user, user2]]
        response = self.auth_put(
            can_access_user,
            req_data, 
            [created_data[0].id]
        )
        self.assertEqual(response.status_code, self.status.HTTP_200_OK)
        updated_data = Organization.objects.get(id=created_data[0].id)
        self.assertEqual(response.data.get("id"), str(updated_data.id))
        self.assertEqual(response.data.get("name"), req_data.get("name"))
        self.assertEqual(response.data.get("description"), req_data.get("description"))
        self.assertEqual(len(response.data.get("members")), 2)
        # data is updated
        updated_data = Organization.objects.get(id=created_data[0].id)
        members = updated_data.members.all()
        self.assertEqual(updated_data.name, req_data.get("name"))
        self.assertEqual(updated_data.description, req_data.get("description"))
        self.assertEqual(len(members), 2)
        self.assertIn(user.id, members)
        # invitation email has been sent
        mailbox = self.get_mailbox()
        to_list = [mail.to[0] for mail in mailbox]
        self.assertEqual(len(mailbox), 1)
        self.assertEqual(user2.email, to_list[0])
        self.assertEqual(mailbox[0].subject, "Notification - You have been add to org updatename")
    