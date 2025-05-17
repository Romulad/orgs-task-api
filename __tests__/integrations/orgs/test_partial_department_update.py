import uuid

from ..base_classe import BaseTestClass
from organization.models import Organization, Department

class TestPartialUpdateOrgDepartmentView(BaseTestClass):
    """### Flow
    - user need to be authenticated
    - user get not found when org doesn't exists
    - user get not found when department doesn't exists
    - user need to have access to or is the creator of org before updating org department
    - test department name field is unique in the org for new specified name
    - if new org and not members is specified: 
        test user has access to the new specified org and 
        test new org owner has access to all members in the department 
    - if org and members is specified:
        test user has access to the org if new
        test org owner has access to all members specified
    - if not org and members specified:
        test if department org owner has full access over specified members
    - test user can update department data to specified data
    - test members in department and not in org are automatically added to org
    and get invitation success notification
    """
    url_name = "departments-detail"
    departs_data = [
        {
            "name": "my depart 1", "description": "some descr"
        },
        {
            "name": "my depart 2", "description": "some descr"
        },
        {
            "name": "my depart 3", "description": "some descr"
        }
    ]

    def setUp(self):
        self.owner_user = self.create_and_active_user(email="owner_user@gmail.com")
        self.org = Organization.objects.create(name="test", owner=self.owner_user)
        departs_data = [*self.departs_data]
        for data in departs_data:
            data["org"] = self.org
        self.created_departs = self.bulk_create_object(Department, departs_data)
    
    def test_only_authenticated_user_can_access(self):
        self.evaluate_method_unauthenticated_request(
            self.HTTP_PATCH, ['fake-id', 'fake-id']
        )
    
    def test_user_get_not_found_error(self):
        test_data = {
            "org": [uuid.uuid4(), self.created_departs[0].id],
            "dep": [self.org.id, uuid.uuid4()]
        }

        for _, url_arg in test_data.items():
            response = self.auth_patch(self.owner_user, {}, url_arg) 
            self.assertEqual(response.status_code, self.status.HTTP_404_NOT_FOUND)
            data = self.loads(response.content)
            self.assertIsNotNone(data.get("detail", None))
    
    def test_other_user_cant_update_data(self):
        no_access_allowed = self.create_and_active_user()
        depart = self.created_departs[0]
        req_data = {
            "name": depart.name,
            "description": "Some description"
        }

        response = self.auth_patch(
            no_access_allowed, req_data, 
            [self.org.id, depart.id]
        )
        self.assertEqual(response.status_code, self.status.HTTP_404_NOT_FOUND)
        data = self.loads(response.content)
        self.assertIsNotNone(data.get("detail", None))
        # data don't get updated
        with self.assertRaises(Department.DoesNotExist):
            Department.objects.get(name=depart.name, description="Some description")
    
    def test_departmen_name_validation(self):
        first_depart = self.created_departs[0]
        second_depart = self.created_departs[1]
        req_data = {
            "name":second_depart.name,
        }

        response = self.auth_patch(
            self.owner_user, req_data, [self.org.id, first_depart.id]
        )
        self.assertEqual(response.status_code, self.status.HTTP_400_BAD_REQUEST)
        data = self.loads(response.content)
        self.assertIsInstance(data.get("name", None), list)
        # data don't get updated
        Department.objects.get(name=second_depart.name)
    
    def test_user_cant_update_to_un_accessed_org(self):
        first_depart = self.created_departs[0]
        other_owner = self.create_and_active_user(email="other_owner@gmaild.con")
        new_org = Organization.objects.create(name="no-access", owner=other_owner)

        req_data = {
            "org": new_org.id,
        }

        response = self.auth_patch(
            self.owner_user, req_data, [self.org.id, first_depart.id]
        )
        self.assertEqual(response.status_code, self.status.HTTP_400_BAD_REQUEST)
        data = self.loads(response.content)
        self.assertIsInstance(data.get("org", None), list)
        # data don't get updated
        with self.assertRaises(Department.DoesNotExist):
            Department.objects.get(name=first_depart.name, org=new_org)
    
    def test_org_owner_need_to_have_full_access_over_members(self):
        free_user = self.create_and_active_user(email="free_user@hnm.com")
        first_depart = self.created_departs[0]
        first_depart.members.add(free_user)

        other_owner = self.create_and_active_user(email="other_owner@gmaild.con")
        new_org = Organization.objects.create(name="new_org_", owner=other_owner)
        new_org.can_be_accessed_by.add(self.owner_user)

        req_data = {
            "org": new_org.id
        }

        response = self.auth_patch(
            self.owner_user, req_data, [self.org.id, first_depart.id]
        )
        self.assertEqual(response.status_code, self.status.HTTP_400_BAD_REQUEST)
        data = self.loads(response.content)
        self.assertIsInstance(data.get("members", None), list)
        # data don't get updated
        depart = Department.objects.get(name=first_depart.name)
        self.assertEqual(len(depart.members.all()), len(first_depart.members.all()))
    
    def test_org_owner_need_to_have_full_access_over_members_specified(self):
        other_owner = self.create_and_active_user(email="other_owner@gmaild.con")
        new_org = Organization.objects.create(name="new_org_", owner=other_owner)
        new_org.can_be_accessed_by.add(self.owner_user)

        depart_member = self.create_and_active_user(
            email="depart_member@hnm.com", created_by=self.owner_user
        )
        depart_member.can_be_accessed_by.add(other_owner)
        first_depart = self.created_departs[0]
        first_depart.members.add(depart_member)

        free_user = self.create_and_active_user(email="free_user@hnm.com")

        req_data = {
            "org": new_org.id,
            "members": [depart_member.id, free_user.id]
        }

        response = self.auth_patch(
            self.owner_user, req_data, [self.org.id, first_depart.id]
        )
        self.assertEqual(response.status_code, self.status.HTTP_400_BAD_REQUEST)
        data = self.loads(response.content)
        self.assertIsInstance(data.get("members", None), list)
        # data don't get updated
        depart = Department.objects.get(name=first_depart.name)
        self.assertEqual(len(depart.members.all()), len(first_depart.members.all()))
    
    def test_existed_org_owner_has_access_over_all_members_specified(self):
        depart_member = self.create_and_active_user(
            email="depart_member@hnm.com", 
            created_by=self.owner_user
        )
        first_depart = self.created_departs[0]
        first_depart.members.add(depart_member)

        free_user = self.create_and_active_user(email="free_user@hnm.com")

        req_data = {
            "members": [depart_member.id, free_user.id]
        }

        response = self.auth_patch(
            self.owner_user, req_data, [self.org.id, first_depart.id]
        )
        self.assertEqual(response.status_code, self.status.HTTP_400_BAD_REQUEST)
        data = self.loads(response.content)
        self.assertIsInstance(data.get("members", None), list)
        # data don't get updated
        depart = Department.objects.get(name=first_depart.name)
        self.assertEqual(len(depart.members.all()), len(first_depart.members.all()))
    
    def test_org_owner_can_update_data(self):
        other_owner = self.create_and_active_user(email="other_owner@gmaild.con")
        new_org = Organization.objects.create(name="new_org_", owner=other_owner)
        new_org.can_be_accessed_by.add(self.owner_user)

        simple_user = self.create_and_active_user(email="simple_user@hnm.com")
        simple_user.can_be_accessed_by.add(other_owner)
        first_depart = self.created_departs[0]
        first_depart.members.add(simple_user)

        req_data = {
            "org": new_org.id
        }

        response = self.auth_patch(
            self.owner_user, req_data, [self.org.id, first_depart.id]
        )
        self.assertEqual(response.status_code, self.status.HTTP_200_OK)
        data = self.loads(response.content)
        self.assertEqual(data.get("id"), str(first_depart.id))
        self.assertEqual(data.get("name"), first_depart.name)
        self.assertEqual(data.get("description"), first_depart.description)
        self.assertEqual(data.get("org"), str(new_org.id))
        self.assertEqual(len(data.get("members")), 1)
        self.assertIn(str(simple_user.id), data.get("members"))
        # data is updated
        depart = Department.objects.get(name=first_depart.name)
        self.assertEqual(depart.org.id, new_org.id)
        # email
        mailbox = self.get_mailbox()
        self.assertEqual(len(mailbox), 1)
        mail_sent = mailbox[0]
        self.assertEqual(mail_sent.to[0], simple_user.email)
        self.assertIn("Notification - You have been add to org", mail_sent.subject)