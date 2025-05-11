from rest_framework import serializers
from django.utils.translation import gettext_lazy as _

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
