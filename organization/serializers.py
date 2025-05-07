from rest_framework import serializers
from django.utils.translation import gettext_lazy as _

from .models import Organization
from user.serializers import UserSerializer

class OrganizationSerializer(serializers.ModelSerializer):
    id = serializers.ReadOnlyField()
    created_at = serializers.ReadOnlyField()
    owner = UserSerializer(read_only=True)
    members = UserSerializer(many=True)
    
    class Meta:
        model = Organization
        fields = [
            "id",
            "name",
            "description",
            "owner",
            "members",
            "created_at"
        ]


class CreateOrganizationSerializer(serializers.ModelSerializer):
    id = serializers.ReadOnlyField()
    name = serializers.CharField(
        required=True,
        error_messages={
            "required": _("The name field is required"),
            "blank": _("Name field can't not be empty")
        }
    )
    owner = UserSerializer(read_only=True)
    class Meta:
        model = Organization
        fields = [
            "id",
            "name",
            "description",
            "owner",
        ]

    def validate_name(self, value:str):
        user = self.context["user"]
        existed = self.Meta.model.objects.filter(name=value, owner=user).exists()
        if existed:
            raise serializers.ValidationError(
                _("User already has an organization with that name")
            )
        return value
    
    def create(self, validated_data:dict):
        user = self.context["user"]
        validated_data["owner"] = user
        validated_data["created_by"] = user
        return super().create(validated_data)