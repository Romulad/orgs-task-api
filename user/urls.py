from rest_framework_simplejwt.views import (
  TokenObtainPairView,
  TokenRefreshView
)
from django.urls import path

from .views import *

urlpatterns = [
  path('registration/', RegistrationView.as_view(), name="registration"),
  path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
  path('activate/<uuid>/<token>/', ValidateNewUserAccountView.as_view(), name='validate_account'),
  path('reset-password/', PasswordResetView.as_view(), name='password_reset'),
  path('reset-password-confirm/<uuid>/<token>/', PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
  path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
]
