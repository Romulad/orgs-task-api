import uuid

from ...base_classe import BaseTestClass
from organization.models import Organization, Department

class TestRetrieveOrgDepartmentView(BaseTestClass):
    """### Flow
    - user need to be authenticated
    - user get not found when org doesn't exists
    - user get not found when department doesn't exists
    - user need to have access to or is the creator before getting org department
    - user get department data with needed fields
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

    def test_only_authenticated_user_can_access(self):
        self.evaluate_method_unauthenticated_request(
            self.HTTP_GET, ['fake-id', 'fake-id']
        )
    
    def test_user_get_not_found_error(self):
        user = self.create_and_active_user()
        org = Organization.objects.create(name="test", owner=user)
        departs_data = [*self.departs_data]
        for data in departs_data:
            data["org"] = org
        created_data = self.bulk_create_object(Department, departs_data)
        
        test_data = {
            "org": [uuid.uuid4(), created_data[0].id],
            "dep": [org.id, uuid.uuid4()]
        }

        for _, url_arg in test_data.items():
            response = self.auth_get(user, url_arg) 
            self.assertEqual(response.status_code, self.status.HTTP_404_NOT_FOUND)
            data = self.loads(response.content)
            self.assertIsNotNone(data.get("detail", None))
    
    def test_user_cant_access_not_allowed_ressource(self):
        no_access_allowed = self.create_and_active_user(email="no_access_allowed@gmail.con")
        user = self.create_and_active_user()
        org = Organization.objects.create(name="test", owner=user)
        departs_data = [*self.departs_data]
        for data in departs_data:
            data["org"] = org
        first_depart = self.bulk_create_object(Department, departs_data)[0]

        response = self.auth_get(no_access_allowed, [org.id, first_depart.id])
        self.assertEqual(response.status_code, self.status.HTTP_404_NOT_FOUND)
        data = self.loads(response.content)
        self.assertIsNotNone(data.get("detail", None))
    
    def test_access_allowed_user_can_get_data(self):
        user = self.create_and_active_user()
        access_allowed_user = self.create_and_active_user(email="access_allowed_user@gai.com")
        org = Organization.objects.create(name="test", owner=user)
        org.can_be_accessed_by.add(access_allowed_user)
        departs_data = [*self.departs_data]
        for data in departs_data:
            data["org"] = org
        first_depart = self.bulk_create_object(Department, departs_data)[0]

        for cur_user in [user, access_allowed_user]:
            response = self.auth_get(cur_user, [org.id, first_depart.id])
            self.assertEqual(response.status_code, self.status.HTTP_200_OK)
            data = self.loads(response.content)
            self.assertEqual(data.get('id'), str(first_depart.id))
            self.assertEqual(data.get('name'), first_depart.name)
            self.assertEqual(data.get('description'), first_depart.description)
            self.assertEqual(data.get('org').get('id'), str(org.id))
            self.assertIsInstance(data.get('members'), list)
            self.assertEqual(len(data.get('members')), 0)
    
    def test_access_allowed_user_on_depart_can_get_data(self):
        depart_creator = self.create_and_activate_random_user()
        can_access_depart = self.create_and_active_user()
        _, _, org = self.create_new_org()
        departs_data = [*self.departs_data]
        for data in departs_data:
            data["org"] = org
        first_depart = self.bulk_create_object(Department, departs_data)[0]
        first_depart.created_by = depart_creator
        first_depart.save()
        first_depart.can_be_accessed_by.add(can_access_depart)

        for user in [
            depart_creator,
            can_access_depart
        ]:
            response = self.auth_get(user, [org.id, first_depart.id])
            self.assertEqual(response.status_code, self.status.HTTP_200_OK)
            data = self.loads(response.content)
            self.assertEqual(data.get('id'), str(first_depart.id))
            self.assertEqual(data.get('name'), first_depart.name)
            self.assertEqual(data.get('description'), first_depart.description)
            self.assertEqual(data.get('org').get('id'), str(org.id))
            self.assertIsInstance(data.get('members'), list)
            self.assertEqual(len(data.get('members')), 0)