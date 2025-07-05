from ..base_classe import BaseTestClass

from app_lib.authorization import auth_checker
from app_lib.app_permssions import get_perm_list


class TestUserHasPermFn(BaseTestClass):
    """
    - test when user is:
        - not part of the org, but has the perm in another org, should return false
        - part of the organization but without perm, and has the perm in another org, return false
        - part of the org with user perm obj containing the perm, return True
        - part of the org with role obj containing the perm, return True
    - for unknow perm string, should always return False no matter if user has the fake 'perm' or not
    - test perm check for org owners:
        - creator has all permission, always return True
        - owner and user in can_be_accessed_by have all default permission
        - owner and user in can_be_accessed_by do not have creator permission
        - another org owners perm check should return False
    """

    def setUp(self):
        self.org_owner, self.org_creator, self.org = self.create_new_org()
        self.user = self.create_and_activate_random_user()
        self.perm = get_perm_list()[0]
    
    def create_perm_for_user_in_another_org(self):
        # the user has the perm in another org, both from perm object and role
        _, _, new_org = self.create_new_org()
        _, _, perm_obj = self.create_new_permission(new_org, self.user)
        perm_obj.add_permissions(self.perm)
        _, role = self.create_new_role(new_org)
        role.add_permissions(self.perm)
        role.users.add(self.user)
    
    def create_perm_for_user_in_org(
        self, 
        perm=[], 
        only_perm_obj=False,
        only_role_obj=False
    ):
        self.org.members.add(self.user)
        if not only_role_obj:
            _, _, perm_obj = self.create_new_permission(self.org, self.user)
            perm_obj.add_permissions(perm)
        if not only_perm_obj:
            _, role = self.create_new_role(self.org)
            role.add_permissions(perm)
            role.users.add(self.user)
    
    def test_perm_for_no_org_user(self):
        self.create_perm_for_user_in_another_org()
        # user does not have the perm for this org
        self.assertFalse(
            auth_checker.has_permission(self.user, self.org, self.perm)
        )
    
    def test_check_for_org_user_without_perm(self):
        self.create_perm_for_user_in_another_org()
        # user does not have the perm for this org and he is part of it
        self.create_perm_for_user_in_org()
        self.assertFalse(
            auth_checker.has_permission(self.user, self.org, self.perm)
        )
    
    def test_perm_check_from_perm_obj(self):
        self.create_perm_for_user_in_org(self.perm, only_perm_obj=True)
        self.assertTrue(
            auth_checker.has_permission(self.user, self.org, self.perm)
        )
    
    def test_perm_check_from_role_obj(self):
        self.create_perm_for_user_in_org(self.perm, only_role_obj=True)
        self.assertTrue(
            auth_checker.has_permission(self.user, self.org, self.perm)
        )
    
    def test_for_fake_perm_str(self):
        fake_perm = "fake_perm_str"
        self.org.members.add(self.user)
        _, _, perm_obj = self.create_new_permission(self.org, self.user)
        perm_obj.add_permissions(fake_perm)
        self.assertFalse(
            auth_checker.has_permission(self.user, self.org, fake_perm)
        )
    
    def test_perm_check_for_org_creator(self):
        self.assertTrue(
            auth_checker.has_permission(self.org_creator, self.org, self.perm)
        )

    def test_perm_check_for_org_owners(self):
        perm = get_perm_list(default_only=True)[0]
        self.org.can_be_accessed_by.add(self.user)
        for user in [
            self.org_owner,
            self.user
        ]:
            self.assertTrue(
                auth_checker.has_permission(user, self.org, perm)
            )
        
    def test_org_owners_than_creator_do_not_have_creator_perm_by_default(self):
        perm = get_perm_list(creator_only=True)[0]
        self.org.can_be_accessed_by.add(self.user)
        for user in [
            self.org_owner,
            self.user
        ]:
            self.assertFalse(
                auth_checker.has_permission(user, self.org, perm)
            )

    def test_perm_check_for_another_org_owners(self):
        new_owner, new_creator, org = self.create_new_org()
        org.can_be_accessed_by.add(self.user)
        for user in [
            new_creator,
            new_owner,
            self.user,
        ]:
            self.assertFalse(
                auth_checker.has_permission(user, self.org, self.perm)
            )