
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth.tokens import PasswordResetTokenGenerator


def get_tokens_for_user(user):
    refresh = RefreshToken.for_user(user)

    if not user.is_active:
        return False

    return {
        'refresh': str(refresh),
        'access': str(refresh.access_token),
    }


class ValidateAccountPasswordGenerator(PasswordResetTokenGenerator):
     def _make_hash_value(self, user, timestamp):
        login_timestamp = (
            ""
            if user.last_login is None
            else user.last_login.replace(microsecond=0, tzinfo=None)
        )
        email_field = user.get_email_field_name()
        email = getattr(user, email_field, "") or ""
        return f"{user.pk}{user.password}{login_timestamp}{timestamp}{email}{user.is_active}"
     
validate_account_token_generator = ValidateAccountPasswordGenerator()
