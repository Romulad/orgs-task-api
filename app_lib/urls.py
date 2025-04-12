from rest_framework.request import Request
from urllib.parse import urlparse


def get_app_base_url(request: Request) -> str:
    """
    Get the base URL of the app.
    """
    url = urlparse(request.build_absolute_uri())
    return f"{url.scheme}://{url.hostname}"