from django.contrib.auth.tokens import default_token_generator

from app_lib.email import send_html_email
from app_lib.urls import get_app_base_url, generate_url_safe_uuid


def send_account_created_notification(user, request):
    """Send an email to the user to notify that his account has been created"""
    template = 'emails/account_created_notif.html'
    context = {
        "first_name": user.first_name,
        "uuid": generate_url_safe_uuid(user.email),
        "token": default_token_generator.make_token(user),
        "base_url": get_app_base_url(request),
    }
    send_html_email(
        title="Invitation to join Platform",
        template_name=template,
        email=user.email,
        context=context
    )