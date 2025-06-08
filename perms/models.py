from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from app_lib.models import AbstractBaseModel
from organization.models import Organization
from app_lib.app_permssions import permissions_exist


User =  settings.AUTH_USER_MODEL

class UserPermissions(AbstractBaseModel):
    '''User permissions in an organization'''
    user = models.ForeignKey(
        User, on_delete=models.CASCADE,
        verbose_name=_("User")
    )
    org = models.ForeignKey(
        Organization, on_delete=models.CASCADE,
        verbose_name=_("Organization")
    )
    perms = models.TextField()

    class Meta:
        verbose_name = _("User permission")
        verbose_name_plural = _("User permissions")
        unique_together = ("user", "org")

    def __str__(self):
        return super().__str__()
    
    def save_perms(self, perms:list):
        updated_perms = ",".join(perms)
        self.perms = updated_perms
        self.save()

    def get_perms(self):
        user_perms = self.perms.split(",")
        while '' in user_perms:
            user_perms.remove('')
        return user_perms
    
    def add_permissions(self, perms:str|list[str]):
        """Add permissions to the user and return a tuple containing in order: 
        - `list` of added permissions
        - `list` of not found permissions
        """
        _, found, not_found = permissions_exist(perms)

        if found:
            added_count = 0
            user_perms = self.get_perms()
            for user_perm in found:
                if user_perm not in user_perms:
                    user_perms.append(user_perm)
                    added_count += 1
            self.save_perms(user_perms) if added_count else ''

        return found, not_found

    def remove_permissions(self, perms:str|list[str]):
        """Remove permissions from the user and return a tuple containing in order: 
        - `list` of removed permissions
        - `list` of not found permissions
        """
        _, not_found, found = permissions_exist(perms)

        if found:
            user_perms = self.get_perms()
            for user_perm in found:
                if user_perm in user_perms:
                    while user_perm in user_perms:
                        user_perms.remove(user_perm)
            self.save(user_perms)

        return found, not_found