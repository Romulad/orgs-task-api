from rest_framework import serializers
from django.utils.translation import gettext_lazy as _

from .models import Task
from organization.models import Organization
from app_lib.queryset import queryset_helpers
from app_lib.authorization import auth_checker
from app_lib.fields import (
    ManyPrimaryKeyRelatedField, 
    DefaultDateTimeField
)
from app_lib.app_permssions import CAN_CREATE_TASK
from app_lib.read_only_serializers import (
    TaskDetailSerializer,
    TaskSerializer
)


class CreateUpdateTaskBaseSerializer(TaskDetailSerializer):

    def check_task_name_already_exists_in_org(self, name, org_id):
        """
        Checks if a task with the given name already exists within the specified organization.
        Args:
            name (str): The name of the task to check for existence.
            org_id (uuid): The ID of the organization to search within.
        Returns:
            bool: True if a task with the specified name exists in the organization, False otherwise.
        """
        return Task.objects.filter(name=name, org__id=org_id).exists()
    
    def check_org_owner_has_access_to_assigned_to(self, assigned_to, org):
        """
        Checks whether the owner of the given organization has access to the specified 'assigned_to' users.
        Args:
            assigned_to (list[User]): The list of users to check access for.
            org: The organization whose owner's access is being verified.
        Returns:
            bool: True if the organization owner has access to all users, False otherwise.
        """
        return auth_checker.has_access_to_objs(assigned_to, org.owner)

    def check_tags_belong_to_org(self, tags, org: Organization):
        """
        Checks whether all tags in the provided list belong to the specified organization.
        Args:
            tags (Iterable[Tag]): A collection of Tag objects to check.
            org (Organization): The organization to verify tag ownership against.
        Returns:
            bool: True if all tags belong to the given organization, False otherwise.
        """
        for tag in tags:
            if tag.org.id != org.id:
                return False
        return True

    def check_depart_belongs_to_org(self, depart, org:Organization):
        """
        Checks whether the given department belongs to the specified organization.
        Args:
            depart: The department instance to check.
            org (Organization): The organization instance to compare against.
        Returns:
            bool: True if the department belongs to the organization or if depart is None, False otherwise.
        """
        if depart and depart.org.id != org.id:
            return False
        return True

    def check_task_name_uniqueness(self, name, org_id):
        """
        Checks whether a task name is unique within a given organization.
        Args:
            name (str): The name of the task to check.
            org_id (uuid): The ID of the organization to check within.
        Raises:
            serializers.ValidationError: If a task with the given name already exists in the organization.
        """
        if self.check_task_name_already_exists_in_org(name, org_id):
            raise serializers.ValidationError(
                _("A task with this name already exists in the organization.")
            )

    def validate_tags_user_depart_against_org(self, attrs):
        """ Validate that the `tags`, `assigned_to` users, and `depart` belong to 
        the same organization as the task. If the `org` field is not specified,
        it will use the organization of the existing task instance if available.
        """
        org = attrs.get('org')

        # validate assigned_to users
        assigned_to = attrs.get('assigned_to', [])
        if assigned_to:
            error_obj = serializers.ValidationError(
                {"assigned_to": [_("The organization owner must have full access to the assigned users.")]}
            )
            if org and not self.check_org_owner_has_access_to_assigned_to(assigned_to, org):
                raise error_obj
            elif not org and self.partial and not self.check_org_owner_has_access_to_assigned_to(
                assigned_to, self.instance.org
            ):
                raise error_obj
            
        # validate tags if specified
        tags = attrs.get('tags', [])
        if tags:
            error_obj =  serializers.ValidationError(
                {"tags": [_("All tags must belong to the same organization as the task.")]}
            )
            if org and not self.check_tags_belong_to_org(tags, org):
                raise error_obj
            elif not org and self.partial and not self.check_tags_belong_to_org(
                tags, self.instance.org
            ):
                raise error_obj
        
        # validate depart if specified
        depart = attrs.get('depart', None)
        if depart:
            error_obj =  serializers.ValidationError(
                {"depart": [_("The department must belong to the same organization as the task.")]}
            )
            if org and not self.check_depart_belongs_to_org(depart, org):
                raise error_obj
            elif not org and self.partial and not self.check_depart_belongs_to_org(
                depart, self.instance.org
            ):
                raise error_obj
    
    def check_and_update_org_members(self, assigned_to, org:Organization):
        """ Checks if the users in `assigned_to` are already members of the given `org` (Organization).
        If not, adds them as new members to the organization.
        Args:
            assigned_to (Iterable[User]): A collection of user instances to be checked and potentially added to the organization.
            org (Organization): The organization to which users may be added.
        """
        org.add_no_exiting_members(assigned_to)


class CreateTaskSerializer(CreateUpdateTaskBaseSerializer):
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
    assigned_to = ManyPrimaryKeyRelatedField(
        queryset=queryset_helpers.get_user_queryset(),
        required=False,
        allow_empty=True,
        help_text=_("Users assigned to this task"),
    )
    due_date = serializers.DateTimeField(
        required=False,
        allow_null=True,
        help_text=_("Deadline for the task"),
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
    tags = ManyPrimaryKeyRelatedField(
        queryset=queryset_helpers.get_tag_queryset(
            only_select_related=True
        ),
        required=False,
        allow_empty=True,
        help_text=_("Tags associated with the task"),
        error_messages={
            'does_not_exist': _("One or more specified tags do not exist."),
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
        # if org_id is not a valid org id, the `org` field on the serializer will raise an error
        self.check_task_name_uniqueness(value, org_id)
        return value
    
    def validate_org(self, org:Organization):
        """
        Validate whether the user has full access to the organization.
        Also user with `CAN_CREATE_TASK` permission can only create task.
        """
        user = self.context['request'].user
        error_obj = serializers.ValidationError(
            _("You do not have permission to create tasks in this organization.")
        )
        
        # this is mandatory check when a user specified a new org, must have access to it
        if auth_checker.has_access_to_obj(org, user):
            return org
        
        # Only apply this check when the user is creating a new task
        # and does not have access to the organization
        # but has permission to create tasks in the organization
        if (
            not self.instance and 
            auth_checker.has_permission(user, org, CAN_CREATE_TASK)
        ):
            return org
        
        raise error_obj

    def validate(self, attrs:dict):
        self.validate_tags_user_depart_against_org(attrs)
        return attrs
    
    def create(self, validated_data):
        org = validated_data['org']
        user = self.context['request'].user
        assigned_to = validated_data.get('assigned_to', [])

        validated_data['created_by'] = user
        task = super().create(validated_data)
        
        # Ensure the user in assigned_to is added to the organization if not already a member
        self.check_and_update_org_members(assigned_to, org)
        
        return task


class UpdateTaskSeriliazer(CreateTaskSerializer):
    description = serializers.CharField(
        required=True,
        allow_blank=True,
        help_text=_("Detailed description of the task"),
    )
    assigned_to = ManyPrimaryKeyRelatedField(
        required=True,
        queryset=queryset_helpers.get_user_queryset(),
        allow_empty=True,
        help_text=_("Users assigned to this task"),
    )
    due_date = DefaultDateTimeField(
        required=True,
        allow_blank=True,
        help_text=_("Deadline for the task"),
    )
    priority = serializers.ChoiceField(
        choices=Task.Priority,
        required=True,
        help_text=_("Priority level of the task"),
        error_messages={
            'invalid_choice': _("Invalid priority choice."),
        }
    )
    status = serializers.ChoiceField(
        choices=Task.Status,
        required=True,
        help_text=_("Current status of the task"),
        error_messages={
            'invalid_choice': _("Invalid status choice."),
        }
    )
    estimated_duration = serializers.DurationField(
        required=True,
        allow_null=True,
        help_text=_("Estimated time to complete the task"),
        error_messages={
            'invalid': _("Enter a valid duration."),
        }
    )
    actual_duration = serializers.DurationField(
        required=True,
        allow_null=True,
        help_text=_("Actual time spent on the task"),
        error_messages={
            'invalid': _("Enter a valid duration."),
        }
    )
    tags = ManyPrimaryKeyRelatedField(
        queryset=queryset_helpers.get_tag_queryset(only_select_related=True),
        required=True,
        allow_empty=True,
        help_text=_("Tags associated with the task"),
    )
    depart = serializers.PrimaryKeyRelatedField(
        queryset=queryset_helpers.get_depart_queryset(only_select_related=True),
        required=True,
        allow_null=True,
        help_text=_("Department to which the task belongs"),
        error_messages={
            'does_not_exist': _("The specified department does not exist."),
        }
    )
    
    def validate_name(self, value):
        """
        Validates the 'name' field for uniqueness within the specified organization.
        If the provided name is unchanged from the current instance, it is accepted.
        Otherwise, checks if the name is unique within the organization, using the 'org'
        field from the initial data if available, or the organization of the current instance.
        """
        if self.instance.name == value:
            return value
        
        org_id = self.initial_data.get('org')
        if org_id:
            self.check_task_name_uniqueness(value, org_id)
        else:
            self.check_task_name_uniqueness(value, self.instance.org.id)

        return value

    def validate_org(self, org):
        """
        Validates the organization (`org`) associated with the serializer instance.
        """
        if self.instance.org.id == org.id:
            return org
        
        super().validate_org(org)

        # validation against existing instance assigned_to, depart, tags, name.
        # only apply validation on existing instance attrs when the given field 
        # is not specified in the request data otherwise let the validation to the
        # field validation step.
        # This ensures that if a validation required field is omitted, 
        # its existing value is still valid in the new org context.

        messages = []
        instance = self.instance

        if not self.initial_data.get("name", None):
            if self.check_task_name_already_exists_in_org(
                instance.name, org.id
            ):
                messages.append(_("A task with the same name already exist in the organization"))
        
        if not self.initial_data.get("assigned_to", None):
            if not self.check_org_owner_has_access_to_assigned_to(
                instance.assigned_to.all(), org
            ):
                messages.append(
                    _('The organization owner should have a full access over user assigned to the task')
                )

        if not self.initial_data.get("tags", None):
            if not self.check_tags_belong_to_org(instance.tags.all(), org):
                messages.append(
                    _('All tags should belong to the organization')
                )
        
        if not self.initial_data.get("depart", None):
            if not self.check_depart_belongs_to_org(instance.depart, org):
                messages.append(
                    _('The department should belongs to the organization')
                )
        
        if messages:
            raise serializers.ValidationError(messages)
        
        return org
    
    def validate(self, attrs):
        return super().validate(attrs)
    
    def update(self, instance, validated_data):
        assigned_to = validated_data.get('assigned_to', [])
        updated = super().update(instance, validated_data)

        org = validated_data.get("org")
        if org:
            self.check_and_update_org_members(assigned_to, org)
        else:
            self.check_and_update_org_members(assigned_to, instance.org)
            
        return updated


class UpdateTaskStatusSerializer(TaskSerializer):
    """
    Use to allow `assigned_to` user to be able to update task status
    """
    status = serializers.ChoiceField(
        choices=Task.Status,
        required=True,
        allow_blank=False,
        help_text=_("Current status of the task"),
        error_messages={
            'invalid_choice': _("Invalid status choice."),
        }
    )