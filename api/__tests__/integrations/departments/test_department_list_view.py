import uuid

from ...base_classe import BaseTestClass
from organization.models import Department

class TestListOrgDepartmentView(BaseTestClass):
    """### Flow
    - user need to be authenticated
    - user get not found when org doesn't exists
    - user need to havce access to or is the creator before getting org departments
    - test org member can get departs they are part of
    - user get department data with needed fields
    - data is paginated
    - data can be filtered and search throught
    """
    url_name = "departments-list"
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
        self.owner, self.creator, self.org = self.create_new_org()
        depart_data = [*self.departs_data]
        for data in depart_data:
            data["org"] = self.org
            data["created_by"] = self.owner
        self.created_depart = self.bulk_create_object(Department, depart_data)
        self.first_depart = self.created_depart[0]

    def test_only_authenticated_user_can_access(self):
        self.evaluate_method_unauthenticated_request(
            self.HTTP_GET, ['fake-id']
        )
    
    def test_user_get_no_data(self):
        user = self.create_and_active_user()
        response = self.auth_get(user, [uuid.uuid4()])
        self.assertEqual(response.status_code, self.status.HTTP_200_OK)
        data = self.loads(response.content).get("results")
        self.assertEqual(len(data), 0)
    
    def test_access_not_allowed_user_cant_access_ressource(self):
        user = self.create_and_active_user()
        response = self.auth_get(user, [self.org.id])
        self.assertEqual(response.status_code, self.status.HTTP_200_OK)
        data = self.loads(response.content).get("results")
        self.assertEqual(len(data), 0)
    
    def test_access_allowed_user_can_access_depart(self):
        user = self.create_and_active_user()
        self.org.can_be_accessed_by.add(user)

        for current_user in [
            self.owner, 
            user,
            self.creator
        ]:
            response = self.auth_get(current_user, [self.org.id])
            self.assertEqual(response.status_code, self.status.HTTP_200_OK)
            data = self.loads(response.content).get('results')
            self.assertEqual(len(data), len(self.created_depart))
            first_data = data[0]
            self.assertIsNotNone(first_data.get('name', None))
            self.assertIsNotNone(first_data.get('description', None))
            self.assertEqual(first_data.get('org').get('id'), str(self.org.id))
            self.assertIsNotNone(first_data.get('id', None))
            self.assertIsNotNone(first_data.get('created_at', None))

    def test_access_allowed_user_on_depart_only_can_access_depart(self):
        can_access_depart_user = self.create_and_activate_random_user()
        depart_creator = self.create_and_activate_random_user()
        depart_member = self.create_and_activate_random_user()

        for created in self.created_depart:
            created.can_be_accessed_by.add(can_access_depart_user)
            created.members.add(depart_member)
            created.created_by = depart_creator
            created.save()
        
        for current_user, depart_count in [
            (depart_creator, len(self.created_depart)), 
            (can_access_depart_user, len(self.created_depart)),
            (depart_member, len(self.created_depart))
        ]:
            response = self.auth_get(current_user, [self.org.id])
            self.assertEqual(response.status_code, self.status.HTTP_200_OK)
            data = self.loads(response.content).get('results')
            self.assertEqual(len(data), depart_count)
            first_data = data[0]
            self.assertIsNotNone(first_data.get('name', None))
            self.assertIsNotNone(first_data.get('description', None))
            self.assertEqual(first_data.get('org').get('id'), str(self.org.id))
            self.assertIsNotNone(first_data.get('id', None))
            self.assertIsNotNone(first_data.get('created_at', None))
    
    def test_depart_can_be_filtered(self):
        first_depart = self.created_depart[0]
        response = self.auth_get(self.owner, [self.org.id], {"ids": [first_depart.id, first_depart.id]})
        self.assertEqual(response.status_code, self.status.HTTP_200_OK)
        data = self.loads(response.content).get('results')
        self.assertEqual(len(data), 1)
        first_data = data[0]
        self.assertEqual(first_data.get('name', None), first_depart.name)
        self.assertEqual(first_data.get('description', None), first_depart.description)
        self.assertEqual(first_data.get('org').get('id'), str(self.org.id))