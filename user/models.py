from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.utils.translation import gettext_lazy as _
from django.core.validators import EmailValidator

from .user_manager import CustomUserManager
from app_lib.models import AbstractBaseModel

class AppUser(AbstractBaseModel, AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(
        _("email"),
        unique=True,
        validators=[EmailValidator],
        error_messages={
            "unique": _("A user with that email already exists."),
        },
    )
    first_name = models.CharField(
        _("first name"), max_length=150
    )
    last_name = models.CharField(
        _("last name"), max_length=150, blank=True
    )
    is_staff = models.BooleanField(
        _("staff status"),
        default=False,
        help_text=_("Designates whether the user can log into this admin site."),
    )
    is_active = models.BooleanField(
        _("active"),
        default=True,
        help_text=_(
            "Designates whether this user should be treated as active. "
            "Unselect this instead of deleting accounts."
        ),
    )
    
    objects = CustomUserManager()

    USERNAME_FIELD = 'email'
    EMAIL_FIELD = "email"
    REQUIRED_FIELDS = ["first_name"]
    
    class Meta:
        verbose_name = _("user")
        verbose_name_plural = _("users")