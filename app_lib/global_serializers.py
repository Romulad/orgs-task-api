from rest_framework import serializers


class GlobalMessageResponse(serializers.Serializer):
    """Global message response serializer"""
    message = serializers.CharField(
        required=True,
    )