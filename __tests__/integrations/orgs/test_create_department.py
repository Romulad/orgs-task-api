
from ..base_classe import BaseTestClass
from organization.models import Department, Organization

class TestCreateDepartmentView(BaseTestClass):
    """### Flow
    - user need to be authenticated
    - test request data is valid:
        - name field is required
        - name field should be unique in the org for the department
        - description field is optional
    - test user without access can't create department in org
    - test department is create with needed field and org, created_by set, test response data is valid
    - test user get not found when organization doesn't exist
    - test not creator but access allowed user can create department in org
    """
    url_name = "orgs-department"
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

    def test_only_authenticated_user_can_access(self):
        self.evaluate_method_unauthenticated_request(
            self.HTTP_POST, ["fake-org-id"]
        )
    
    def test_not_found_request(self):
        owner = self.create_and_active_user()
        orgs_data = [*self.orgs_data]
        for data in orgs_data:
            data["owner"] = owner
        self.bulk_create_object(
            Organization, orgs_data
        )
        response = self.auth_post(owner, {"name": ''}, ["fake-id"])
        self.assertEqual(response.status_code, self.status.HTTP_404_NOT_FOUND)
        data = self.loads(response.content)
        self.assertIsNotNone(data.get('detail'))
    
    def test_request_data_validaty(self):
        owner = self.create_and_active_user()
        orgs_data = [*self.orgs_data]
        for data in orgs_data:
            data["owner"] = owner
        created_org = self.bulk_create_object(
            Organization, orgs_data
        )[0]
        # create department with org
        Department.objects.create(name="depart1", org=created_org)

        test_datas = [
            {"req_data": {}, "field": "name"},
            {"req_data": {"name": ""}, "field": "name"},
            {"req_data": {"description": "Awesome description"}, "field": "name"},
            {"req_data": {"name": "depart1"}, "field": "name"},
        ]
        for test_data in test_datas:
            response = self.auth_post(owner, test_data["req_data"], [created_org.id])
            self.assertEqual(response.status_code, self.status.HTTP_400_BAD_REQUEST)
            data = self.loads(response.content)
            self.assertIsInstance(data.get(test_data['field']), list)
            # only on department exist
            self.assertEqual(len(Department.objects.all()), 1)
            self.assertEqual(len(Organization.objects.all()), 3)
    
    def test_not_access_allowed_user_cant_create_depart_in_org(self):
        user = self.create_and_active_user(email="test@ganil.comk")
        owner = self.create_and_active_user()
        orgs_data = [*self.orgs_data]
        for data in orgs_data:
            data["owner"] = owner
        created_org = self.bulk_create_object(
            Organization, orgs_data
        )[0]

        response = self.auth_post(user, {"name": "depart1"}, [created_org.id])
        self.assertEqual(response.status_code, self.status.HTTP_404_NOT_FOUND)
        data = self.loads(response.content)
        self.assertIsNotNone(data.get('detail'))
        # ressource state doesn't change
        self.assertEqual(len(Department.objects.all()), 0)
        self.assertEqual(len(Organization.objects.all()), 3)
    
    def test_access_allowed_user_can_create_depart_in_org(self):
        user = self.create_and_active_user(email="test@ganil.comk")
        owner = self.create_and_active_user()
        orgs_data = [*self.orgs_data]
        for data in orgs_data:
            data["owner"] = owner
        created_org = self.bulk_create_object(
            Organization, orgs_data
        )[0]
        created_org.can_be_accessed_by.add(user)

        test_datas = [
            {'user': user, "data": {"name": "depart1"}, "dep_count": 1},
            {'user': owner, "data": {"name": "depart2"}, "dep_count": 2}
        ]

        for test_data in test_datas:
            current_user = test_data["user"]
            dep_name = test_data.get('data')['name']
            response = self.auth_post(current_user, test_data["data"], [created_org.id])
            self.assertEqual(response.status_code, self.status.HTTP_201_CREATED)
            data = self.loads(response.content)
            self.assertEqual(data.get('name'), dep_name)
            self.assertEqual(data.get('description'), "")
            self.assertEqual(data.get('org'), str(created_org.id))
            self.assertIsNotNone(data.get('id'))
            # ressource state change
            Department.objects.get(name=dep_name, org=created_org, created_by=current_user)
            self.assertEqual(len(Department.objects.all()), test_data['dep_count'])
        self.assertEqual(len(Organization.objects.all()), 3)