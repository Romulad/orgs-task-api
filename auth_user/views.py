from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode
from django.shortcuts import get_object_or_404
from django.contrib.auth import get_user_model
from django.http.response import Http404
from django.contrib.auth.tokens import default_token_generator

from rest_framework.views import APIView
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework import status
from rest_framework.serializers import ValidationError

from .serializers import (
  RegistrationSerializer,
  RegistrationResponseSerializer,
  PasswordResetSerializer,
  PasswordResetConfirmSerializer
)
from .lib import (
   validate_account_token_generator, 
   send_validation_email,
   send_password_reset_email,
   send_password_reset_confirm_email
)
from app_lib.global_serializers import (
   GlobalMessageResponse
)
from app_lib.decorators import schema_wrapper


class RegistrationView(APIView):
    serializer_class = RegistrationSerializer

    @schema_wrapper(
        RegistrationSerializer,
        RegistrationResponseSerializer,
        status.HTTP_201_CREATED
    )
    def post(self, request:Request):
        """
        # Create a new user
        Use this endpoint to create a **new** account
        """
        req_data = request.data
        serializer = self.serializer_class(data=req_data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        send_validation_email(user, request)
        return Response(
            RegistrationResponseSerializer(user).data,
            status=status.HTTP_201_CREATED
        )


class ValidateNewUserAccountView(APIView):
   
   @schema_wrapper(
        response_serializer=GlobalMessageResponse
   )
   def get(self, request: Request, uuid:str, token:str):
      """# Validate user account after creation
      Email is automatically send when user link is invalid and user 
      account still inactive
      """
      bad_response = Response(
        {"message": "Invalid or expired url"},
        status.HTTP_400_BAD_REQUEST
      )
      try:
        user_email = force_str(urlsafe_base64_decode(uuid))
      except:
        user_email = ""
        
      user_model = get_user_model()

      try:
        user = get_object_or_404(user_model, email=user_email)
      except Http404:
        return bad_response
      
      token_is_valid = validate_account_token_generator.check_token(user, token)
      if token_is_valid:
         user.is_active = True
         user.save()
         return Response(
           { "message": "Your account has been successfully activate"}
         )
      elif not token_is_valid and not user.is_active:
        send_validation_email(user, request, False)
        return Response(
           {"message": "Your account is still inactive. New mail has been sent to validate your account"}
         )
      else:
         return bad_response


class PasswordResetView(APIView):
    serializer_class = PasswordResetSerializer

    @schema_wrapper(
        PasswordResetSerializer,
        GlobalMessageResponse,
    )
    def post(self, request):
        """# Request a password reset
        Use this endpoint to request a password reset email
        """
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.data['email']
        user_model = get_user_model()

        try:
            user = get_object_or_404(user_model, email=email)
        except Http404:
            pass
        else:
            if user and user.is_active:
                send_password_reset_email(user, request)
        
        return Response({"message": "Reset password email has been sent successfully"})


class PasswordResetConfirmView(APIView):
   serializer_class = PasswordResetConfirmSerializer
   
   @schema_wrapper(
      PasswordResetConfirmSerializer,
      GlobalMessageResponse,
    )
   def post(self, request, uuid, token):
        """
        Handles POST requests for resetting a user's password using a password reset token.
        """
        user_email = force_str(urlsafe_base64_decode(uuid))
        user_model = get_user_model()
        bad_response = Response(
            {"message": "Invalid or expired link"},
            status.HTTP_400_BAD_REQUEST
        )

        try:
            user = get_object_or_404(user_model, email=user_email)
        except:
            return bad_response
        
        if not default_token_generator.check_token(user, token):
            return bad_response
        
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)

        new_password = serializer.data['password']
        if user.check_password(new_password):
            raise ValidationError(
                {"password": ["You can not use your old password"]}
            )

        user.set_password(new_password)
        user.save()
        send_password_reset_confirm_email(user)

        return Response(
            {"message": "You password has been changed successfully"}
        )