from drf_spectacular.utils import extend_schema
from rest_framework import status

from .api_response import (
    ERROR_RESPONSE_EXAMPLE, 
    GlobalValidationErrorResponse
)

def schema_wrapper(
    request_serializer=None,
    response_serializer=None,
    response_status_code=status.HTTP_200_OK,
    **kwargs,
):
    """
    A decorator to simplify the usage of `extend_schema` for API view functions, allowing easy configuration
    of request and response serializers, status codes, and example responses for schema generation.
    Args:
        request_serializer (Serializer): Serializer class for the request body.
        response_serializer (Serializer): Serializer class for the response body.
        response_status_code (int): HTTP status code for the successful response. Defaults to status.HTTP_200_OK.
        **kwargs: Additional keyword arguments passed to `extend_schema`.
    Returns:
        function: A decorator that applies the configured schema to the decorated view function.
    
    **Note**: 
        - `extend_schema` `request` arg overrides `request_serializer` if specified
        - `extend_schema` `responses` arg overrides default responses schema if specified
        - `extend_schema` `examples` arg overrides default examples if specified
    """

    request = kwargs.pop('request', None)
    responses = kwargs.pop('responses', None)
    examples = kwargs.pop('examples', None)

    def wrapper(func):
        return extend_schema(
            request=request_serializer if not request else request,
            responses={
                response_status_code: response_serializer,
                status.HTTP_400_BAD_REQUEST: GlobalValidationErrorResponse
            } if not responses else responses,
            examples=[
                ERROR_RESPONSE_EXAMPLE
            ] if not examples else examples,
            **kwargs
        )(func)

    return wrapper