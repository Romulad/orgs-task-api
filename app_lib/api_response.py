from drf_spectacular.utils import OpenApiExample
from rest_framework import status, serializers


ERROR_RESPONSE_EXAMPLE = OpenApiExample(
    "Generic Error Response",
    response_only=True,
    summary="Generic error response for various HTTP status codes",
    value={
        "field_name": ["Error message for a specific field, where 'field_name' is the key used during the request"],
        "non_field_errors": ["Error message for a non-field-specific error"],
        "detail": "General error message for responses other than validation errors",
    },
    status_codes=[
        status.HTTP_400_BAD_REQUEST,
        status.HTTP_401_UNAUTHORIZED,
        status.HTTP_403_FORBIDDEN,
        status.HTTP_404_NOT_FOUND,
        status.HTTP_405_METHOD_NOT_ALLOWED,
        status.HTTP_409_CONFLICT,
        status.HTTP_500_INTERNAL_SERVER_ERROR,
    ],
)


class GlobalValidationErrorResponse(serializers.Serializer):
    """Global validation error response serializer"""
    field = serializers.ListField(
        child=serializers.CharField(), 
        help_text="List of errors. **non_field_errors** is used for non-field errors"
    )
