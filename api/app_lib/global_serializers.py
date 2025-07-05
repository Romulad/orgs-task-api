from rest_framework import serializers
from django.utils.translation import gettext_lazy as _

from .authorization import auth_checker
from user.models import AppUser as User

class GlobalMessageResponse(serializers.Serializer):
    """Global message response serializer"""
    message = serializers.CharField(
        required=True,
    )


class BulkDeleteResourceSerializer(serializers.Serializer):
    ids = serializers.ListField(
        child=serializers.UUIDField(),
        min_length=1,
        error_messages={
            "min_length": _("You need to provide a valid list of identifiers"),
        }
    )


class GlobalBulkDeleteResponse(serializers.Serializer):
    """Bulk delete success response"""
    not_found = serializers.ListField(
        child=serializers.CharField(),
        help_text="List of not found ressource ids."
    )
    deleted = serializers.ListField(
        child=serializers.CharField(),
        help_text="List of deleted ressource ids."
    )


class ChangeUserOwnerListSerializer(serializers.Serializer):
    owner_ids = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=User.objects.select_related(
                "created_by"
            ).prefetch_related(
                "can_be_accessed_by"
            ),
        pk_field=serializers.UUIDField(),
        required=True,
        source="id",
        allow_empty=False
    )

    def validate_owner_ids(self, users:User):
        current_user = self.context["user"]

        if self.instance.id == current_user.id:
            return users
                
        is_allowed = auth_checker.has_access_to_objs(users, current_user)
        if not is_allowed:
            raise serializers.ValidationError(_(
                "You need to have full access over user you specified"
            ))
        return users

    def update(self, instance, validated_data):
        owners = validated_data.get("id")
        instance.can_be_accessed_by.set(owners)
        return instance
