from rest_framework import serializers
from django.contrib.auth import get_user_model

from auth_user.lib import (
  validate_password, 
)
from user.models import AppUser

class RegistrationSerializer(serializers.Serializer):
  """Registration route request data"""
  email = serializers.EmailField(
    required=True, 
    error_messages={
      "required": "You need to provide a valid email address",
      "invalid": "Your email address is invalid"
    }
  )
  first_name = serializers.CharField(
    min_length=3, required=True,
    error_messages={
      "required": "You need to provide a valid first name",
      "min_length": "Your first name must contain at least 3 characters"
    }
  )
  last_name = serializers.CharField(
    required=False, default="", allow_blank=True
  )
  password = serializers.CharField(
    min_length=8, required=True,
    error_messages={
      "min_length": "Your password must contain at least 8 characters",
    }
  )
  password2 = serializers.CharField(
    required=True, min_length=8, 
    help_text="Same value as the password field and should be provide by the user"
  )

  def validate_email(self, email:str):
    user_model = get_user_model()
    if user_model.objects.filter(email=email).exists():
      raise serializers.ValidationError(
        "A user with that email already exists."
      )
    return email

  def validate_password(self, password:str):
    result = validate_password(password)
    if isinstance(result, str):
      raise serializers.ValidationError(result)
    return password

  def validate(self, attrs:dict):
    password = attrs.get("password", "")
    password2 = attrs.get("password2", "")
    if password != password2 :
      raise serializers.ValidationError(
        {"password2": 'Password mismatch'}
      )
    return attrs

  def create(self, validated_data:dict) -> AppUser:
    user_model = get_user_model()
    validated_data.pop('password2')
    validated_data.setdefault('is_active', False)
    new_user = user_model.objects.create_user(**validated_data)
    return new_user

class RegistrationResponseSerializer(serializers.Serializer):
  """Registration response fields"""
  id = serializers.CharField(required=True)
  email = serializers.EmailField(required=True)
  first_name = serializers.CharField(required=True)
  last_name = serializers.CharField()


class PasswordResetSerializer(serializers.Serializer):
  email = serializers.EmailField(
    required=True,
    error_messages={
      "required": "The email field is required",
      "invalid": "Please provide a valid email address"
    }
  )


class PasswordResetConfirmSerializer(serializers.Serializer):
  password = serializers.CharField(
    required=True, min_length=8,
    error_messages={
      "required": "The password field is required",
      "min_length": "Your password must contain at least 8 characters"
    }
  )
  password2 = serializers.CharField(
    required=True, min_length=8
  )

  def validate_password(self, password:str):
    result = validate_password(password)
    if isinstance(result, str):
      raise serializers.ValidationError(result)
    return password
  
  def validate(self, attrs):
      if attrs['password'] != attrs['password2']:
          raise serializers.ValidationError(
            {"password2": "Passwords must match."}
          )
      return attrs

