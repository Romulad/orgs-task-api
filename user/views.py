from rest_framework.response import Response
from rest_framework import status, generics
from django.core.mail import send_mail
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.shortcuts import get_object_or_404
from django.contrib.auth.tokens import default_token_generator
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType

from .serializers import (
   UserRegistrationSerializer,
   PasswordResetSerializer,
   PasswordResetConfirmSerializer
)
from .utils import get_tokens_for_user
from .models import AppUser
from .utils import validate_account_token_generator


class RegistrationView(generics.GenericAPIView):
  serializer_class = UserRegistrationSerializer

  def post(self, request):
    """
    # Create a new user
    Provide necessary field to create a new **user**
    """
    serializer = self.serializer_class(data=request.data)
    if serializer.is_valid():
        user = serializer.save()
        send_mail(
           subject='Test Email',
           from_email="testadmin@gmail.com",
           message=f'''Validate your account with this link 
           https://localhost:8000/auth/activate/{urlsafe_base64_encode(force_bytes(user.email))}/{validate_account_token_generator.make_token(user)}/''', 
           recipient_list=[user.email]
        )

        return Response(
           {"message": "User successfully created"},
           status=status.HTTP_201_CREATED
        )
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ValidateNewUserAccountView(APIView):
   
   def get(self, request, uuid, token):
      user_email = force_str(urlsafe_base64_decode(uuid))

      try:
        user = get_object_or_404(AppUser, email=user_email)
      except:
        return Response(
           "Invalid link",
           status.HTTP_400_BAD_REQUEST
        )
      
      if validate_account_token_generator.check_token(user, token):
         user.is_active = True
         user.save()
         return Response(get_tokens_for_user(user))
      else:
         return Response(
           "Invalid link",
           status.HTTP_400_BAD_REQUEST
        )


class PasswordResetView(generics.GenericAPIView):
  permission_classes = [AllowAny]
  serializer_class = PasswordResetSerializer

  def post(self, request):
    serializer = self.serializer_class(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    email = serializer.data['email']

    try:
        user = get_object_or_404(AppUser, email=email)
    except:
        pass
    else:
      send_mail(
          subject='Test Email',
          from_email="testadmin@gmail.com",
          message=f'''Reset your password with this link 
          https://localhost:8000/auth/reset-password-confirm/{urlsafe_base64_encode(force_bytes(email))}/{default_token_generator.make_token(user)}/''', 
          recipient_list=[user.email]
        )
    
    return Response('Email have been sent successfully')


class PasswordResetConfirmView(generics.GenericAPIView):
  serializer_class = PasswordResetConfirmSerializer

  def post(self, request, uuid, token):
      user_email = force_str(urlsafe_base64_decode(uuid))

      try:
        user = get_object_or_404(AppUser, email=user_email)
      except:
        return Response(
           "Invalid link",
           status.HTTP_400_BAD_REQUEST
        )
      
      if not default_token_generator.check_token(user, token):
         return Response(
           "Invalid link",
           status.HTTP_400_BAD_REQUEST
        )
      
      serializer = self.serializer_class(data=request.data)
      if not serializer.is_valid():
         return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

      new_password = serializer.data['password']

      user.set_password(new_password)
      user.save()

      return Response("Password successfully updated")
