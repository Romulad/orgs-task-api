from rest_framework import serializers
from .models import AppUser

class UserRegistrationSerializer(serializers.Serializer):
  email = serializers.EmailField(required=True)
  first_name = serializers.CharField(max_length=50)
  last_name = serializers.CharField(max_length=50)
  password = serializers.CharField(required=True, min_length=8)
  password2 = serializers.CharField(required=True, min_length=8)

  def validate_email(self, value):
    if AppUser.objects.filter(email=value).exists():
        raise serializers.ValidationError("This email is already in use.")
    return value

  def validate(self, attrs):
      if attrs['password'] != attrs['password2']:
          raise serializers.ValidationError("Passwords must match.")
      return attrs

  def create(self, validated_data):
      validated_data.pop('password2')
      validated_data.setdefault('is_active', False)
      user = AppUser.objects.create_user(**validated_data)
      return user


class PasswordResetSerializer(serializers.Serializer):
  email = serializers.EmailField(required=True)


class PasswordResetConfirmSerializer(serializers.Serializer):
  password = serializers.CharField(required=True, min_length=8)
  password2 = serializers.CharField(required=True, min_length=8)

  def validate(self, attrs):
      if attrs['password'] != attrs['password2']:
          raise serializers.ValidationError("Passwords must match.")
      return attrs

