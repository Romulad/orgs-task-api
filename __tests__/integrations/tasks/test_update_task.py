import uuid

from django.forms import model_to_dict

from ..base_classe import BaseTestClass
from tasks.models import Task


class TestUpdateTaskView(BaseTestClass):
    """### Flow
    - user need to be authenticated
    - test user get not found when ressource doesn't exist
    - other depart owners or other user can't udpdate the task obj - 404
    - test assigned to users that has access to the task and it not owner can't update task - 403
    - test all field is required - 400
    - test data validation: (here an instance already exist)
        - test `name` field validation:
            - field is required
            - same name as the default instance name should not cause an error
            - `name` should be unique with the org if new and other than the existing instance name
        - test `description` field validation:
            - field is required
        - test `org` validation:
            - field is required
            - if org id different from existing intance org id test the user updating the ressource 
            has a full access over the new org
            - if org is same as the intance org no validation needed as the org should be validate 
            with the user who is changing it
        - test `assigned_to`:
            - field is required
            - `assigned_to` can be empty but should be include
            - `assigned_to` should be valid user ids
            - the org owner should have a full access over `assigned_to`
        - test `due_date`:
            - field is required
            - can be empty or none
            - test it is properly validate if not null
        - test `priority`:
            - `priority` field should be include
            - user can not choose different `priority` value
        - test `status`:
            - `status` field should be include
            - user can not choose different `status` value
        - test `estimated_duration`:
            - field is required
            - can be empty or none
            - test it is properly validate if not null
        - test `actual_duration`:
            - field is required
            - can be empty or none
            - test it is properly validate if not null
        - test `tags` validation:
            - field is required
            - test the tags should exist
            - test the tags specified for the task should all belongs to the specified org, we should
            not include a tag from another org
            - test can be an empty list
        - test `depart` vaidation if specified:
            - field is required
            - test depart exist first
            - test the depart specified should be in the org specified
            - test depart can be null/none/empty
    - test assigned_to get automatically added to specified org if not existed by default
    - test access allowed user:
        - org owners
        - depart owners
        - task owners
    can successfully update task with needed data and needed response is returned
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
        self.req_data = {key: value if value != None else "" for key, value in model_to_dict(self.target_task).items()}
        self.simple_user = self.create_and_activate_random_user()
    
    def test_only_authenticated_user_can_access(self):
        self.evaluate_method_unauthenticated_request(
            self.HTTP_PUT, ["fake-id"]
        )
    
    def test_not_found_ressource(self):
        response = self.auth_put(self.owner_user, {}, [uuid.uuid4()])
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
            response = self.auth_put(user, {}, [self.target_task.id])
            self.assertEqual(response.status_code, self.status.HTTP_404_NOT_FOUND)
            self.assertIsNotNone(response.data.get("detail", None))
    
    def test_simple_assigned_to_user_cant_update_task(self):
        self.target_task.assigned_to.add(self.simple_user)
        response = self.auth_put(self.simple_user, {}, [self.target_task.id])
        self.assertEqual(response.status_code, self.status.HTTP_403_FORBIDDEN)
        self.assertIsNotNone(response.data.get("detail", None))
    
    def test_all_field_should_be_include(self):
        del self.req_data["priority"]
        response = self.auth_put(self.owner_user, self.req_data, [self.target_task.id])
        self.assertEqual(response.status_code, self.status.HTTP_400_BAD_REQUEST)
        self.assertIsNotNone(response.data.get("priority", None))
    
    def test_name_field_validation(self):
        del self.req_data["name"]
        test_datas = [
            {**self.req_data},
            {**self.req_data, "name": self.tasks[1].name},
        ]
        for req_data in test_datas:
            response = self.auth_put(self.owner_user, req_data, [self.target_task.id])
            self.assertEqual(response.status_code, self.status.HTTP_400_BAD_REQUEST)
            errors = self.loads(response.content).get('name')
            self.assertIsInstance(errors, list)
        self.target_task.refresh_from_db(fields=["name"])
        self.assertEqual(self.target_task.name, "first_task")
    
    def test_name_field_can_be_the_current_instance_name(self):
        response = self.auth_put(self.owner_user, self.req_data, [self.target_task.id])
        self.assertEqual(response.status_code, self.status.HTTP_200_OK)
    
    def test_description_field_validation(self):
        del self.req_data["description"]
        response = self.auth_put(self.owner_user, self.req_data, [self.target_task.id])
        self.assertEqual(response.status_code, self.status.HTTP_400_BAD_REQUEST)
        errors = self.loads(response.content).get('description')
        self.assertIsInstance(errors, list)

    def test_org_validation(self):
        del self.req_data["org"]
        self.target_task.can_be_accessed_by.add(self.simple_user)
        _, _, new_org = self.create_new_org()
        test_datas = [
            {
                "user": self.owner_user, 
                "req_data": {**self.req_data}
            },
            {
                "user": self.owner_user, 
                "req_data": {**self.req_data, "org": uuid.uuid4()}
            },
            {
                "user": self.simple_user, 
                "req_data": {**self.req_data, "org": new_org.id}
            }
        ]
        for data in test_datas:
            req_data = data["req_data"]
            current_user = data["user"]
            response = self.auth_put(current_user, req_data, [self.target_task.id])
            self.assertEqual(response.status_code, self.status.HTTP_400_BAD_REQUEST)
            errors = self.loads(response.content).get('org')
            self.assertIsInstance(errors, list)
        self.target_task.refresh_from_db()
        self.assertNotEqual(self.target_task.org.id, new_org.id)
    
    def test_same_org_can_be_specified_by_no_org_owner_but_task_owner(self):
        self.target_task.can_be_accessed_by.add(self.simple_user)
        response = self.auth_put(self.simple_user, self.req_data, [self.target_task.id])
        self.assertEqual(response.status_code, self.status.HTTP_200_OK)
    
    def test_assigned_to_validation(self):
        del self.req_data["assigned_to"]
        test_datas = [
            {**self.req_data},
            {**self.req_data, "assigned_to": ["inavlid-id"]},
            {**self.req_data, "assigned_to": [uuid.uuid4()]},
            {**self.req_data, "assigned_to": [self.simple_user.id]},
        ]
        # simulate the fact that user making the request has access to the user but not the org owner
        self.simple_user.can_be_accessed_by.add(self.org_creator)

        for req_data in test_datas:
            response = self.auth_put(self.org_creator, req_data, [self.target_task.id])
            self.assertEqual(response.status_code, self.status.HTTP_400_BAD_REQUEST)
            errors = self.loads(response.content).get('assigned_to')
            self.assertIsNotNone(errors)
        self.target_task.refresh_from_db()
        self.assertEqual(len(self.target_task.assigned_to.all()), 0)
    
    def test_due_date_validation(self):
        del self.req_data["due_date"]
        test_datas = [
            {**self.req_data},
            {**self.req_data, "due_date": "inavlid-due_date"}
        ]
        for req_data in test_datas:
            response = self.auth_put(self.owner_user, req_data, [self.target_task.id])
            self.assertEqual(response.status_code, self.status.HTTP_400_BAD_REQUEST)
            errors = self.loads(response.content).get('due_date')
            self.assertIsNotNone(errors)
        self.target_task.refresh_from_db()
        self.assertIsNone(self.target_task.due_date)
    
    def test_due_date_is_required_but_can_be_empty(self):
        self.req_data["due_date"] = ""
        response = self.auth_put(self.owner_user, self.req_data, [self.target_task.id])
        self.assertEqual(response.status_code, self.status.HTTP_200_OK)
    
    def test_priority_validation(self):
        del self.req_data["priority"]
        test_datas = [
            {**self.req_data},
            {**self.req_data, "priority": "inavlid-priority"}
        ]
        for req_data in test_datas:
            response = self.auth_put(self.owner_user, req_data, [self.target_task.id])
            self.assertEqual(response.status_code, self.status.HTTP_400_BAD_REQUEST)
            errors = self.loads(response.content).get('priority')
            self.assertIsInstance(errors, list)
        self.target_task.refresh_from_db()
        self.assertNotEqual(self.target_task.priority, "inavlid-priority")
    
    def test_status_validation(self):
        del self.req_data["status"]
        test_datas = [
            {**self.req_data},
            {**self.req_data, "status": "inavlid-status"}
        ]
        for req_data in test_datas:
            response = self.auth_put(self.owner_user, req_data, [self.target_task.id])
            self.assertEqual(response.status_code, self.status.HTTP_400_BAD_REQUEST)
            errors = self.loads(response.content).get('status')
            self.assertIsInstance(errors, list)
        self.target_task.refresh_from_db()
        self.assertNotEqual(self.target_task.status, "inavlid-status")
    
    def test_actual_duration_and_estimated_duration_validation(self):
        for to_check in ["actual_duration", "estimated_duration"]:
            del self.req_data[to_check]
            test_datas = [
                {**self.req_data},
                {**self.req_data, to_check: f"inavlid-{to_check}"}
            ]
            for req_data in test_datas:
                response = self.auth_put(self.owner_user, req_data, [self.target_task.id])
                self.assertEqual(response.status_code, self.status.HTTP_400_BAD_REQUEST)
                errors = self.loads(response.content).get(to_check)
                self.assertIsNotNone(errors)
            self.target_task.refresh_from_db()
            self.assertIsNone(getattr(self.target_task, to_check))
            self.req_data[to_check] = None

    def test_estimated_duration_and_actual_duration_are_required_but_can_be_empty(self):
        self.req_data["estimated_duration"] = ""
        self.req_data["actual_duration"] = ""
        response = self.auth_put(self.owner_user, self.req_data, [self.target_task.id])
        self.assertEqual(response.status_code, self.status.HTTP_200_OK)
    
    def test_tags_validation(self):
        del self.req_data["tags"]
        _, _, new_org = self.create_new_org()
        _, other_tag = self.create_new_tag(new_org)
        test_datas = [
            {**self.req_data},
            {**self.req_data, "tags": ["inavlid-id"]},
            {**self.req_data, "tags": [uuid.uuid4()]},
            {**self.req_data, "tags": [other_tag.id]},
        ]
        for req_data in test_datas:
            response = self.auth_put(self.owner_user, req_data, [self.target_task.id])
            self.assertEqual(response.status_code, self.status.HTTP_400_BAD_REQUEST)
            errors = self.loads(response.content).get('tags')
            self.assertIsInstance(errors, list)
        self.target_task.refresh_from_db()
        self.assertEqual(len(self.target_task.tags.all()), 0)
    
    def test_tags_can_be_empty_list(self):
        self.req_data["tags"] = []
        response = self.auth_put(self.owner_user, self.req_data, [self.target_task.id])
        self.assertEqual(response.status_code, self.status.HTTP_200_OK)
    
    def test_depart_validation(self):
        del self.req_data["depart"]
        _, _, new_org = self.create_new_org()
        _, depart = self.create_new_depart(new_org)
        test_datas = [
            {**self.req_data},
            {**self.req_data, "depart": "inavlid-id"},
            {**self.req_data, "depart": uuid.uuid4()},
            {**self.req_data, "depart": depart.id},
        ]
        for req_data in test_datas:
            response = self.auth_put(self.owner_user, req_data, [self.target_task.id])
            self.assertEqual(response.status_code, self.status.HTTP_400_BAD_REQUEST)
            errors = self.loads(response.content).get('depart')
            self.assertIsInstance(errors, list)
        self.target_task.refresh_from_db()
        self.assertIsNone(self.target_task.depart)
    
    def test_depart_can_be_empty(self):
        self.req_data["depart"] = ""
        response = self.auth_put(self.owner_user, self.req_data, [self.target_task.id])
        self.assertEqual(response.status_code, self.status.HTTP_200_OK)
    
    def test_assigned_to_get_added_to_org_when_not_a_members(self):
        self.simple_user.can_be_accessed_by.add(self.owner_user)
        self.req_data["assigned_to"] = [self.simple_user.id]
        response = self.auth_put(self.org_creator, self.req_data, [self.target_task.id])
        self.assertEqual(response.status_code, self.status.HTTP_200_OK)
        self.org.refresh_from_db()
        members = self.org.members.all()
        self.assertIn(self.simple_user, members)
    
    def test_allow_user_can_update_data(self):
        _, creator, org = self.create_new_org(owner=self.owner_user)
        _, depart = self.create_new_depart(org)
        self.req_data["name"] = "new_random_name"
        self.req_data["org"] = org.id
        self.req_data["depart"] = depart.id

        response = self.auth_put(creator, self.req_data, [self.target_task.id])
        self.assertEqual(response.status_code, self.status.HTTP_200_OK)
        # assert response data
        response_data = self.loads(response.content)
        self.assertEqual(response_data["name"], self.req_data["name"])
        self.assertEqual(response_data["org"], str(org.id))
        self.assertEqual(response_data["due_date"], self.req_data["due_date"])
        self.assertEqual(response_data["priority"], self.req_data["priority"])
        self.assertEqual(response_data["status"], self.req_data["status"])
        self.assertEqual(response_data["estimated_duration"], self.req_data["estimated_duration"])
        self.assertEqual(response_data["actual_duration"], self.req_data["actual_duration"])
        self.assertIsNotNone(response_data.get("tags"))
        self.assertEqual(response_data["depart"], str(depart.id))
        # assert task is updated
        self.target_task.refresh_from_db()
        self.assertEqual(self.target_task.name, self.req_data["name"])
        self.assertEqual(self.target_task.org.id, org.id)
        self.assertEqual(self.target_task.depart.id, depart.id)
    
    def test_other_task_owners_can_update_data(self):
        depart_creator, depart = self.create_new_depart(self.org)
        can_access_depart_user = self.create_and_activate_random_user()
        depart.can_be_accessed_by.add(can_access_depart_user)

        task_creator = self.create_and_activate_random_user()
        can_access_task_user = self.create_and_activate_random_user()

        # user who is in assigned to but it an owner
        depart.can_be_accessed_by.add(self.simple_user)

        self.target_task.depart = depart
        self.target_task.created_by = task_creator
        self.target_task.save()
        self.target_task.can_be_accessed_by.add(can_access_task_user)
        self.target_task.assigned_to.add(self.simple_user)

        for user in [
            depart_creator,
            can_access_depart_user,
            task_creator,
            can_access_task_user,
            self.simple_user
        ]:
            self.req_data["name"] = "new_name_for_tsk_%s" % (user.email)
            response = self.auth_put(user, self.req_data, [self.target_task.id])
            self.assertEqual(response.status_code, self.status.HTTP_200_OK)
            # assert task is updated
            self.target_task.refresh_from_db()
            self.assertEqual(self.target_task.name, self.req_data["name"])




