from app_lib.models import AbstractBaseModel
from django.db import models
from django.utils.translation import gettext_lazy as _

from organization.models import Organization

class Tag(AbstractBaseModel):
    name = models.CharField(
        max_length=300,
        help_text=_("Name of the tag"),
        verbose_name=_("Tag Name")
    )
    description = models.TextField(
        blank=True,
        null=True,
        help_text=_("Description of the tag"),
        verbose_name=_("Tag Description")
    )
    org = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name='tags',
        verbose_name=_("Organization"),
        help_text=_("Organization to which this tag belongs to")
    )

    class Meta:
        unique_together = ('name', 'org')
        indexes = [
            models.Index(fields=['name'])
        ]

    def __str__(self):
        return self.name