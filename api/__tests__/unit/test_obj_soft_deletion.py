from ..base_classe import BaseTestClass

class TestObjSoftDeletion(BaseTestClass):
    """
    - create a user and delete it, should be deleted with is_deleted and still on all_object
    - create a user A, create a related org with user A as creator, create a related user B to user A
    that will be used as the org owner. Then:
        - Deleting the owner, should not cause any problem, only him will be deleted
        - Deleting the user A all other related ressource should be deleted. Reset the owner before
        deletion to check if he gets deleted successfully as the user A is his creator
    - for M2M, create user A, create an org and add him as member, create a task and add him as
    task creator and in assigned_to user, create department and add user A as member to then delete
    user A:
        - user A should be deleted successfully from objects
        - should not exist as org member anymore
        - will be deleted from task creator and assigned_to
        - should be removed from department members
        - should still available on all_objects
    - for nested relation, create user A, create a related org with user A as creator, 
    create related depart for the org, create task related to the org, create a role related to org then
    delete user A, every created ressource should be deleted with is_deleted and still available 
    through all_objects
    - test a hard deletion work as it should, no ressource will be available either on objects nor on 
    all_objects after deletion
    - simulate many object creation
    """

    def setUp(self):
        self.user_a = self.create_and_activate_random_user()
        self.user_class = self.user_a.__class__
        self.owner, self.creator, self.org = self.create_new_org()
        self.org_class = self.org.__class__
    
    def test_simple_deletion(self):
        self.user_a.delete()
        # Check if the user is soft deleted
        with self.assertRaises(self.user_class.DoesNotExist):
            self.user_class.objects.get(id=self.user_a.id)
        # Check if the user is still available in all_objects
        user_object = self.user_class.all_objects.get(id=self.user_a.id)
        self.assertTrue(user_object.is_deleted)
    
    def test_direct_related_deletion(self):
        """
        - create a user A, create a related org with user A as creator, create a related user B to user A
        that will be used as the org owner. Then:
            - Deleting the owner, should not cause any problem, only him will be deleted
            - Deleting the user A all other related ressource should be deleted. Reset the owner before
            deletion to check if he gets deleted successfully as the user A is his creator
        """
        # user related to user_a
        user_b = self.create_and_activate_random_user()
        user_b.created_by = self.user_a
        user_b.save()
        # org
        self.org.created_by = self.user_a
        self.org.owner = user_b
        self.org.save()
        # delete org owner, nothing should happen other than setting owner to null on org.
        # then reset data as previous to perform delete on user_a
        self.assertIsNotNone(self.org_class.objects.get(id=self.org.id).owner)
        user_b.delete()
        user_a_org = self.org_class.objects.get(id=self.org.id)
        self.assertIsNone(user_a_org.owner)
        user_a_org.owner = user_b
        user_a_org.save()
        user_b.is_deleted = False
        user_b.save()
        # delete user_a
        self.user_a.delete()
        for ressource, obj_class in [
            (user_a_org, self.org_class),
            (self.user_a, self.user_class),
            (user_b, self.user_class),
        ]:
            with self.assertRaises(obj_class.DoesNotExist):
                obj_class.objects.get(id=ressource.id)
    
    def test_m2m_clean_up(self):
        """
        - for M2M, create user A, create an org and add him as member, create a task and add him as
        task creator and in assigned_to user, create department and add user A as member to then delete
        user A:
            - user A should be deleted successfully from objects
            - should not exist as org member anymore
            - will be deleted from task creator and assigned_to
            - should be removed from department members
            - should still available on all_objects
        """
        self.org.members.add(self.user_a)
        # task
        _, task = self.create_new_task(self.org, creator=self.user_a)
        task.assigned_to.add(self.user_a)
        # depart
        _, depart = self.create_new_depart(self.org, creator=self.user_a)
        depart.members.add(self.user_a)
        # delete user_a
        self.user_a.delete()
        with self.assertRaises(self.user_class.DoesNotExist):
            self.user_class.objects.get(id=self.user_a.id)
        # org clean up
        self.org.refresh_from_db()
        self.assertNotIn(self.user_a, self.org.members.all())
        # task clean up
        task.refresh_from_db()
        self.assertIsNone(task.created_by)
        self.assertNotIn(self.user_a, task.assigned_to.all())
        # depart clean up
        depart.refresh_from_db()
        self.assertIsNone(depart.created_by)
        self.assertNotIn(self.user_a, depart.members.all())
        # all_objects
        self.user_class.all_objects.get(id=self.user_a.id)
    
    def test_nested_relation_deletion(self):
        """
        - for nested relation, create user A, create a related org with user A as creator, 
        create related depart for the org, create task related to the org, create a role related to org then
        delete user A, every created ressource should be deleted with is_deleted and still available 
        through all_objects
        """
        self.org.created_by = self.user_a
        self.org.save()
        # more org
        orgs = [self.create_new_org(creator=self.user_a)[-1] for _ in range(10)]
        # departs in org
        departs = [self.create_new_depart(self.org)[-1] for _ in range(10)]
        depart_class = departs[0].__class__
        # tasks in org
        tasks = [self.create_new_task(self.org)[-1] for _ in range(10)]
        task_class = tasks[0].__class__
        # roles in org
        roles = [self.create_new_role(self.org)[-1] for _ in range(10)]
        role_class = roles[0].__class__
        # delete user_a
        self.user_a.delete()
        for ressource, obj_class in [
            (self.user_a, self.user_class),
            (self.org, self.org_class),
            *[(org, self.org_class) for org in orgs],
            *[(depart, depart_class) for depart in departs],
            *[(task, task_class) for task in tasks],
            *[(role, role_class) for role in roles]
        ]:
            with self.assertRaises(obj_class.DoesNotExist):
                obj_class.objects.get(id=ressource.id)
            obj_class.all_objects.get(id=ressource.id)
            
    def test_hard_deletion(self):
        self.user_a.hard_delete()
        # Check if the user is totally deleted
        with self.assertRaises(self.user_class.DoesNotExist):
            self.user_class.objects.get(id=self.user_a.id)
        with self.assertRaises(self.user_class.DoesNotExist):
            self.user_class.all_objects.get(id=self.user_a.id)