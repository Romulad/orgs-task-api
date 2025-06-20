import uuid

from django.forms import model_to_dict

from ...base_classe import BaseTestClass
from tasks.models import Task


class TestPartialUpdateTaskView(BaseTestClass):
    """### Flow
    - user need to be authenticated
    - test user get not found when ressource doesn't exist
    - other depart owners or other users can't udpdate the task obj - 404
    - test assigned to users that has access to the task and it not owner can't update task - 403
    - test data validation: (here an instance already exist and user can send any combination of field)
        - test `name` field validation:
            - same name as the default instance name should not cause an error
            - task `name` should be unique within either the task org or the org specified in the request
            data if available
        - test `org` validation:
            - if org is same as the intance org no validation needed as the org should be validate 
            with the user who is changing it
            - if org id different from existing intance org id: 
                - test the user updating the ressource has a full access over the new org
                - test the new org owner has access to all existing assigned_to users on task
                - test the existing task tags' org is same as the new org
                - test the new org is the same org for the existing task depart
                - test name uniqueness for existing instance
        - test `assigned_to`:
            - `assigned_to` should be valid user ids
            - test either req data org owner or existing task org owner has a full access over 
            `assigned_to` users
        - test `due_date`:
            - test is properly validate if specified
        - test `priority`:
            - test user can not choose different `priority` value
        - test `status`:
            - test user can not choose different `status` value
        - test `estimated_duration`:
            - test is properly validate if specified
        - test `actual_duration`:
            - test is properly validate if specified
        - test `tags` validation:
            - `tags` should be valid tag ids
            - test either req data org or existing task org has a full access over 
            `tags` object
        - test `depart` vaidation if specified:
            - `depart` should be valid depart id
            - test either req data org or existing task org has a full access over 
            `depart` object
    - test assigned_to get automatically added to specified org if not existed by default
    - test access allowed user:
        - org owners
        - depart owners
        - task owners
    can successfully update task, include same name in the data.
    """
    url_name = "tasks-detail"
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

    def setUp(self):
        self.owner_user, self.org_creator, self.org = self.create_new_org()
        task_data = [*self.task_data]
        for data in task_data:
            data["org"] = self.org
        self.tasks = self.bulk_create_object(Task, task_data)
        self.target_task = self.tasks[0]
        self.simple_user = self.create_and_activate_random_user()
    
    def test_only_authenticated_user_can_access(self):
        self.evaluate_method_unauthenticated_request(
            self.HTTP_PATCH, ["fake-id"]
        )
    
    def test_not_found_ressource(self):
        response = self.auth_patch(self.owner_user, {}, [uuid.uuid4()])
        self.assertEqual(response.status_code, self.status.HTTP_404_NOT_FOUND)
        self.assertIsNotNone(response.data.get("detail", None))
    
    def test_user_without_access_to_the_task_cant_update_it(self):
        depart_creator, depart = self.create_new_depart(self.org)
        can_access_depart_user = self.create_and_activate_random_user()
        depart.can_be_accessed_by.add(can_access_depart_user)

        for user in [
            depart_creator,
            can_access_depart_user,
            self.simple_user
        ]:
            response = self.auth_patch(user, {}, [self.target_task.id])
            self.assertEqual(response.status_code, self.status.HTTP_404_NOT_FOUND)
            self.assertIsNotNone(response.data.get("detail", None))
    
    def test_simple_assigned_to_user_cant_update_task(self):
        self.target_task.assigned_to.add(self.simple_user)
        response = self.auth_patch(self.simple_user, {}, [self.target_task.id])
        self.assertEqual(response.status_code, self.status.HTTP_403_FORBIDDEN)
        self.assertIsNotNone(response.data.get("detail", None))
    
    def test_name_validation_new_and_existing_org(self):
        _, _, new_org = self.create_new_org(owner=self.owner_user)
        _, task = self.create_new_task(new_org)
        test_datas = [
            {'name': self.tasks[1].name},
            {'name': task.name, "org": new_org.id},
        ]
        for req_data in test_datas:
            response = self.auth_patch(self.owner_user, req_data, [self.target_task.id])
            self.assertEqual(response.status_code, self.status.HTTP_400_BAD_REQUEST)
            errors = self.loads(response.content).get('name')
            self.assertIsInstance(errors, list)
        self.target_task.refresh_from_db(fields=["name"])
        self.assertEqual(self.target_task.name, "first_task")
    
    def test_new_org_validation_against_user(self):
        _, _, new_org = self.create_new_org()
        req_data = {"org": new_org.id}
        response = self.auth_patch(self.owner_user, req_data, [self.target_task.id])
        self.assertEqual(response.status_code, self.status.HTTP_400_BAD_REQUEST)
        errors = self.loads(response.content).get('org')
        self.assertIsInstance(errors, list)
        self.target_task.refresh_from_db(fields=["org"])
        self.assertEqual(self.target_task.org.id, self.org.id)

    def test_new_org_validation_against_intance(self):
        _, owner, new_org = self.create_new_org()
        self.org.can_be_accessed_by.add(owner)
        
        # new org owner doesn't have full access over assigned_to
        self.target_task.assigned_to.add(self.simple_user)
        # new org doesn't have full access over tags
        _, new_tag = self.create_new_tag(self.org)
        self.target_task.tags.add(new_tag)
        # new org doesn't have full access over task depart
        _, depart = self.create_new_depart(self.org)
        self.target_task.depart = depart
        self.target_task.save()
        # new org has a task that has the same name with the target task
        self.create_new_task(new_org, name=self.target_task.name)

        req_data = {"org": new_org.id}
        response = self.auth_patch(owner, req_data, [self.target_task.id])
        self.assertEqual(response.status_code, self.status.HTTP_400_BAD_REQUEST)
        errors = self.loads(response.content).get('org')
        self.assertIsInstance(errors, list)
        self.assertEqual(len(errors), 4)
        self.target_task.refresh_from_db(fields=["org"])
        self.assertEqual(self.target_task.org.id, self.org.id)
    
    def test_assigned_to_validation(self):
        _, owner, new_org = self.create_new_org()
        self.simple_user.can_be_accessed_by.add(self.owner_user)
        self.org.can_be_accessed_by.add(owner)

        test_data = [
            {
                "assigned_to": [uuid.uuid4()]
            },
            {
                "assigned_to": [self.create_and_activate_random_user().id]
            },
            {
                "assigned_to": [self.simple_user],
                "org": new_org.id
            }
        ]
        for req_data in test_data:
            response = self.auth_patch(owner, req_data, [self.target_task.id])
            self.assertEqual(response.status_code, self.status.HTTP_400_BAD_REQUEST)
            errors = self.loads(response.content).get('assigned_to')
            self.assertIsInstance(errors, list)
        self.target_task.refresh_from_db(fields=["assigned_to"])
        users = self.target_task.assigned_to.all()
        self.assertEqual(len(users), 0)
    
    def test_due_date_proper_validation(self):
        test_datas = [
            {"due_date": "inavlid-due_date", "field": "due_date"},
            {"priority": "inavlid-priority", "field": "priority"},
            {"status": "inavlid-status", "field": "status"},
            {"estimated_duration": "inavlid-estimated_duration", "field": "estimated_duration"},
            {"actual_duration": "inavlid-actual_duration", "field": "actual_duration"},
        ]
        before_update_data = {
            "priority": self.target_task.priority,
            "due_date": self.target_task.due_date,
            "status": self.target_task.status,
            "estimated_duration": self.target_task.estimated_duration,
            "actual_duration": self.target_task.actual_duration,
        }

        for data in test_datas:
            field = data["field"]
            req_data = {field: data[field]}
            response = self.auth_patch(self.owner_user, req_data, [self.target_task.id])
            self.assertEqual(response.status_code, self.status.HTTP_400_BAD_REQUEST)
            errors = self.loads(response.content).get(field)
            self.assertIsInstance(errors, list)
            self.target_task.refresh_from_db(fields=[field])
            self.assertEqual(getattr(self.target_task, field), before_update_data[field])
    
    def test_tags_validation(self):
        _, owner, new_org = self.create_new_org()
        self.org.can_be_accessed_by.add(owner)

        test_data = [
            {
                "tags": [uuid.uuid4()]
            },
            {
                "tags": [self.create_new_tag(new_org)[1].id]
            },
            {
                "tags": [self.create_new_tag(self.org)[1].id],
                "org": new_org.id
            }
        ]
        for req_data in test_data:
            response = self.auth_patch(owner, req_data, [self.target_task.id])
            self.assertEqual(response.status_code, self.status.HTTP_400_BAD_REQUEST)
            errors = self.loads(response.content).get('tags')
            self.assertIsInstance(errors, list)
        self.target_task.refresh_from_db(fields=["tags"])
        tags = self.target_task.tags.all()
        self.assertEqual(len(tags), 0)
    
    def test_depart_validation(self):
        _, owner, new_org = self.create_new_org()
        self.org.can_be_accessed_by.add(owner)

        test_data = [
            {
                "depart": uuid.uuid4()
            },
            {
                "depart": self.create_new_depart(new_org)[1].id
            },
            {
                "depart": self.create_new_depart(self.org)[1].id,
                "org": new_org.id
            }
        ]
        for req_data in test_data:
            response = self.auth_patch(owner, req_data, [self.target_task.id])
            self.assertEqual(response.status_code, self.status.HTTP_400_BAD_REQUEST)
            errors = self.loads(response.content).get('depart')
            self.assertIsInstance(errors, list)
        self.target_task.refresh_from_db(fields=["depart"])
        self.assertIsNone(self.target_task.depart)
    
    def test_assigned_to_get_added_to_org_when_not_a_members(self):
        self.simple_user.can_be_accessed_by.add(self.owner_user)
        req_data = {"assigned_to": [self.simple_user.id]}
        response = self.auth_patch(self.org_creator, req_data, [self.target_task.id])
        self.assertEqual(response.status_code, self.status.HTTP_200_OK)
        # org get updated
        self.org.refresh_from_db(fields=["members"])
        members = self.org.members.all()
        self.assertIn(self.simple_user, members)
        # data is also updated
        self.target_task.refresh_from_db(fields=["assigned_to"])
        self.assertIn(
            self.simple_user,
            self.target_task.assigned_to.all()
        )
    
    def test_task_owners_can_update_data(self):
        # user who is in assigned to but he is an owner
        self.org.can_be_accessed_by.add(self.simple_user)

        depart_creator, depart = self.create_new_depart(self.org)
        can_access_depart_user = self.create_and_activate_random_user()
        depart.can_be_accessed_by.add(can_access_depart_user)

        task_creator = self.create_and_activate_random_user()
        can_access_task_user = self.create_and_activate_random_user()

        self.target_task.depart = depart
        self.target_task.created_by = task_creator
        self.target_task.save()
        self.target_task.can_be_accessed_by.add(can_access_task_user)
        self.target_task.assigned_to.add(self.simple_user)

        req_data = {
            "name": self.target_task.name,
        }

        for user in [
            self.org_creator,
            self.owner_user,
            self.simple_user,
            depart_creator,
            can_access_depart_user,
            task_creator,
            can_access_task_user,
        ]:
            # ensure the new depart is created has the same owners
            _, new_depart = self.create_new_depart(self.org, creator=depart_creator)
            new_depart.can_be_accessed_by.add(can_access_depart_user)
            req_data["depart"] = new_depart.id

            response = self.auth_patch(user, req_data, [self.target_task.id])
            self.assertEqual(response.status_code, self.status.HTTP_200_OK)
            data = self.loads(response.content)
            self.assertIsNotNone(data["name"])
            self.assertIsNotNone(data["org"])
            self.assertIsNone(data["due_date"])
            self.assertIsNotNone(data["priority"])
            self.assertIsNotNone(data["status"])
            self.assertIsNone(data["estimated_duration"])
            self.assertIsNone(data["actual_duration"])
            self.assertIsNotNone(data.get("tags"))
            self.assertEqual(data["depart"], str(new_depart.id))
            # assert task is updated
            self.target_task.refresh_from_db(fields=['depart'])
            self.assertEqual(self.target_task.depart.id, new_depart.id)