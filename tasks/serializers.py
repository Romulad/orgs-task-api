from rest_framework import serializers
from django.utils.translation import gettext_lazy as _

from .models import Task
from user.serializers import UserSerializer
from organization.serializers import OrganizationSerializer, DepartmentSerializer
from organization.models import Organization
from app_lib.queryset import queryset_helpers
from app_lib.authorization import auth_checker
from tags.serializers import TagSerializer
from app_lib.fn import get_diff_objs


class TaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = Task
        fields = [
            "id",
            "name",
            "description",
            "due_date",
            "priority",
            "status",
            'estimated_duration',
            "actual_duration",
            "allow_auto_status_update",
            "created_at",
        ]
        extra_kwargs = {
            'id': {'read_only': True},
            'name': {'read_only': True},
            'description': {'read_only': True},
            'due_date': {'read_only': True},
            'priority': {'read_only': True},
            'status': {'read_only': True},
            'estimated_duration': {'read_only': True},
            'actual_duration': {'read_only': True},
            'allow_auto_status_update': {'read_only': True},
            'created_at': {'read_only': True},
        }


class TaskDetailSerializer(TaskSerializer):
    assigned_to = UserSerializer(many=True, read_only=True)
    parent_task = TaskSerializer(read_only=True)
    tags = TagSerializer(many=True, read_only=True)
    depart = DepartmentSerializer(read_only=True)
    org = OrganizationSerializer(read_only=True)
    can_be_accessed_by = UserSerializer(many=True, read_only=True)

    class Meta(TaskSerializer.Meta):
        fields = [
            *TaskSerializer.Meta.fields,
            "assigned_to",
            "parent_task",
            "tags",
            "depart",
            "org",
            "can_be_accessed_by",
        ]


class CreateTaskSerializer(TaskDetailSerializer):
    name = serializers.CharField(
        required=True,
        help_text=_("Name of the task"),
        error_messages={
            'required': _("This field is required."),
            'blank': _("This field cannot be blank."),
        }
    )
    description = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text=_("Detailed description of the task"),
    )
    assigned_to = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=queryset_helpers.get_user_queryset(),
        required=False,
        allow_null=True,
        help_text=_("Users assigned to this task"),
        error_messages={
            'does_not_exist': _("One or more specified users do not exist."),
        }
    )
    due_date = serializers.DateTimeField(
        required=False,
        allow_null=True,
        help_text=_("Deadline for the task"),
        error_messages={
            'invalid': _("Enter a valid date/time."),
        }
    )
    priority = serializers.ChoiceField(
        choices=Task.Priority,
        default=Task.Priority.MEDIUM,
        help_text=_("Priority level of the task"),
        error_messages={
            'invalid_choice': _("Invalid priority choice."),
        }
    )
    status = serializers.ChoiceField(
        choices=Task.Status,
        default=Task.Status.PENDING,
        help_text=_("Current status of the task"),
        error_messages={
            'invalid_choice': _("Invalid status choice."),
        }
    )
    estimated_duration = serializers.DurationField(
        required=False,
        allow_null=True,
        help_text=_("Estimated time to complete the task"),
        error_messages={
            'invalid': _("Enter a valid duration."),
        }
    )
    actual_duration = serializers.DurationField(
        required=False,
        allow_null=True,
        help_text=_("Actual time spent on the task"),
        error_messages={
            'invalid': _("Enter a valid duration."),
        }
    )
    allow_auto_status_update = serializers.BooleanField(
        default=True,
        required=False,
        help_text=_("Allow automatic status updates based on sub-task progress"),
        error_messages={
            'invalid': _("Enter a valid boolean value."),
        }
    )
    tags = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=queryset_helpers.get_tag_queryset(only_select_related=True),
        required=False,
        allow_null=True,
        help_text=_("Tags associated with the task"),
        error_messages={
            'does_not_exist': _("One or more specified tags do not exist."),
        }
    )
    parent_task = serializers.PrimaryKeyRelatedField(
        queryset=queryset_helpers.get_task_queryset(only_select_related=True),
        required=False,
        allow_null=True,
        help_text=_("Parent task if this is a sub-task"),
        error_messages={
            'does_not_exist': _("The specified parent task does not exist."),
        }
    )
    depart = serializers.PrimaryKeyRelatedField(
        queryset=queryset_helpers.get_depart_queryset(only_select_related=True),
        required=False,
        allow_null=True,
        help_text=_("Department to which the task belongs"),
        error_messages={
            'does_not_exist': _("The specified department does not exist."),
        }
    )
    org = serializers.PrimaryKeyRelatedField(
        queryset=queryset_helpers.get_org_queryset(),
        required=True,
        help_text=_("Organization to which the task belongs"),
        error_messages={
            'required': _("This field is required."),
            'does_not_exist': _("The specified organization does not exist."),
        }
    )

    def validate_name(self, value):
        """
        Validate that the task name is unique within the organization.
        """
        org_id = self.initial_data.get('org')
        if not org_id:
            raise serializers.ValidationError(
                {"org": [_("This field is required.")]}
            )
        # if org_id is not valid org id, the `org` field on the serializer will raise an error
        if Task.objects.filter(name=value, org__id=org_id).exists():
            raise serializers.ValidationError(
                _("A task with this name already exists in the organization.")
            )
        return value
    
    def validate_org(self, org:Organization):
        """
        Validate that the user has full access to the organization.
        """
        user = self.context['request'].user
        if not auth_checker.has_access_to_obj(org, user):
            raise serializers.ValidationError(
                _("You do not have permission to create tasks in this organization.")
            )
        return org

    def validate(self, attrs:dict):
        org = attrs.get('org')

        # validate assigned_to users
        assigned_to = attrs.get('assigned_to', [])
        if assigned_to:
            if not auth_checker.has_access_to_objs(assigned_to, org.owner):
                raise serializers.ValidationError(
                    {"assigned_to": [_("The organization owner must have full access to the assigned users.")]}
                )
        
        # validate parent_task org is same as the new task org
        parent_task = attrs.get('parent_task', None)
        if parent_task:
            if parent_task.org.id != org.id:
                raise serializers.ValidationError(
                    {"parent_task": [_("The parent task must belong to the same organization as the new task.")]}
                )
            # validate parent_task depart if exists
            if parent_task.depart and parent_task.depart.org.id != org.id:
                raise serializers.ValidationError(
                    {"parent_task": [_("The parent task's department must belong to the same organization as the new task.")]}
                )
        
        # validate tags if specified
        tags = attrs.get('tags', [])
        for tag in tags:
            if tag.org.id != org.id:
                raise serializers.ValidationError(
                    {"tags": [_("All tags must belong to the same organization as the new task.")]}
                )
        
        # validate depart if specified
        depart = attrs.get('depart', None)
        if depart and depart.org.id != org.id:
            raise serializers.ValidationError(
                {"depart": [_("The department must belong to the same organization as the new task.")]}
            )

        return attrs
    
    def create(self, validated_data):
        org = validated_data['org']
        assigned_to = validated_data.get('assigned_to', [])
        parent_task = validated_data.get('parent_task', None)
        user = self.context['request'].user

        validated_data['created_by'] = user
        task = super().create(validated_data)

        # ensure parent_task status is updated if needed
        if parent_task and parent_task.allow_auto_status_update:
            task_status = validated_data.get('status')
            if (
                task_status in [Task.Status.IN_PROGRESS, Task.Status.PENDING] and 
                parent_task.status in [Task.Status.CANCELLED, Task.Status.COMPLETED]
            ):
                parent_task.status = Task.Status.IN_PROGRESS
                parent_task.save()
            elif (
                task_status in [Task.Status.COMPLETED, Task.Status.CANCELLED] and
                parent_task.status in [Task.Status.IN_PROGRESS, Task.Status.PENDING]
            ):
                no_completed_count = Task.objects.filter(
                    parent_task=parent_task, 
                    status__in=[Task.Status.IN_PROGRESS, Task.Status.PENDING]
                ).count()
                if not no_completed_count:
                    parent_task.status = Task.Status.COMPLETED
                    parent_task.save()
        
        # Ensure the user in assigned_to is added to the organization if not already a member
        if assigned_to:
            new_user = get_diff_objs(assigned_to, org.members.all())
            org.members.add(*new_user)
        
        return task
        