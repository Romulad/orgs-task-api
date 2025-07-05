from rest_framework.request import Request
from urllib.parse import urlparse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode


def get_app_base_url(request: Request) -> str:
    """
    Get the base URL of the app.
    """
    url = urlparse(request.build_absolute_uri())
    return f"{url.scheme}://{url.hostname}"


def generate_url_safe_uuid(value:str) -> str:
    """
    Generate a URL-safe UID.
    """
    return urlsafe_base64_encode(force_bytes(value))