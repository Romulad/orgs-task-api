from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from app_lib.models import AbstractBasePermissionModel
from organization.models import Organization

User =  settings.AUTH_USER_MODEL

class UserPermissions(AbstractBasePermissionModel):
    '''User permissions in an organization'''
    user = models.ForeignKey(
        User, on_delete=models.CASCADE,
        verbose_name=_("User")
    )
    org = models.ForeignKey(
        Organization, on_delete=models.CASCADE,
        verbose_name=_("Organization")
    )

    class Meta:
        verbose_name = _("User permission")
        verbose_name_plural = _("User permissions")
        unique_together = ("user", "org")

    def __str__(self):
        return super().__str__()


class Role(AbstractBasePermissionModel):
    name = models.CharField(
        _("Name of the role"),
        max_length=255
    )
    description = models.TextField(
        _("Role description"),
    )
    org = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        verbose_name=_("Organization")
    )
    users = models.ManyToManyField(
        User,
        verbose_name=_("Set of users that have the role")
    )

    class Meta:
        verbose_name = _("Role")
        verbose_name_plural = _("Roles")
        unique_together = ("name", 'org')
        indexes = [
            models.Index(fields=['name'])
        ]