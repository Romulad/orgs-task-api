from rest_framework import serializers
from django.utils.translation import gettext_lazy as _

from app_lib.queryset import queryset_helpers
from app_lib.fields import ManyPrimaryKeyRelatedField
from app_lib.authorization import auth_checker
from .models import Role
from user.serializers import UserSerializer
from organization.serializers import OrganizationSerializer
from app_lib.app_permssions import permissions_exist

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
                _("You need to have access to the organization")
            )
        return org

    def validate(self, attrs):
        users = attrs["user_ids"]
        org = attrs["org"]

        if not auth_checker.has_access_to_objs(
            users, org.owner
        ):
            raise serializers.ValidationError({
                "user_ids": [_('The org owner need to have a full access over users')]
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


class RoleSerializer(serializers.ModelSerializer):
    id = serializers.ReadOnlyField()
    name = serializers.ReadOnlyField()
    description = serializers.ReadOnlyField()
    org = OrganizationSerializer(read_only=True)
    created_at = serializers.ReadOnlyField()
    perms = serializers.ReadOnlyField(source='get_perms')
    class Meta:
        model = Role
        fields = [
            "id",
            "name",
            "description",
            "perms",
            "org",
            "created_at"
        ]


class RoleDetailSerializer(RoleSerializer):
    can_be_accessed_by = UserSerializer(many=True, read_only=True)
    class Meta(RoleSerializer.Meta):
        fields = [
            *RoleSerializer.Meta.fields,
            "can_be_accessed_by"
        ]


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

    def validate_org(self, org):
        user = self.context['request'].user
        if not auth_checker.has_access_to_obj(org, user):
            raise serializers.ValidationError(
                _("You need to have access to the organization")
            )
        return org
    
    def validate_name(self, name):
        org_id = self.initial_data.get("org", "")
        if Role.objects.filter(
            name=name, org__id=org_id
        ).exists():            
            raise serializers.ValidationError( 
                _("Role with this name already exists in the organization.")
            )
        
        return name
    
    def validate_perms(self, perms):
        _, found, _ = permissions_exist(perms)
        return found
    
    def create(self, validated_data):
        user = self.context['request'].user
        perms = validated_data.get("perms", [])
        validated_data["perms"] = Role.dump_perms(perms)
        validated_data["created_by"] = user
        created_role = super().create(validated_data)
        return created_role