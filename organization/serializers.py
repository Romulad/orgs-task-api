from rest_framework import serializers
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.models import AnonymousUser

from .models import Organization
from user.models import AppUser as User
from app_lib.email import send_invitation_success_email
from app_lib.authorization import auth_checker
from app_lib.queryset import queryset_helpers
from app_lib.fn import get_diff_objs
from app_lib.fields import ManyPrimaryKeyRelatedField
from app_lib.read_only_serializers import (
    OrganizationDetailSerializer,
    DepartmentDeailSerializer,
    UserSerializer
)


class CreateOrganizationSerializer(OrganizationDetailSerializer):
    name = serializers.CharField(
        required=True,
        error_messages={
            "required": _("The name field is required"),
            "blank": _("Name field can't not be empty")
        }
    )
    description = serializers.CharField(
        required=False, allow_blank=True
    )
    members = ManyPrimaryKeyRelatedField(
        queryset=queryset_helpers.get_user_queryset(),
        allow_empty=True,
        required=False,
        serializer_class=UserSerializer
    )
    owner = serializers.PrimaryKeyRelatedField(
        queryset=queryset_helpers.get_user_queryset(),
        pk_field=serializers.UUIDField(),
        required=False,
    )

    def __init__(self, instance=None, data=..., **kwargs):
        super().__init__(instance, data, **kwargs)
        owner_user = self.context.get("user")
        if not isinstance(owner_user, AnonymousUser):
            self.fields['owner'].default = owner_user

    def validate_name(self, value:str):
        """
        Validate that the organization name is unique for the current user.
        Args:
            value (str): The organization name to validate.
        Raises:
            serializers.ValidationError: If the user already has an organization with the given name.
        Returns:
            str: The validated organization name.
        """
        user = self.context["user"]
        exists = self.Meta.model.objects.filter(name=value, owner=user).exists()
        if exists:
            raise serializers.ValidationError(
                _("User already has an organization with that name")
            )
        return value

    def validate_owner(self, value:User):
        """
        Validates that the specified owner user can be assigned by the current user.
        Args:
            value (User): The user instance to be set as the owner.
        Raises:
            serializers.ValidationError: If the current user does not have access to assign the specified owner.
        Returns:
            User: The validated user instance to be set as the owner.
        """
        user = self.context["user"]
        is_allowed = auth_checker.has_access_to_obj(value, user)
        if not is_allowed:
            raise serializers.ValidationError(
                _("You can't add a user you didn't create or have access to as owner")
            )
        return value
    
    def validate(self, attrs):
        user = self.context["user"]
        owner = attrs.get("owner", None)
        members = attrs.get("members", None)

        # Ensure all specified members are accessible by the owner 
        # (or the user if owner is not specified).
        if members:
            if owner:
                self.check_member_validity(members, owner)
            else:
                self.check_member_validity(members, user)

        return attrs
    
    def check_member_validity(self, members:list[User], owner:User):
        """
        Validates that the specified members can be added by the given owner.
        Checks if the `owner` has access rights to all users in the `members` list.
        If access is denied for any member, raises a `serializers.ValidationError`.
        Args:
            members (list[User]): List of user instances to be validated as members.
            owner (User): The user instance representing the owner performing the action.
        Returns:
            list[User]: The validated list of member users.
        Raises:
            serializers.ValidationError: If the owner does not have access to one or more members.
        """
        is_allowed = auth_checker.has_access_to_objs(members, owner)
        if not is_allowed:
            raise serializers.ValidationError(
                {"members": [
                    _("You or the specified owner cannot add a user you did not create or do not have access to as a member")
                    ]
                }
            )
        return members
    
    def create(self, validated_data:dict):
        user = self.context["user"]
        members = validated_data.get("members", None)

        # owner can be the user making the request or `owner` field
        # `owner` field takes precedence over the user making the request
        if validated_data.get("owner", None) is None:
            validated_data["owner"] = user

        # To know who create the user
        validated_data["created_by"] = user

        created_instance = super().create(validated_data)

        if members is not None:
            send_invitation_success_email(
                members, created_instance.name
            )

        return created_instance


class UpdateOrganizationSerializer(CreateOrganizationSerializer):
    description = serializers.CharField(
        required=True, allow_blank=True
    )
    members = ManyPrimaryKeyRelatedField(
        queryset=queryset_helpers.get_user_queryset(),
        required=True,
    )
    owner = serializers.PrimaryKeyRelatedField(
        queryset=queryset_helpers.get_user_queryset(),
        pk_field=serializers.UUIDField(),
        required=True,
    )

    def validate_name(self, value):
        # avoid check when the name has not being modified
        org_name = self.instance.name
        if org_name == value:
            return value
        return super().validate_name(value)
    
    def validate_owner(self, value:User):
        instance = self.instance
        owner_id = instance.owner.id

        if value.id == owner_id:
            return value
        
        # trying to change the owner, check user has access to the new owner
        super().validate_owner(value)

        return value

    def validate(self, attrs:dict):
        members = attrs.get('members', None)
        owner = attrs.get('owner', None)
        all_members = self.instance.members.all()
        current_owner = self.instance.owner

        # ensure new owner specified or the current owner has access to all members
        # specified in the request data or current members (all_members)
        if owner and members:
            self.check_member_validity(members, owner)
        elif owner and not members:
            self.check_member_validity(all_members, owner)
        elif not owner and members and members != all_members:
                self.check_member_validity(members, current_owner)

        return attrs

    def update(self, instance, validated_data):
        # members not part of the org yet
        new_members = []
        if (all_members := validated_data.get("members", None)):
            new_members = get_diff_objs(all_members, instance.members.all())

        updated_obj = super().update(instance, validated_data)

        send_invitation_success_email(new_members, instance.name)

        return updated_obj


class CreateDepartmentSerializer(DepartmentDeailSerializer):
    name = serializers.CharField(
        required=True,
        error_messages={
            "required": _("The name field is required"),
            "blank": _("Name field can't not be empty")
        }
    )
    description = serializers.CharField(
        required=False, allow_blank=True
    )
    members = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=queryset_helpers.get_user_queryset(),
        pk_field=serializers.UUIDField(),
        required=False,
    )
    
    def validate_name(self, value:str):
        org = self.context["org"]
        exists = self.Meta.model.objects.filter(name=value, org=org).exists()
        if exists:
            raise serializers.ValidationError(
                _("Organization already has a department with that name")
            )
        return value

    def validate_members(self, members:list[User]):
        org = self.context["org"]
        org_owner = org.owner
        is_valid = auth_checker.has_access_to_objs(members, org_owner)
        if not is_valid:
            raise serializers.ValidationError(
                _("The org owner need to have full access over members")
            )
        return members

    def create(self, validated_data:dict):
        org = self.context["org"]
        user = self.context['user']

        new_members = []
        if (depart_members := validated_data.get("members", None)):
            org_members = org.members.all()
            new_members = get_diff_objs(depart_members, org_members)
        
        validated_data["created_by"] = user
        validated_data["org"] = org
        department = super().create(validated_data)

        if new_members:
            org.members.add(*new_members)
            send_invitation_success_email(new_members, org.name)

        return department


class UpdateDepartmentSerializer(CreateDepartmentSerializer):
    name = serializers.CharField(
        required=True,
        error_messages={
            "required": _("The name field is required"),
            "blank": _("Name field can't not be empty")
        }
    )
    description = serializers.CharField(
        required=True,
    )
    org = serializers.PrimaryKeyRelatedField(
        queryset=queryset_helpers.get_org_queryset(),
        pk_field=serializers.UUIDField(),
        required=True,
    )
    members = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=queryset_helpers.get_user_queryset(),
        pk_field=serializers.UUIDField(),
        required=True,
    )

    def validate_name(self, value):
        # avoid validation when name has not being modified
        if self.instance.name == value:
            return value
        
        existed_org = self.instance.org
        self.context["org"] = existed_org
        return super().validate_name(value)

    def validate_org(self, org:Organization):
        # avoid validation when org has not being modified
        if self.instance.org.id == org.id:
            return org
        
        # want to change org for the depart, check if he has access to the new org
        user = self.context["user"]
        is_allowed = auth_checker.has_access_to_obj(org, user)
        if not is_allowed:
            raise serializers.ValidationError(
                _("You don't have access to the new org")
            )
        return org
    
    def validate_members(self, members):
        existed_org = self.instance.org
        self.context["org"] = existed_org
        return super().validate_members(members)

    def validate(self, attrs:dict):
        members_error = serializers.ValidationError({
            "members": [_("The org owner need to have a full access over department members")]
        })
        instance = self.instance
        org = attrs.get('org', None)
        members = attrs.get('members', None)

        # ensure the org owner has access to the members 
        # either current instance org or specified org in the request data
        if org and org.id == instance.org.id:
            return attrs
        elif org and not members:
            if not auth_checker.has_access_to_objs(
                instance.members.all(), org.owner
            ):
                raise members_error
        elif org and members:
            if not auth_checker.has_access_to_objs(
                members, org.owner
            ):
                raise members_error
        elif not org and members:
            if not auth_checker.has_access_to_objs(
                members, instance.org.owner
            ):
                raise members_error
            
        return attrs

    def update(self, instance, validated_data):
        """
        Updates an organization instance with validated data, 
        handling member additions and sending invitation emails.
        Args:
            instance: The current organization instance to update.
            validated_data (dict): The validated data containing fields to update, possibly including 'members' and 'org'.
        Returns:
            The updated organization instance.
        **Notes**:
            - If 'org' is provided in validated_data, 
            members(either on the instance or specified in request data) are added to that organization.
        """
        new_member =[]
        members = validated_data.get("members", None)
        org = validated_data.get("org", None)

        if org:
            if members:
                new_member = org.add_no_exiting_members(members)
            else:
                new_member = org.add_no_exiting_members(instance.members.all())
        else:
            if members:
                new_member = instance.org.add_no_exiting_members(members)

        updated_data = super().update(instance, validated_data)

        if new_member:
            send_invitation_success_email(
                new_member, org.name if org else instance.org.name
            )
        
        return updated_data