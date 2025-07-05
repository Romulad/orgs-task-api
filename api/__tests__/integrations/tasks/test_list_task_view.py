from ...base_classe import BaseTestClass
from tasks.models import Task

class TestListTaskView(BaseTestClass):
    """### Flow
    - user need to be authenticated
    - test user without access can not get any task
    - test for user that has acess:
        - org owner or has access to org should be able to get all tasks available in the org
        - depart creator or has access to should be able to get all tasks attached to his department
        - task creator should be able to get tasks he created
        - user in can_be_accessed_by on task should be able to get all task where he has access
        - user assigne_to should be able to get all tasks he is part of
    - test user can get needed data
    - test response is paginated
    - test we can apply filters, e.g a search through filter
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

    def setUp(self):
        self.owner_user, self.org_creator, self.org = self.create_new_org()
        task_data = [*self.task_data]
        for data in task_data:
            data["org"] = self.org
        self.tasks = self.bulk_create_object(Task, task_data)
        self.simple_user = self.create_and_active_user(email="simple_user@gamail.com")

    def test_only_authenticated_user_can_access(self):
        self.evaluate_method_unauthenticated_request(
            self.HTTP_GET
        )
    
    def test_user_without_access_cant_get_any_ressources(self):
        new_owner, _, _ = self.create_new_org()
        response = self.auth_get(new_owner)
        self.assertEqual(response.status_code, self.status.HTTP_200_OK)
        data = self.loads(response.content).get("results")
        self.assertEqual(len(data), 0)
    
    def test_org_creator_access_allowed_and_owner_get_needed_data(self):
        # someone who has access to the org
        self.org.can_be_accessed_by.add(self.simple_user)

        for user in [self.org_creator, self.owner_user, self.simple_user]:
            response = self.auth_get(user)
            self.assertEqual(response.status_code, self.status.HTTP_200_OK)
            data = self.loads(response.content).get("results")
            self.assertEqual(len(data), len(self.tasks))
            d_ids = [str(obj.id) for obj in self.tasks]
            for result in data:
                self.assertIn(result["id"], d_ids)
                self.assertIsNotNone(result.get("name"))
                self.assertIsNot(result.get("description", 0), 0)
                self.assertIsNotNone(result.get("created_at"))
                self.assertIsNot(result.get("due_date", 0), 0)
                self.assertIsNot(result.get("actual_duration", 0), 0)
                self.assertIsNot(result.get("estimated_duration", 0), 0)
                self.assertIsNotNone(result.get("status"))
                self.assertIsNotNone(result.get("priority"))
    
    def test_depart_creator_access_allowed_get_needed_data(self):
        # create new depart
        depart_creator, depart = self.create_new_depart(self.org)

        # for user who has access to depart
        access_to_depart = self.create_and_activate_random_user()
        depart.can_be_accessed_by.add(access_to_depart)

        # update task to point to department
        depart_tasks = self.tasks[:2]
        for task in depart_tasks:
            task.depart = depart
            task.save()
        
        for user in [depart_creator, access_to_depart]:
            response = self.auth_get(user)
            self.assertEqual(response.status_code, self.status.HTTP_200_OK)
            data = self.loads(response.content).get("results")
            self.assertEqual(len(data), len(depart_tasks))
            d_ids = [str(obj.id) for obj in depart_tasks]
            for result in data:
                self.assertIn(result["id"], d_ids)
    
    def task_creator_or_allow_access_in_org_get_needed_data(self):
        task_creator = self.create_and_activate_random_user()
        can_access_task_user = self.create_and_activate_random_user()

        # update task to point to task_creator
        depart_tasks = self.tasks[1:]
        for task in depart_tasks:
            task.created_by = task_creator
            task.can_be_accessed_by.add(can_access_task_user)
            task.save()
        
        for user in [task_creator, can_access_task_user]:
            response = self.auth_get(user)
            self.assertEqual(response.status_code, self.status.HTTP_200_OK)
            data = self.loads(response.content).get("results")
            self.assertEqual(len(data), len(depart_tasks))
            d_ids = [str(obj.id) for obj in depart_tasks]
            for result in data:
                self.assertIn(result["id"], d_ids)
    
    def test_user_assigne_to_task_get_needed_data(self):
        assigne_user = self.create_and_activate_random_user()

        # update task to point to assigne_user
        depart_tasks = self.tasks[2:]
        for task in depart_tasks:
            task.assigned_to.add(assigne_user)
        
        response = self.auth_get(assigne_user)
        self.assertEqual(response.status_code, self.status.HTTP_200_OK)
        data = self.loads(response.content).get("results")
        self.assertEqual(len(data), len(depart_tasks))
        d_ids = [str(obj.id) for obj in depart_tasks]
        for result in data:
            self.assertIn(result["id"], d_ids)
    
    def test_can_filter_data(self):
        response = self.auth_get(self.owner_user, query_params={"search": "d"})
        self.assertEqual(response.status_code, self.status.HTTP_200_OK)
        data = self.loads(response.content).get("results")
        self.assertEqual(len(data), 2)
        names = ["second_task", "third_task"]
        for result in data:
            self.assertIn(result["name"], names)
    
    def test_filter_by_assigned_to(self):
        tasks = self.tasks[1:]
        for task in tasks:
            task.assigned_to.add(self.simple_user)

        response = self.auth_get(
            self.owner_user, 
            query_params={"assigned_to_ids": "%s" % (str(self.simple_user.id))}
        )
        self.assertEqual(response.status_code, self.status.HTTP_200_OK)
        data = self.loads(response.content).get("results")
        self.assertEqual(len(data), 2)
        ids = [str(t.id) for t in tasks]
        for result in data:
            self.assertIn(result["id"], ids)
    
    def test_filter_by_assigned_to_emails(self):
        tasks = self.tasks[1:]
        for task in tasks:
            task.assigned_to.add(self.simple_user)

        response = self.auth_get(
            self.owner_user, 
            query_params={"assigned_to_emails": "%s," % (self.simple_user.email)}
        )
        self.assertEqual(response.status_code, self.status.HTTP_200_OK)
        data = self.loads(response.content).get("results")
        self.assertEqual(len(data), 2)
        ids = [str(t.id) for t in tasks]
        for result in data:
            self.assertIn(result["id"], ids)
    