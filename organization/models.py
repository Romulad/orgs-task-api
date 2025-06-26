from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _

from app_lib.models import AbstractBaseModel
from app_lib.fn import get_diff_objs

class Organization(AbstractBaseModel):
  name = models.CharField(
    _('organization name'), max_length=100
  )
  description = models.TextField(
    _("organization description"), default=""
  )
  owner = models.ForeignKey(
    settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, 
    verbose_name=_('organization owner'), related_name="org_owner",
    null=True
  )
  members = models.ManyToManyField(
    settings.AUTH_USER_MODEL, verbose_name=_('organization members')
  )
  created_by = models.ForeignKey(
    settings.AUTH_USER_MODEL,
    on_delete=models.CASCADE,
    null=True,
    related_name="user_orgs",
  )

  class Meta:
    verbose_name = _('Organization')
    verbose_name_plural = _('Organizations')
    unique_together = ["name", "owner"]
    indexes = [
      models.Index(fields=['name'])
    ]

  def __str__(self):
    return f"{self.owner.email}_{self.name}"
  
  def add_no_exiting_members(self, users):
    """ Adds users to the organization if they are not already members.
    This method compares the provided `users` list with the current
    members of the organization. Only users who are not already members will be added.

    Args:
      users (Iterable[User]): An iterable of user instances to be added to the organization.
    """
    new_users = get_diff_objs(users, self.members.all())
    if new_users:
      self.members.add(*new_users)
  

class Department(AbstractBaseModel):
  name = models.CharField(
    _('Department name'), max_length=100
  )
  description = models.TextField(
    _("Department description"), default=""
  )
  org = models.ForeignKey(
    Organization, on_delete=models.CASCADE, 
    verbose_name=_('organization'), related_name="depart_own"
  )
  members = models.ManyToManyField(
    settings.AUTH_USER_MODEL, verbose_name=_('Department members')
  )

  class Meta:
    verbose_name = _('Department')
    verbose_name_plural = _('Departments')
    unique_together = ("name", "org")
    indexes = [
      models.Index(fields=['name'])
    ]

  def __str__(self):
    return f"{self.name}"