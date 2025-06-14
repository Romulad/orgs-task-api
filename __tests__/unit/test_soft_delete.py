

def test_delete_scenario(self):
        user_creator = self.create_and_activate_random_user()
        user = self.create_and_activate_random_user()
        user.created_by = user_creator
        user.save()

        _, _, random_org = self.create_new_org()

        _, _, org = self.create_new_org(owner=user, creator=user)
        _, depart = self.create_new_depart(random_org)
        depart.members.add(user)
        _, task = self.create_new_task(random_org)
        task.assigned_to.add(user)

        user.delete()