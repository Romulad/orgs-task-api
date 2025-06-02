import uuid

from ..base_classe import BaseTestClass
from tasks.models import Task
from tags.models import Tag
from organization.models import Department, Organization


class TestCreateTaskView(BaseTestClass):
    """### Flow
    - user need to be authenticated
    - test data validation:
        - test `name` field validation:
            - `name` is required
            - `name` should be unique with the org
        - test `org` validation:
            - test `org` is required
            - test the user creating the ressource should have a full access over the org
        - test `assigned_to` if include in data:
            - `assigned_to` should b valid user ids
            - the org owner should have a full access over `assigned_to`
        - test `due_date` is properly validate if included
        - test user can not choose different `priority` value
        - test user can not choose different `status` value
        - test `estimated_duration` if specified can only accept valida data
        - test `actual_duration` if specified can only accept valid data
        - test `allowed_status_update` if specified can only accept valid data
        - test `tags` validation if specified:
            - test the tags should exist
            - test the tags specified for the task should all belongs to the task org, we should
            not include a tag from another org
        - test `depart` vaidation if specified:
            - test depart exist first
            - test the depart specified and the task been created has the same org
    - test assigned_to get automatically added to org members if not existed by default
    - test task is created with created_by field set to the user creating the task
    - test task is successfully created with needed data and needed response is returned
    """
    url_name = "tasks-list"
    task_data = [
        {
            "name": "first_task"
        },
        {
            "name": "second_task"
        },
        {
            "name": "third_task"
        }
    ]

    def test_only_authenticated_user_can_access(self):
        self.evaluate_method_unauthenticated_request(
            self.HTTP_POST
        )

    def setUp(self):
        self.owner_user = self.create_and_active_user(email="owner_user@dshgd.com")
        self.org = Organization.objects.create(
            name="owner_org", 
            owner=self.owner_user, 
            created_by=self.owner_user
        )
        self.another_org = Organization.objects.create(
            name="another_org", 
            owner=self.owner_user, 
        )
        task_data = [*self.task_data]
        for data in task_data:
            data["org"] = self.org
        self.tasks = self.bulk_create_object(Task, task_data)
        self.simple_user = self.create_and_active_user(email="simple_user@gamail.com")
    
    def assert_task_number(self, count=3):
        self.assertEqual(Task.objects.all().count(), count)
    
    def test_name_field_validation(self):
        test_datas = [
            {"org": self.org.id},
            {"name": "", "org": self.org.id},
            {"name": "first_task", "org": self.org.id},
        ]
        for req_data in test_datas:
            response = self.auth_post(self.owner_user, req_data)
            self.assertEqual(response.status_code, self.status.HTTP_400_BAD_REQUEST)
            errors = self.loads(response.content).get('name')
            self.assertIsInstance(errors, list)
            self.assert_task_number()
    
    def test_org_validation(self):
        test_datas = [
            {"user": self.owner_user, "req_data": {'name': "randomname"}},
            {"user": self.owner_user, "req_data": {'name': "randomname", "org": uuid.uuid4()}},
            {"user": self.simple_user, "req_data": {"name": "randomname", "org": self.org.id}}
        ]
        for data in test_datas:
            req_data = data["req_data"]
            current_user = data["user"]
            response = self.auth_post(current_user, req_data)
            self.assertEqual(response.status_code, self.status.HTTP_400_BAD_REQUEST)
            errors = self.loads(response.content).get('org')
            self.assertIsInstance(errors, list)
            self.assert_task_number()
    
    def test_assigned_to_validation(self):
        test_datas = [
            {"name": "random_task_name", "org": self.org.id, "assigned_to": ["inavlid-id"]},
            {"name": "random_task_name", "org": self.org.id, "assigned_to": [uuid.uuid4()]},
            {"name": "random_task_name", "org": self.org.id, "assigned_to": [self.simple_user.id]},
        ]
        for req_data in test_datas:
            response = self.auth_post(self.owner_user, req_data)
            self.assertEqual(response.status_code, self.status.HTTP_400_BAD_REQUEST)
            errors = self.loads(response.content).get('assigned_to')
            self.assertIsNotNone(errors)
            self.assert_task_number()
    
    def test_due_date_validation(self):
        req_data = {
            "name": "random_task_name",
            "org": self.org.id,
            "due_date": "2023-10-10T10:00:00-07:"
        }

        response = self.auth_post(self.owner_user, req_data)
        self.assertEqual(response.status_code, self.status.HTTP_400_BAD_REQUEST)
        errors = self.loads(response.content).get('due_date')
        self.assertIsInstance(errors, list)
        self.assert_task_number()    
    
    def test_priority_validation(self):
        req_data = {
            "name": "random_task_name",
            "org": self.org.id,
            "priority": "IN_PROGRESS"
        }

        response = self.auth_post(self.owner_user, req_data)
        self.assertEqual(response.status_code, self.status.HTTP_400_BAD_REQUEST)
        errors = self.loads(response.content).get('priority')
        self.assertIsInstance(errors, list)
        self.assert_task_number()
    
    def test_status_validation(self):
        req_data = {
            "name": "random_task_name",
            "org": self.org.id,
            "status": "Medium"
        }

        response = self.auth_post(self.owner_user, req_data)
        self.assertEqual(response.status_code, self.status.HTTP_400_BAD_REQUEST)
        errors = self.loads(response.content).get('status')
        self.assertIsInstance(errors, list)
        self.assert_task_number()
    
    def test_estimated_duration_validation(self):
        req_data = {
            "name": "random_task_name",
            "org": self.org.id,
            "estimated_duration": "invalid-duration"
        }

        response = self.auth_post(self.owner_user, req_data)
        self.assertEqual(response.status_code, self.status.HTTP_400_BAD_REQUEST)
        errors = self.loads(response.content).get('estimated_duration')
        self.assertIsInstance(errors, list)
        self.assert_task_number()
    
    def test_actual_duration_validation(self):
        req_data = {
            "name": "random_task_name",
            "org": self.org.id,
            "actual_duration": "invalid-duration"
        }

        response = self.auth_post(self.owner_user, req_data)
        self.assertEqual(response.status_code, self.status.HTTP_400_BAD_REQUEST)
        errors = self.loads(response.content).get('actual_duration')
        self.assertIsInstance(errors, list)
        self.assert_task_number()
    
    def test_tags_validation(self):
        other_tag = Tag.objects.create(
            name="other_tag", 
            org=self.another_org, 
        )
        test_datas = [
            {
                "name": "random_task_name",
                "org": self.org.id,
                "tags": ["invalid-id"]
            },
            {
                "name": "random_task_name",
                "org": self.org.id,
                "tags": [uuid.uuid4()]
            },
            {
                "name": "random_task_name",
                "org": self.org.id,
                "tags": [other_tag.id]
            }
        ]
        for req_data in test_datas:
            response = self.auth_post(self.owner_user, req_data)
            self.assertEqual(response.status_code, self.status.HTTP_400_BAD_REQUEST)
            errors = self.loads(response.content).get('tags')
            self.assertIsInstance(errors, list)
            self.assert_task_number()
    
    def test_depart_validation(self):
        other_depart = Department.objects.create(
            name="other_depart", 
            org=self.another_org, 
        )
        test_datas = [
            {
                "name": "random_task_name",
                "org": self.org.id,
                "depart": "invalid-id"
            },
            {
                "name": "random_task_name",
                "org": self.org.id,
                "depart": uuid.uuid4()
            },
            {
                "name": "random_task_name",
                "org": self.org.id,
                "depart": other_depart.id
            }
        ]
        for req_data in test_datas:
            response = self.auth_post(self.owner_user, req_data)
            self.assertEqual(response.status_code, self.status.HTTP_400_BAD_REQUEST)
            errors = self.loads(response.content).get('depart')
            self.assertIsInstance(errors, list)
            self.assert_task_number()
    
    def test_new_user_in_assigned_to_get_added_to_org(self):
        self.simple_user.can_be_accessed_by.add(self.owner_user)
        req_data = {
            "name": "random_task_name",
            "org": self.org.id,
            "assigned_to": [self.simple_user.id]
        }
        response = self.auth_post(self.owner_user, req_data)
        self.assertEqual(response.status_code, self.status.HTTP_201_CREATED)
        self.assert_task_number(4)
        # Check if the user is added to the org members
        self.assertTrue(
            Organization.objects.filter(
                id=self.org.id, 
                members__in=[self.simple_user]
            ).exists()
        )
    
    def test_task_creation_with_created_by_field(self):
        req_data = {
            "name": "random_task_name",
            "org": self.org.id,
        }
        response = self.auth_post(self.owner_user, req_data)
        self.assertEqual(response.status_code, self.status.HTTP_201_CREATED)
        self.assert_task_number(4)
        Task.objects.get(name=req_data["name"], org=self.org, created_by=self.owner_user)
    
    def test_task_creation_with_all_valid_data(self):
        self.simple_user.can_be_accessed_by.add(self.owner_user)
        tag = Tag.objects.create(
            name="test_tag",
            org=self.org, 
        )
        depart = Department.objects.create(
            name="test_depart", 
            org=self.org, 
        )
        req_data = {
            "name": "random_task_name",
            "description": "This is a test task",
            "org": self.org.id,
            "assigned_to": [self.simple_user.id],
            "due_date": "2023-10-10T10:00:00Z",
            "priority": Task.Priority.HIGH,
            "status": Task.Status.PENDING,
            "estimated_duration": "01:00:00",
            "actual_duration": "00:30:00",
            "allow_auto_status_update": True,
            "tags": [tag.id],
            "depart": depart.id
        }
        response = self.auth_post(self.owner_user, req_data)
        self.assertEqual(response.status_code, self.status.HTTP_201_CREATED)
        # assert response data
        response_data = self.loads(response.content)
        self.assertEqual(response_data["name"], req_data["name"])
        self.assertEqual(response_data["org"], str(self.org.id))
        self.assertIn(str(self.simple_user.id), [user_id for user_id in response_data["assigned_to"]])
        self.assertEqual(response_data["due_date"], req_data["due_date"])
        self.assertEqual(response_data["priority"], req_data["priority"])
        self.assertEqual(response_data["status"], req_data["status"])
        self.assertEqual(response_data["estimated_duration"], req_data["estimated_duration"])
        self.assertEqual(response_data["actual_duration"], req_data["actual_duration"])
        self.assertEqual(response_data["allow_auto_status_update"], req_data["allow_auto_status_update"])
        self.assertEqual(response_data["tags"][0], str(tag.id))
        self.assertEqual(response_data["depart"], str(depart.id))
        # assert task is created
        self.assert_task_number(4)
        new_task = Task.objects.get(name=req_data["name"], org=self.org)
        self.assertEqual(new_task.name, req_data["name"])
        self.assertEqual(new_task.org.id, req_data["org"])
        self.assertIn(self.simple_user, new_task.assigned_to.all())
        self.assertEqual(new_task.priority, req_data["priority"])
        self.assertEqual(new_task.status, req_data["status"])