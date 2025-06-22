from rest_framework import serializers
from django.utils.translation import gettext_lazy as _

from app_lib.queryset import queryset_helpers
from app_lib.fields import ManyPrimaryKeyRelatedField
from app_lib.authorization import auth_checker
from .models import Role, UserPermissions
from user.serializers import UserSerializer
from organization.serializers import OrganizationSerializer
from app_lib.app_permssions import permissions_exist, get_perm_data

class SimpleUserPermissionSerializer(serializers.ModelSerializer):
    perms = serializers.SerializerMethodField()

    class Meta:
        model = UserPermissions
        fields = [
            "perms"
        ]
    
    def get_perms(self, user_perm:UserPermissions):
        user_perms = user_perm.get_perms()
        return get_perm_data(user_perms)


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


class SimpleRoleSerializer(serializers.ModelSerializer):
    id = serializers.ReadOnlyField()
    name = serializers.ReadOnlyField()
    description = serializers.ReadOnlyField()
    created_at = serializers.ReadOnlyField()
    perms = serializers.ReadOnlyField()
    class Meta:
        model = Role
        fields = [
            "id",
            "name",
            "description",
            "perms",
            "created_at"
        ]
    
    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation["perms"] = instance.get_perms()
        return representation
    

class RoleSerializer(SimpleRoleSerializer):
    org = OrganizationSerializer(read_only=True)
    class Meta:
        model = Role
        fields = [
            *SimpleRoleSerializer.Meta.fields,
            "org",
        ]


class RoleDetailSerializer(RoleSerializer):
    users = UserSerializer(many=True, read_only=True)
    can_be_accessed_by = UserSerializer(many=True, read_only=True)
    class Meta(RoleSerializer.Meta):
        fields = [
            *RoleSerializer.Meta.fields,
            "users",
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
    users = ManyPrimaryKeyRelatedField(
        queryset=queryset_helpers.get_user_queryset(),
        required=False,
        allow_empty=True,
    )

    def validate_org(self, org):
        user = self.context['request'].user
        if not auth_checker.has_access_to_obj(org, user):
            raise serializers.ValidationError(
                _("You need to have access to the organization")
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
        org = attrs.get("org")

        users = attrs.get("users", None)
        if users:
            if not auth_checker.has_access_to_objs(users, org.owner):
                raise serializers.ValidationError({"users": [
                    _("The org owner need to have access to all users")
                ]})

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

        # ensure the new org does not have a role with the same already
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
        org = attrs.get("org")
        users = attrs.get("users")

        if users:
            if org:
                return super().validate(attrs)
            # users is specified, no org, make sure the existing org owner has access to users
            elif not org and not auth_checker.has_access_to_objs(
                users, self.instance.org.owner
            ):
                raise serializers.ValidationError({"users": [
                    _("The role org owner need to have access to all specified users")
                ]})

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