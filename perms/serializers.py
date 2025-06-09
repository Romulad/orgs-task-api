from rest_framework import serializers
from django.utils.translation import gettext_lazy as _

from app_lib.queryset import queryset_helpers
from app_lib.fields import ManyPrimaryKeyRelatedField
from app_lib.authorization import auth_checker


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