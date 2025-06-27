from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _

from .models import AppUser
from app_lib.password import generate_password, validate_password
from .lib import send_account_created_notification
from .lib import get_user_authorizations_per_org

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


class UserDetailSerializer(UserSerializer):
    can_be_accessed_by = UserSerializer(many=True, read_only=True)
    authorizations = serializers.SerializerMethodField()

    class Meta(UserSerializer.Meta):
        fields = [
            *UserSerializer.Meta.fields,
            "can_be_accessed_by",
            "authorizations"
        ]
    
    def get_authorizations(self, user):
        return get_user_authorizations_per_org(user)


class CreateUserSerializer(UserDetailSerializer):
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
    
    class Meta(UserDetailSerializer.Meta):
        fields = [
            *UserDetailSerializer.Meta.fields,
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


class UpdateUserSerializer(UserDetailSerializer):
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
        required=True, allow_blank=True
    )

    def validate_email(self, email):
        if email == self.instance.email:
            return email
        user_model = get_user_model()
        if user_model.objects.filter(email=email).exists():
            raise serializers.ValidationError(
                _("A user with that email already exists.")
            )
        return email


class UpdateUserPasswordSerializer(serializers.Serializer):
    new_password = serializers.CharField(
        required=True, min_length=8, write_only=True
    )
    confirm_new_password = serializers.CharField(
        required=True, min_length=8, write_only=True
    )
    password = serializers.CharField(
        required=True, min_length=8, write_only=True
    )
    
    def validate_new_password(self, new_password:str):
        result = validate_password(new_password)
        if isinstance(result, str):
            raise serializers.ValidationError(result)

        target_user = self.context["target_user"]
        if target_user.check_password(new_password):
            raise serializers.ValidationError(_("You can't reuse the same password"))

        return new_password  

    def validate_password(self, password:str):
        user = self.context["user"]
        if not user.check_password(password):
            raise serializers.ValidationError(_("Invalid password"))

        return password

    def validate(self, attrs):
        new_password = attrs.get("new_password")
        confirm_new_password = attrs.get("confirm_new_password")
        if new_password != confirm_new_password:
            raise serializers.ValidationError(
                {"confirm_new_password": [
                    _("Password mismatch")
                ]}
            )
        return attrs 
    
    def update(self, instance, validated_data):
        new_password = validated_data.get("new_password")
        instance.set_password(new_password)
        instance.save()
        return instance