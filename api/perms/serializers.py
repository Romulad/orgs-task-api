from rest_framework import serializers
from django.utils.translation import gettext_lazy as _

from app_lib.queryset import queryset_helpers
from app_lib.fields import ManyPrimaryKeyRelatedField
from app_lib.authorization import auth_checker
from .models import Role
from app_lib.app_permssions import permissions_exist
from app_lib.read_only_serializers import RoleDetailSerializer
from app_lib.common_error_messages import (
    ORG_ACCESS_ISSUE_MESSAGE, 
    CREATOR_LEVEL_PERM_ISSUE_MESSAGE,
    OWNER_ACCESS_OVER_USERS_ISSUE_MESSAGE
)


class AddPermissionsSerializer(serializers.Serializer):
    org = serializers.PrimaryKeyRelatedField(
        required=True,
        queryset=queryset_helpers.get_org_queryset(),
        write_only=True
    )
    user_ids = ManyPrimaryKeyRelatedField(
        allow_empty=False,
        required=True,
        queryset=queryset_helpers.get_user_queryset(),
        write_only=True
    )
    perms = serializers.ListField(
        child=serializers.CharField(),
        required=True,
        allow_empty=False,
        write_only=True
    )

    def validate_org(self, org):
        user = self.context['request'].user
        if not auth_checker.has_access_to_obj(org, user):
            raise serializers.ValidationError(
               ORG_ACCESS_ISSUE_MESSAGE
            )
        return org

    def validate(self, attrs):
        user = self.context['request'].user
        users = attrs["user_ids"]
        org = attrs["org"]
        perms = attrs["perms"]

        if not auth_checker.has_access_to_objs(
            users, org.owner
        ):
            raise serializers.ValidationError({
                "user_ids": [OWNER_ACCESS_OVER_USERS_ISSUE_MESSAGE]
            })
        
        if perms and not auth_checker.can_add_creator_level_perms(
            perms, org, user
        ):
            raise serializers.ValidationError({
                "perms": [CREATOR_LEVEL_PERM_ISSUE_MESSAGE]
            })

        return attrs

    def create(self, validated_data):
        users = validated_data["user_ids"]
        org = validated_data["org"]
        perms = validated_data["perms"]
        perms_tuple = auth_checker.add_permissions_to_users(users, org, perms)
        org.add_no_exiting_members(users)
        return perms_tuple


class RemovePermissionsSerializer(AddPermissionsSerializer):

    def validate(self, attrs):
        return attrs
    
    def create(self, validated_data):
        users = validated_data["user_ids"]
        org = validated_data["org"]
        perms = validated_data["perms"]
        perms_tuple = auth_checker.remove_permissions_from_users(users, org, perms)
        return perms_tuple


class CreateRoleSerializer(RoleDetailSerializer):
    name = serializers.CharField(
        required=True,
        max_length=255,
        allow_blank=False,
    )
    description = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
    )
    perms = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        allow_empty=True,
    )
    org = serializers.PrimaryKeyRelatedField(
        required=True,
        queryset=queryset_helpers.get_org_queryset()
    )
    users = ManyPrimaryKeyRelatedField(
        queryset=queryset_helpers.get_user_queryset(),
        required=False,
        allow_empty=True,
    )

    def validate_org(self, org):
        user = self.context['request'].user
        if not auth_checker.has_access_to_obj(org, user):
            raise serializers.ValidationError(
                ORG_ACCESS_ISSUE_MESSAGE
            )
        return org
    
    def assert_name_uniqueness(self, name, org_id):
        if Role.objects.filter(
            name=name, org__id=org_id
        ).exists():           
            raise serializers.ValidationError( 
                _("Role with this name already exists in the organization.")
            )
    
    def validate_name(self, name):
        org_id = self.initial_data.get("org", "")
        self.assert_name_uniqueness(name, org_id)
        return name
    
    def validate_perms(self, perms):
        _, found, _ = permissions_exist(perms)
        return found
    
    def validate(self, attrs):
        user = self.context['request'].user
        org = attrs.get("org")
        perms = attrs.get("perms")

        users = attrs.get("users", None)
        if users:
            if not auth_checker.has_access_to_objs(users, org.owner):
                raise serializers.ValidationError({"users": [
                    OWNER_ACCESS_OVER_USERS_ISSUE_MESSAGE
                ]})
        
        if perms and not auth_checker.can_add_creator_level_perms(
            perms, org, user
        ):
            raise serializers.ValidationError({
                "perms": [CREATOR_LEVEL_PERM_ISSUE_MESSAGE]
            })

        return attrs
    
    def create(self, validated_data):
        user = self.context['request'].user
        validated_data["created_by"] = user

        perms = validated_data.get("perms", [])
        validated_data["perms"] = Role.dump_perms(perms)

        org = validated_data["org"]
        users = validated_data.get("users", None)

        created_role = super().create(validated_data)

        if users is not None:
            org.add_no_exiting_members(users)

        return created_role


class UpdateRoleSerializer(CreateRoleSerializer):
    description = serializers.CharField(
        required=True,
        allow_blank=True,
    )
    perms = serializers.ListField(
        child=serializers.CharField(),
        required=True,
        allow_empty=True,
    )
    users = ManyPrimaryKeyRelatedField(
        queryset=queryset_helpers.get_user_queryset(),
        required=True,
        allow_empty=True,
    )

    def validate_name(self, name):
        if self.instance.name == name:
            return name
        
        if self.initial_data.get("org"):
            return super().validate_name(name)
        
        self.assert_name_uniqueness(name, self.instance.org.id)

        return name

    def validate_org(self, org):
        if self.instance.org.id == org.id:
            return org
        
        # validate user permission over org
        super().validate_org(org)

        # ensure the new org does not have a role with the same name already
        if self.initial_data.get("name", None) is None:
            self.assert_name_uniqueness(self.instance.name, org.id)

        # ensure the new org owner has a full access over users with role
        if self.initial_data.get("users", None) is None:
            if not auth_checker.has_access_to_objs(
                self.instance.users.all(), org.owner
            ):
                raise serializers.ValidationError(_(
                    "The new organization owner need to have a full access"
                    "over existing users with this role"
                ))

        return org

    def validate(self, attrs):
        user = self.context['request'].user
        org = attrs.get("org")
        users = attrs.get("users")
        perms = attrs.get("perms")

        if users:
            users_error_obj = serializers.ValidationError({"users": [
                OWNER_ACCESS_OVER_USERS_ISSUE_MESSAGE
            ]})
            # users is specified, make sure the specified org owner has access to users
            if org and not auth_checker.has_access_to_objs(
                users, org.owner
            ):
                raise users_error_obj
            # users is specified, no org, make sure the existing role org owner has access to users
            elif not org and not auth_checker.has_access_to_objs(
                users, self.instance.org.owner
            ):
                raise users_error_obj
        
        if perms:
            # perms is specified, make sure the user making the request can add creator level 
            # perms if such perms is in the request data
            perm_error_obj = serializers.ValidationError({"perms": [
                CREATOR_LEVEL_PERM_ISSUE_MESSAGE
            ]})
            if org and not auth_checker.can_add_creator_level_perms(
                perms, org, user
            ):
                raise perm_error_obj
            elif not org and not auth_checker.can_add_creator_level_perms(
                perms, self.instance.org, user
            ):
                raise perm_error_obj

        return attrs

    def update(self, instance, validated_data):
        if perms := validated_data.get("perms", None):
            validated_data["perms"] = Role.dump_perms(perms)
        
        org = validated_data.get("org", None)
        users = validated_data.get("users", None)

        updated_role = super().update(instance, validated_data)

        if users is not None:
            target_org = org if org is not None else instance.org
            target_org.add_no_exiting_members(users)

        return updated_role