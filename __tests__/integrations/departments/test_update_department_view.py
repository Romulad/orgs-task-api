import uuid

from ..base_classe import BaseTestClass
from organization.models import Organization, Department

class TestUpdateOrgDepartmentView(BaseTestClass):
    """### Flow
    - user need to be authenticated
    - user get not found when org doesn't exists
    - user get not found when department doesn't exists
    - user need to have access to or is the creator of org before updating org department
    - test all field required should be present or validation error
    - test department name field is unique in the org for new specified name
    - test user has access to the new specified org
    - test new specified org owner has full access over department members or error
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
            self.HTTP_PUT, ['fake-id', 'fake-id']
        )
    
    def test_user_get_not_found_error(self):
        test_data = {
            "org": [uuid.uuid4(), self.created_departs[0].id],
            "dep": [self.org.id, uuid.uuid4()]
        }

        for _, url_arg in test_data.items():
            response = self.auth_put(self.owner_user, {}, url_arg) 
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

        response = self.auth_put(
            no_access_allowed, req_data, 
            [self.org.id, depart.id]
        )
        self.assertEqual(response.status_code, self.status.HTTP_404_NOT_FOUND)
        data = self.loads(response.content)
        self.assertIsNotNone(data.get("detail", None))
        # data don't get updated
        with self.assertRaises(Department.DoesNotExist):
            Department.objects.get(name=depart.name, description="Some description")
    
    def test_all_field_should_be_present(self):
        depart = self.created_departs[0]
        req_data = {
            "name": "updated_name",
            "org": self.org.id,
            "members": self.get_ids_from(self.org.members.all())
        }

        response = self.auth_put(
            self.owner_user, req_data, [self.org.id, depart.id]
        )
        self.assertEqual(response.status_code, self.status.HTTP_400_BAD_REQUEST)
        data = self.loads(response.content)
        self.assertIsInstance(data.get("description", None), list)
        # data don't get updated
        with self.assertRaises(Department.DoesNotExist):
            Department.objects.get(name="updated_name")
    
    def test_department_name_validation(self):
        first_depart = self.created_departs[0]
        second_depart = self.created_departs[1]
        req_data = {
            "name":second_depart.name,
            "description": first_depart.description,
            "org": self.org.id,
            "members" : self.get_ids_from(first_depart.members.all())
        }

        response = self.auth_put(
            self.owner_user, req_data, [self.org.id, first_depart.id]
        )
        self.assertEqual(response.status_code, self.status.HTTP_400_BAD_REQUEST)
        data = self.loads(response.content)
        self.assertIsInstance(data.get("name", None), list)
        # data don't get updated, we still have one depart with second_depart.name
        Department.objects.get(name=second_depart.name)
    
    def test_user_cant_update_to_un_accessed_org(self):
        first_depart = self.created_departs[0]
        other_owner = self.create_and_active_user(email="other_owner@gmaild.con")
        new_org = Organization.objects.create(name="no-access", owner=other_owner)

        req_data = {
            "name": first_depart.name,
            "description": first_depart.description,
            "org": new_org.id,
            "members" : self.get_ids_from(first_depart.members.all())
        }

        response = self.auth_put(
            self.owner_user, req_data, [self.org.id, first_depart.id]
        )
        self.assertEqual(response.status_code, self.status.HTTP_400_BAD_REQUEST)
        data = self.loads(response.content)
        self.assertIsInstance(data.get("org", None), list)
        # data don't get updated
        with self.assertRaises(Department.DoesNotExist):
            Department.objects.get(name=first_depart.name, org=new_org)
    
    def test_org_owner_need_to_have_full_access_over_members(self):
        first_depart = self.created_departs[0]
        free_user = self.create_and_active_user(email="free_user@hnm.com")
        req_data = {
            "name": first_depart.name,
            "description": first_depart.description,
            "org": self.org.id,
            "members" : self.get_ids_from(
                first_depart.members.all()
            ) + [free_user.id]
        }

        response = self.auth_put(
            self.owner_user, req_data, [self.org.id, first_depart.id]
        )
        self.assertEqual(response.status_code, self.status.HTTP_400_BAD_REQUEST)
        data = self.loads(response.content)
        self.assertIsInstance(data.get("members", None), list)
        # data don't get updated
        depart = Department.objects.get(name=first_depart.name)
        self.assertEqual(len(depart.members.all()), len(first_depart.members.all()))
    
    def test_user_can_update_depart_data(self):
        first_depart = self.created_departs[0]
        free_user = self.create_and_active_user(email="free_user@hnm.com")
        free_user.can_be_accessed_by.add(self.owner_user)
        self.org.members.add(free_user)
        new_org = Organization.objects.create(name="no-access", owner=self.owner_user)
        req_data = {
            "name": first_depart.name,
            "description": first_depart.description,
            "org": new_org.id,
            "members" : self.get_ids_from(
                first_depart.members.all()
            ) + [free_user.id]
        }

        response = self.auth_put(
            self.owner_user, req_data, [self.org.id, first_depart.id]
        )
        self.assertEqual(response.status_code, self.status.HTTP_200_OK)
        data = self.loads(response.content)
        self.assertEqual(data.get("id"), str(first_depart.id))
        self.assertEqual(data.get("name"), first_depart.name)
        self.assertEqual(data.get("description"), first_depart.description)
        self.assertEqual(data.get("org"), str(new_org.id))
        self.assertEqual(len(data.get("members")), 1)
        self.assertIn(str(free_user.id), data.get("members"))
        # data get updated
        depart = Department.objects.get(name=first_depart.name)
        members = depart.members.all()
        self.assertEqual(depart.org.id, new_org.id)
        self.assertEqual(len(members), 1)
        self.assertIn(free_user, members)

    def test_update_data_with_no_existed_members_in_org(self):
        first_depart = self.created_departs[0]
        simple_user = self.create_and_active_user(email="simple_user@hnm.com")
        simple_user.can_be_accessed_by.add(self.owner_user)
        req_data = {
            "name": first_depart.name,
            "description": first_depart.description,
            "org": self.org.id,
            "members" : self.get_ids_from(
                first_depart.members.all()
            ) + [simple_user.id]
        }

        response = self.auth_put(
            self.owner_user, req_data, [self.org.id, first_depart.id]
        )
        self.assertEqual(response.status_code, self.status.HTTP_200_OK)
        # new_user is added to org and invitation mail is sent
        org_data = Organization.objects.get(id=self.org.id, name=self.org.name)
        members = org_data.members.all()
        self.assertEqual(len(members), 1)
        self.assertIn(simple_user, members)
        mailbox = self.get_mailbox()
        self.assertEqual(len(mailbox), 1)
        mail_sent = mailbox[0]
        self.assertEqual(mail_sent.to[0], simple_user.email)
        self.assertIn("Notification - You have been add to org", mail_sent.subject)
    
    def test_access_allowed_on_depart_can_update_data(self):
        first_depart = self.created_departs[0]
        depart_creator = self.create_and_activate_random_user()
        can_access_depart_user = self.create_and_activate_random_user()
        first_depart.created_by = depart_creator
        first_depart.save()
        first_depart.can_be_accessed_by.add(can_access_depart_user)

        req_data = {
            "name": "new_name_never_use",
            "description": first_depart.description,
            "org": self.org.id,
            "members" : self.get_ids_from(
                first_depart.members.all()
            )
        }

        for user in [
            depart_creator,
            can_access_depart_user
        ]:
            response = self.auth_put(
                user, req_data, [self.org.id, first_depart.id]
            )
            self.assertEqual(response.status_code, self.status.HTTP_200_OK)
            data = self.loads(response.content)
            self.assertEqual(data.get("id"), str(first_depart.id))
        # data is updated
        first_depart.refresh_from_db(fields=["name"])
        self.assertEqual(first_depart.name, 'new_name_never_use')