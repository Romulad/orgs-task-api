import uuid

from ...base_classe import BaseTestClass
from organization.models import Department, Organization
from app_lib.app_permssions import CAN_CREATE_DEPART

class TestCreateDepartmentView(BaseTestClass):
    """### Flow
    - user need to be authenticated
    - test user get not found when organization doesn't exist
    - test user without org access can't create department in org
    - test request data is valid:
        - name field is required
        - name field should be unique in the org for the department
        - description field is optional
        - members field is optional
        - the org owner should have full acccess over members specified
    - test department is create with needed field and org, created_by set, test response data is valid
    - test not creator only but access allowed user can create department in org
    - test user with permission to create depart in org can create new department for the org
    - test new member add to a department that is not present in the org should be
    automatically added and invitation success email should be sent
    """
    url_name = "departments-list"
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
        self.owner = self.create_and_activate_random_user()
        self.can_access_org_user = self.create_and_activate_random_user()
        orgs_data = [*self.orgs_data]
        for data in orgs_data:
            data["owner"] = self.owner
        self.orgs = self.bulk_create_object(
            Organization, orgs_data
        )
        self.created_org = self.orgs[0]
        self.created_org.can_be_accessed_by.add(self.can_access_org_user)

    def test_only_authenticated_user_can_access(self):
        self.evaluate_method_unauthenticated_request(
            self.HTTP_POST, ["fake-org-id"]
        )
    
    def test_not_found_request(self):
        response = self.auth_post(self.owner, {"name": ''}, [uuid.uuid4()])
        self.assertEqual(response.status_code, self.status.HTTP_404_NOT_FOUND)
        data = self.loads(response.content)
        self.assertIsNotNone(data.get('detail'))

    def test_not_access_allowed_user_cant_create_depart_in_org(self):
        user = self.create_and_activate_random_user()
        response = self.auth_post(user, {"name": "depart1"}, [self.created_org.id])
        self.assertEqual(response.status_code, self.status.HTTP_404_NOT_FOUND)
        data = self.loads(response.content)
        self.assertIsNotNone(data.get('detail'))
        # ressource state doesn't change
        self.assertEqual(len(Department.objects.all()), 0)
        self.assertEqual(len(Organization.objects.all()), 3)
    
    def test_request_data_validaty_for_name(self):
        # create department with org
        Department.objects.create(name="depart1", org=self.created_org)

        test_datas = [
            {},
            {"name": ""},
            {"description": "Awesome description"},
            {"name": "depart1"},
        ]
        for test_data in test_datas:
            response = self.auth_post(self.owner, test_data, [self.created_org.id])
            self.assertEqual(response.status_code, self.status.HTTP_400_BAD_REQUEST)
            data = self.loads(response.content)
            self.assertIsInstance(data.get("name"), list)
            # only on department exist
            self.assertEqual(len(Department.objects.all()), 1)
            self.assertEqual(len(Organization.objects.all()), 3)
    
    def test_request_data_validaty_for_members(self):
        user = self.create_and_active_user(email="usermail@gmail.com")
        test_datas = [
            {"name": "testname", 'members': [user.id]}
        ]
        for test_data in test_datas:
            response = self.auth_post(self.owner, test_data, [self.created_org.id])
            self.assertEqual(response.status_code, self.status.HTTP_400_BAD_REQUEST)
            data = self.loads(response.content)
            self.assertIsInstance(data.get("members"), list)
            # only on department exist
            self.assertEqual(len(Department.objects.all()), 0)
            self.assertEqual(len(Organization.objects.all()), 3)

    def test_access_allowed_user_can_create_depart_in_org(self):
        added_to_depart = self.create_and_active_user(email="added@gmail.con")
        added_to_depart.can_be_accessed_by.add(self.owner)
        self.created_org.members.add(added_to_depart)

        test_datas = [
            {
                'user': self.can_access_org_user, 
                "data": {"name": "depart1", 'members': [added_to_depart.id]}, 
                "dep_count": 1, 
                "dep_member_count": 1,
            },
            {
                'user': self.owner, 
                "data": {"name": "depart2"}, 
                "dep_count": 2,
                "dep_member_count": 0,
            }
        ]

        for test_data in test_datas:
            current_user = test_data["user"]
            dep_name = test_data.get('data')['name']
            dep_member_count = test_data['dep_member_count']
            response = self.auth_post(current_user, test_data["data"], [self.created_org.id])
            self.assertEqual(response.status_code, self.status.HTTP_201_CREATED)
            data = self.loads(response.content)
            self.assertEqual(data.get('name'), dep_name)
            self.assertEqual(data.get('description'), "")
            self.assertEqual(data.get('org').get('id'), str(self.created_org.id))
            self.assertIsNotNone(data.get('id'))
            self.assertEqual(len(data.get('members')), dep_member_count)
            # ressource state change
            Department.objects.get(name=dep_name, org=self.created_org, created_by=current_user)
            self.assertEqual(len(Department.objects.all()), test_data['dep_count'])
        self.assertEqual(len(Organization.objects.all()), 3)

    def test_user_can_create_depart_in_org_with_new_member(self):
        added_to_depart = self.create_and_active_user(email="added@gmail.con")
        added_to_depart.can_be_accessed_by.add(self.owner)

        req_data = {
            "name": "depart1", 
            'members': [added_to_depart.id]
        } 

        response = self.auth_post(self.owner, req_data, [self.created_org.id])
        self.assertEqual(response.status_code, self.status.HTTP_201_CREATED)
        data = self.loads(response.content)
        self.assertEqual(data.get('name'), 'depart1')
        self.assertEqual(len(data.get('members')), 1)
        # ressource state change
        created_dep = Department.objects.get(name="depart1", org=self.created_org, created_by=self.owner)
        org = Organization.objects.get(id=self.created_org.id)
        self.assertEqual(len(created_dep.members.all()), 1)
        self.assertIn(added_to_depart, created_dep.members.all())
        self.assertEqual(len(org.members.all()), 1)
        self.assertIn(added_to_depart, org.members.all())
        # mail is sent to new member
        mailbox = self.get_mailbox()
        self.assertEqual(len(mailbox), 1)
        mail_sent = mailbox[0]
        self.assertEqual(mail_sent.to[0], added_to_depart.email)
        self.assertIn("Notification - You have been add to org", mail_sent.subject)
    
    def test_user_with_perm_can_create_depart_in_org(self):
        user_with_perm, _, perm_obj = self.create_new_permission(self.created_org)
        perm_obj.add_permissions(CAN_CREATE_DEPART)

        added_to_depart = self.create_and_activate_random_user()
        added_to_depart.can_be_accessed_by.add(self.owner)

        req_data = {
            "name": "depart1", 
            'members': [added_to_depart.id]
        } 

        response = self.auth_post(user_with_perm, req_data, [self.created_org.id])
        self.assertEqual(response.status_code, self.status.HTTP_201_CREATED)
        data = self.loads(response.content)
        self.assertEqual(data.get('name'), 'depart1')
        self.assertEqual(len(data.get('members')), 1)