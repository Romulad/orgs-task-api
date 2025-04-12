from rest_framework_simplejwt.views import (
  TokenObtainPairView,
  TokenRefreshView
)
from django.urls import path

from .views import *

urlpatterns = [
  path(
    'register/', 
    RegistrationView.as_view(), 
    name="register"
  ),
  path(
    'login/', 
    TokenObtainPairView.as_view(), 
    name='login'
  ),
  path(
    'refresh/', 
    TokenRefreshView.as_view(), 
    name='token_refresh'
  ),
  path(
    'activate/<str:uuid>/<str:token>/', 
    ValidateNewUserAccountView.as_view(), 
    name='validate_account'
  ),
  path(
    'reset-password/', 
    PasswordResetView.as_view(), 
    name='password_reset'
  ),
  path(
    'reset-password/<str:uuid>/<str:token>/', 
    PasswordResetConfirmView.as_view(), 
    name='password_reset_confirm'
  ),
]
