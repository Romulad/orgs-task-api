from ..base_classe import BaseTestClass


class TestQuerysetSoftDeletion(BaseTestClass):
    """
    - create users and delete them, should be deleted with is_deleted and still on all_object
    - create many user A, create a related orgs for each user A as creator, create a related 
    user B for each user A. Then:
        - Deleting the users A, all orgs and user B related should be deleted
    - for M2M, create many user A, create org and add each user A as member, create a task 
    and add each user A as an assigned_to user, create department and add each user A as member, 
    then delete all user A using a queryset:
        - users A should not exist as org member anymore
        - will be deleted from task assigned_to
        - should be removed from department members
        - should still available on all_objects
    - for field update, create many user A, create orgs with each user A as owner, create a tasks
    and add each user A as task creator, create department and add each user A as creator, then delete
    users A using a queryset:
        - all orgs owner should be set to null
        - all tasks created creator should be set to null
        - all departments creator should be set to null
    - for nested relation, create many user A, create a related orgs for each user A as creator, 
    create many related departs for each org, create many task related to each org, 
    create roles related to each org then delete all user A using a queryset, every created 
    ressources for each user should be deleted with is_deleted and still available through all_objects
    - test a hard deletion work as it should, no ressource will be available either on objects nor on 
    all_objects after deletion
    - simulate many object creation
    """

    def setUp(self):
        self.users_a = [self.create_and_activate_random_user() for _ in range(10)]
        self.user_pks = [obj.id for obj in self.users_a]
        self.user_class = self.users_a[0].__class__
        self.orgs = [self.create_new_org()[-1] for _ in range(10)]
        self.org_class = self.orgs[0].__class__
    
    def delete_users_a(self):
        self.user_class.objects.filter(id__in=self.user_pks).delete()
    
    def test_simple_deletion(self):
        self.delete_users_a()
        # Check if the users are soft deleted
        for user_pk in self.user_pks:
            with self.assertRaises(self.user_class.DoesNotExist):
                self.user_class.objects.get(id=user_pk)
            # Check if the user is still available in all_objects
            user_object = self.user_class.all_objects.get(id=user_pk)
            self.assertTrue(user_object.is_deleted)
    
    def test_direct_related_deletion(self):
        """
        - create many user A, create a related orgs for each user A as creator, create a related 
        user B for each user A. Then:
        - Deleting the users A, all orgs and user B related should be deleted
        """
        # org
        for org, user_a in zip(self.orgs, self.users_a):
            org.created_by = user_a
            org.save()
        # user related to user_a
        users_b = []
        for user_a in self.users_a:
            user_b = self.create_and_activate_random_user()
            user_b.created_by = user_a
            user_b.save()
            users_b.append(user_b)
        # delete users_a
        self.delete_users_a()
        # ressources deletion
        for ressource, obj_class in [
            *[(deleted_org, self.org_class) for deleted_org in self.orgs],
            *[(deleted_user_a, self.user_class) for deleted_user_a in self.users_a],
            *[(deleted_user_b, self.user_class) for deleted_user_b in users_b],
        ]:
            with self.assertRaises(obj_class.DoesNotExist):
                obj_class.objects.get(id=ressource.id)
            obj_class.all_objects.get(id=ressource.id)
    
    def test_m2m_clean_up(self):
        """
        - for M2M, create many user A, create org and add each user A as member, create a task 
        and add each user A as an assigned_to user, create department and add each user A as member, 
        then delete all user A using a queryset:
            - users A should not exist as org member anymore
            - will be deleted from task assigned_to
            - should be removed from department members
        """
        org = self.orgs[0]
        org.members.add(*self.users_a)
        # task
        _, task = self.create_new_task(org)
        task.assigned_to.add(*self.users_a)
        # depart
        _, depart = self.create_new_depart(org)
        depart.members.add(*self.users_a)
        # delete users_a
        self.delete_users_a()
        # org clean up
        updated_org = self.org_class.objects.get(id=org.id)
        updated_task = task.__class__.objects.get(id=task.id)
        updated_depart = depart.__class__.objects.get(id=depart.id)
        for deleted_user_a in self.users_a:
            self.assertNotIn(deleted_user_a, updated_org.members.all())
            self.assertNotIn(deleted_user_a, updated_task.assigned_to.all())
            self.assertNotIn(deleted_user_a, updated_depart.members.all())
    
    def test_field_update_on_deletion(self):
        """
        - for field update, create many user A, create orgs with each user A as owner, create a tasks
        and add each user A as task creator, create department and add each user A as creator, then delete
        users A using a queryset:
            - all orgs owner should be set to null
            - all tasks created creator should be set to null
            - all departments creator should be set to null
        """
        # org
        for org, user_a in zip(self.orgs, self.users_a):
            org.owner = user_a
            org.save()
        # tasks
        tasks = []
        for task_creator in self.users_a:
            _, task = self.create_new_task(self.orgs[0])
            task.created_by = task_creator
            task.save()
            tasks.append(task)
        # departs
        departs = []
        for depart_creator in self.users_a:
            _, depart = self.create_new_depart(self.orgs[0])
            depart.created_by = depart_creator
            depart.save()
            departs.append(task)
        # delete users A
        self.delete_users_a()
        # clean up
        for ressource, obj_class, attr in [
            *[(org, self.org_class, "owner") for org in self.orgs],
            *[(task, tasks[0].__class__, "created_by") for task in tasks],
            *[(depart, departs[0].__class__, "created_by") for depart in departs],
        ]:
            updated_obj = obj_class.objects.get(id=ressource.id)
            self.assertIsNone(getattr(updated_obj, attr))

    def test_nested_relation_deletion(self):
        """
        - for nested relation, create many user A, create a related orgs for each user A as creator, 
        create many related departs for each org, create many task related to each org, 
        create roles related to each org then delete all user A using a queryset, every created 
        ressources for each user should be deleted with is_deleted and still available 
        through all_objects
        """
        # 2 orgs per user
        orgs = [*self.orgs]
        for org, user_a in zip(self.orgs, self.users_a):
            org.created_by = user_a
            org.save()
            # more org
            orgs.extend([self.create_new_org(creator=user_a)[-1] for _ in range(1)])
        # 2 departs, tasks, roles per org
        departs = []
        tasks = []
        roles = []
        for new_org in orgs:
            departs.extend([
                self.create_new_depart(new_org)[-1] for _ in range(2)
            ])
            tasks.extend ([
                self.create_new_task(new_org)[-1] for _ in range(2)
            ])
            roles.extend([
                self.create_new_role(new_org)[-1] for _ in range(2)
            ])
        depart_class = departs[0].__class__
        task_class = tasks[0].__class__
        role_class = roles[0].__class__
        # delete users_a
        self.delete_users_a()
        for ressource, obj_class in [
            *[(deleted_user, self.user_class) for deleted_user in self.users_a],
            *[(org, self.org_class) for org in orgs],
            *[(depart, depart_class) for depart in departs],
            *[(task, task_class) for task in tasks],
            *[(role, role_class) for role in roles]
        ]:
            with self.assertRaises(obj_class.DoesNotExist):
                obj_class.objects.get(id=ressource.id)
            obj_class.all_objects.get(id=ressource.id)
            
    def test_hard_deletion(self):
        self.user_class.objects.filter(id__in=self.user_pks).hard_delete()
        # Check if the user is totally deleted
        for user_pk in self.user_pks:
            with self.assertRaises(self.user_class.DoesNotExist):
                self.user_class.objects.get(id=user_pk)
            with self.assertRaises(self.user_class.DoesNotExist):
                self.user_class.all_objects.get(id=user_pk)