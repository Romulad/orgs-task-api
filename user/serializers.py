from rest_framework import serializers
from django.contrib.auth import get_user_model

from .models import AppUser
from app_lib.password import generate_password, validate_password
from .lib import send_account_created_notification


class UserSerializer(serializers.ModelSerializer):
    id = serializers.ReadOnlyField()
    created_at = serializers.ReadOnlyField()
    first_name = serializers.ReadOnlyField()
    last_name  = serializers.ReadOnlyField()
    email = serializers.ReadOnlyField()
    class Meta:
        model = AppUser
        fields = [
            "id",
            "email",
            "first_name",
            "last_name",
            "created_at"
        ]

class CreateUserSerializer(UserSerializer):
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
        default=generate_password, allow_blank=False,
        error_messages={
            "min_length": "Your password must contain at least 8 characters",
        }, 
        write_only=True
    )
    
    class Meta(UserSerializer.Meta):
        fields = [
            *UserSerializer.Meta.fields,
            "password"
        ]
    
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

    def create(self, validated_data:dict) -> AppUser:
        request = self.context["request"]
        user_model = get_user_model()
        validated_data.setdefault('created_by', request.user)
        new_user = user_model.objects.create_user(**validated_data)
        send_account_created_notification(new_user, request)
        return new_user