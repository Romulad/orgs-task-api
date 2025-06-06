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
from app_lib.fields import ManyPrimaryKeyRelatedField, DefaultDateTimeField

# TODO: nested db fectch for create and update view

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
            'created_at': {'read_only': True},
        }


class TaskDetailSerializer(TaskSerializer):
    assigned_to = UserSerializer(many=True, read_only=True)
    tags = TagSerializer(many=True, read_only=True)
    depart = DepartmentSerializer(read_only=True)
    org = OrganizationSerializer(read_only=True)
    can_be_accessed_by = UserSerializer(many=True, read_only=True)

    class Meta(TaskSerializer.Meta):
        fields = [
            *TaskSerializer.Meta.fields,
            "assigned_to",
            "tags",
            "depart",
            "org",
            "can_be_accessed_by",
        ]


class CreateUpdateTaskBaseSerializer(TaskDetailSerializer):

    def check_task_name_already_exists_in_org(self, name, org_id):
        return Task.objects.filter(name=name, org__id=org_id).exists()
    
    def check_org_owner_has_access_to_assigned_to(self, assigned_to, org):
        return auth_checker.has_access_to_objs(assigned_to, org.owner)

    def check_tags_belong_to_org(self, tags, org):
        for tag in tags:
            if tag.org.id != org.id:
                return False
        return True

    def check_depart_belongs_to_org(self, depart, org):
        if depart and depart.org.id != org.id:
            return False
        return True

    def check_task_name_uniqueness(self, name, org_id):
        if self.check_task_name_already_exists_in_org(name, org_id):
            raise serializers.ValidationError(
                _("A task with this name already exists in the organization.")
            )

    def validate_tags_user_depart_against_org(self, attrs):
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
    
    def check_and_update_org_members(self, assigned_to, org):
        if assigned_to:
            new_user = get_diff_objs(assigned_to, org.members.all())
            org.members.add(*new_user)


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
    assigned_to = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=queryset_helpers.get_user_queryset(),
        required=False,
        allow_null=True,
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
        self.check_task_name_uniqueness(value, org_id)
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
        if self.instance.name == value:
            return value
        
        org_id = self.initial_data.get('org')
        if org_id:
            self.check_task_name_uniqueness(value, org_id)
        else:
            self.check_task_name_uniqueness(value, self.instance.org.id)

        return value

    def validate_org(self, org):
        if self.instance.org.id == org.id:
            return org
        
        super().validate_org(org)

        # validation against existing instance assigned_to, depart, tags, name.
        # only apply validation on existing instance attrs when the given field 
        # is not specified in the request data otherwise let the validation to the
        # field validation step
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