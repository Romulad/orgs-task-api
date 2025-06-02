from app_lib.models import AbstractBaseModel
from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _

from organization.models import Organization, Department
from tags.models import Tag

User = settings.AUTH_USER_MODEL

class Task(AbstractBaseModel):
    class Priority(models.TextChoices):
        LOW = "low", _("Low")
        MEDIUM = "medium", _("Medium")
        HIGH = "high", _("High")
        CRITICAL = "critical", _("Critical")

    class Status(models.TextChoices):
        PENDING = "pending", _("Pending")
        IN_PROGRESS = "in_progress", _("In Progress")
        COMPLETED = "completed", _("Completed")
        CANCELLED = "cancelled", _("Cancelled")

    name = models.CharField(
        max_length=255, 
        help_text=_("Name of the task"), 
        verbose_name=_("Task Name")
    )
    description = models.TextField(
        blank=True, 
        null=True, 
        help_text=_("Detailed description of the task"), 
        verbose_name=_("Task Description")
    )
    assigned_to = models.ManyToManyField(
        User,
        blank=True,
        related_name="tasks_assigned",
        help_text=_("Users assigned to this task"),
        verbose_name=_("Assigned To")
    )
    due_date = models.DateTimeField(
        blank=True, 
        null=True, 
        help_text=_("Deadline for the task"), 
        verbose_name=_("Due Date")
    )
    priority = models.CharField(
        max_length=50,
        choices=Priority,
        default=Priority.MEDIUM,
        help_text=_("Priority level of the task"), 
        verbose_name=_("Priority")
    )
    status = models.CharField(
        max_length=50,
        choices=Status,
        default=Status.PENDING,
        help_text=_("Current status of the task"), 
        verbose_name=_("Status")
    )
    estimated_duration = models.DurationField(
        blank=True, 
        null=True, 
        help_text=_("Estimated time to complete the task"), 
        verbose_name=_("Estimated Time")
    )
    actual_duration = models.DurationField(
        blank=True, 
        null=True, 
        help_text=_("Actual time spent on the task"), 
        verbose_name=_("Actual Time")
    )
    tags = models.ManyToManyField(
        Tag,
        blank=True, 
        related_name="tasks", 
        help_text=_("Tags associated with the task"), 
        verbose_name=_("Tags")
    )
    org = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="tasks",
        help_text=_("Organization this task belongs to"),
        verbose_name=_("Organization")
    )
    depart = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tasks",
        help_text=_("Department this task belongs to"),
        verbose_name=_("Department")
    )
    
    class Meta:
        unique_together = ('name', 'org')

    def __str__(self):
        return self.name


