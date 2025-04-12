from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode
from django.shortcuts import get_object_or_404
from django.contrib.auth import get_user_model

from rest_framework.views import APIView
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework import status
from rest_framework import serializers
from drf_spectacular.utils import extend_schema, inline_serializer

from .serializers import (
  RegistrationSerializer,
  RegistrationResponseSerializer
)
from .lib import validate_account_token_generator, send_validation_email

class RegistrationView(APIView):
  serializer_class = RegistrationSerializer

  @extend_schema(
      request=RegistrationSerializer,
      responses={201: RegistrationResponseSerializer},
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
   
   @extend_schema(
      responses={
        200: inline_serializer(
           "SuccessResponse", {"message": serializers.CharField()}
        ),
        400: inline_serializer(
           "BadRequestResponse", {"message": serializers.CharField()}
        )
      }
   )
   def get(self, request: Request, uuid:str, token:str):
      """# Validate user account after creation
      Email is automatically send when user link is invalid and user 
      account still inactive
      """
      user_email = force_str(urlsafe_base64_decode(uuid))
      user_model = get_user_model()
      bad_response = Response(
        {"message": "Invalid or expired url"},
        status.HTTP_400_BAD_REQUEST
      )

      try:
        user = get_object_or_404(user_model, email=user_email)
      except:
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