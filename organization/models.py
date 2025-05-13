import uuid

from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _

from app_lib.models import AbstractBaseModel

class Organization(AbstractBaseModel):
  name = models.CharField(
    _('organization name'), max_length=100
  )
  description = models.TextField(
    _("organization description"), default=""
  )
  owner = models.ForeignKey(
    settings.AUTH_USER_MODEL, on_delete=models.CASCADE, 
    verbose_name=_('organization owner'), related_name="org_owner"
  )
  members = models.ManyToManyField(
    settings.AUTH_USER_MODEL, verbose_name=_('organization members')
  )

  class Meta:
    verbose_name = _('Organization')
    verbose_name_plural = _('Organizations')
    unique_together = ["name", "owner"]

  def __str__(self):
    return f"{self.owner.email}_{self.name}"
  

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
    unique_together = ["name", "org"]

  def __str__(self):
    return f"{self.name}"