import uuid

from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.db.models.manager import Manager


class DefaultManager(Manager):
    
    def get_queryset(self):
        return super().get_queryset().filter(is_deleted=False)


class AbstractBaseModel(models.Model):
    """
    Abstract base model that provides common fields and methods.
    """
    id = models.UUIDField(
        primary_key=True, editable=False, default=uuid.uuid4
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="%(app_label)s_%(class)s_created_by",
        blank=True,
    )
    can_be_accessed_by = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name="%(app_label)s_%(class)s_can_be_accessed_by",
        blank=True,
    )
    is_deleted = models.BooleanField(
        _("deleted"),
        default=False,
        help_text=_(
            "Indicate a deleted ressource."
            "Select this instead of deleting ressource."
        ),
    )
    created_at = models.DateTimeField(
        auto_now_add=True, verbose_name=_('created at'), db_index=True
    )
    updated_at = models.DateTimeField(
        auto_now=True, verbose_name=_('modified at')
    )
    deleted_at = models.DateTimeField(
        null=True, blank=True
    )

    objects = DefaultManager()
    all_objects = Manager()

    class Meta:
        abstract = True