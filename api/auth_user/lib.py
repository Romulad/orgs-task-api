from django.utils.translation import gettext_lazy as _
from django.contrib.auth.tokens import PasswordResetTokenGenerator, default_token_generator
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.request import Request
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from app_lib.email import send_html_email
from app_lib.urls import get_app_base_url
from user.models import AppUser
from app_lib.password import validate_password as v_p


def validate_password(password:str):
    return v_p(password)


def get_tokens_for_user(user):
    refresh = RefreshToken.for_user(user)

    if not user.is_active:
        return False

    return {
        'refresh': str(refresh),
        'access': str(refresh.access_token),
    }

class ValidateAccountTokenGenerator(PasswordResetTokenGenerator):
    def _make_hash_value(self, user, timestamp):
        login_timestamp = (
            ""
            if user.last_login is None
            else user.last_login.replace(microsecond=0, tzinfo=None)
        )
        email_field = user.get_email_field_name()
        email = getattr(user, email_field, "") or ""
        status = user.is_active
        return f"{user.id}{user.password}{login_timestamp}{timestamp}{email}{status}"

    def make_token(self, user):
        """
        Return a token that can be used once to validate user account.
        """
        return super().make_token(user)
    
validate_account_token_generator = ValidateAccountTokenGenerator()


def send_validation_email(
    user: AppUser, 
    request: Request,
    first_time: bool = True
):
    user_email = user.email
    first_name = user.first_name
    uuid = urlsafe_base64_encode(force_bytes(user_email))
    token = validate_account_token_generator.make_token(user)
    context = {
      "first_name": first_name,
      "uuid": uuid,
      "token": token,
      "base_url": get_app_base_url(request),
      "first_time": first_time
    }
    send_html_email(
      f"Welcome {first_name}",
      "email/welcome_email.html",
      user_email,
      context
    )


def send_password_reset_email(
    user: AppUser, 
    request: Request,
):
    user_email = user.email
    first_name = user.first_name
    uuid = urlsafe_base64_encode(force_bytes(user_email))
    token = default_token_generator.make_token(user)
    context = {
      "first_name": first_name,
      "uuid": uuid,
      "token": token,
      "base_url": get_app_base_url(request),
    }
    send_html_email(
      f"Reset your password",
      "email/password_reset_email.html",
      user_email,
      context
    )


def send_password_reset_confirm_email(
    user: AppUser, 
):
    user_email = user.email
    first_name = user.first_name
    context = {
      "first_name": first_name,
    }
    send_html_email(
      f"Password reset successfully",
      "email/password_reset_confirm.html",
      user_email,
      context
    )