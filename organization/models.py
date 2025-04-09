import uuid

from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _


class Organization(models.Model):
  id = models.UUIDField(
    primary_key=True, default=uuid.uuid4, 
    editable=False
  )
  name = models.CharField(
    _('organization name'), max_length=100
  )
  owner = models.OneToOneField(
    settings.AUTH_USER_MODEL, on_delete=models.CASCADE, 
    verbose_name=_('organization owner'), related_name="org_owner"
  )
  members = models.ManyToManyField(
    settings.AUTH_USER_MODEL, verbose_name=_('orgnization members')
  )
  created_at = models.DateTimeField(
    auto_now_add=True, verbose_name=_('created at')
  )
  last_modified = models.DateTimeField(
    auto_now=True, verbose_name=_('modified at')
  )

  class Meta:
    verbose_name = _('Organization')
    verbose_name_plural = _('Organizations')
    unique_together = ["name", "owner"]

  def __str__(self):
    return f"{self.owner.email}_{self.name}"