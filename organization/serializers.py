from rest_framework import serializers
from django.utils.translation import gettext_lazy as _
from django.db.models.query import Q

from .models import Organization
from user.models import AppUser as User
from user.serializers import UserSerializer
from app_lib.email import send_invitation_success_email

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


class UpdateOrganizationSerializer(
    OrganizationSerializer, CreateOrganizationSerializer
) :
    members = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=User.objects.all(),
        required=False,
    )

    def validate_members(self, memberIds:list):
        owner_id = self.instance.owner.id
        not_allowed = User.objects.filter(
            Q(id__in=memberIds),
            ~Q(created_by__id=owner_id), 
            ~Q(can_be_accessed_by__in=[owner_id])
        )
        if not_allowed:
            raise serializers.ValidationError(
                _("You can't add a user you didn't create or have access to as member")
            )
        return memberIds

    def update(self, instance, validated_data):
        memberIds = validated_data["members"]
        new_members = instance.members.filter(~Q(id__in=memberIds))
        instance = super().update(instance, validated_data)
        send_invitation_success_email(new_members, instance.name)
        return instance