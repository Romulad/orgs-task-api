from rest_framework import serializers
from django.utils.translation import gettext_lazy as _

from .models import Organization, Department
from user.models import AppUser as User
from user.serializers import UserSerializer
from app_lib.email import send_invitation_success_email

class OrganizationSerializer(serializers.ModelSerializer):
    id = serializers.ReadOnlyField()
    created_at = serializers.ReadOnlyField()
    owner = UserSerializer(read_only=True)
    members = UserSerializer(many=True)
    departments = serializers.PrimaryKeyRelatedField(
        many=True,
        read_only=True,
    )
    
    class Meta:
        model = Organization
        fields = [
            "id",
            "name",
            "description",
            "owner",
            "members",
            'departments',
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
    members = UserSerializer(many=True, read_only=True)
    class Meta:
        model = Organization
        fields = [
            "id",
            "name",
            "description",
            "owner",
            "members",
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
        queryset=User.objects.select_related(
                "created_by"
            ).prefetch_related(
                "can_be_accessed_by"
            ),
        pk_field=serializers.UUIDField(),
        allow_null=True
    )

    def validate_members(self, members:list[User]):
        owner_id = self.instance.owner.id
        for member in members:
            is_allowed = True
            can_have_access = owner_id in [
                have_access.id for have_access in member.can_be_accessed_by.all()
            ]
            if member.created_by:
                is_allowed = (
                    can_have_access or
                    member.created_by.id == owner_id
                )
            else:
                is_allowed = can_have_access
            if not is_allowed:
                raise serializers.ValidationError(
                    _("You can't add a user you didn't create or have access to as member")
                )
        return members
    
    def update(self, instance, validated_data):
        new_members = []
        if (all_members := validated_data.get("members", None)):
            existed_member_ids = [existed_mem.id for existed_mem in instance.members.all()]
            new_members = [
                new_member for new_member in all_members if not new_member.id in existed_member_ids
            ]

        instance = super().update(instance, validated_data)
        send_invitation_success_email(new_members, instance.name)
        return instance


class DepartmentSerializer(serializers.ModelSerializer):
    id = serializers.ReadOnlyField()
    created_at = serializers.ReadOnlyField()
    org = serializers.PrimaryKeyRelatedField(read_only=True)
    name = serializers.ReadOnlyField()
    members = serializers.PrimaryKeyRelatedField(many=True, read_only=True)
    description = serializers.ReadOnlyField()

    class Meta:
        model = Department
        fields = [
            'id',
            'name',
            'description',
            'org',
            "members",
            'created_at',
        ]


class CreateDepartmentSerializer(DepartmentSerializer):
    name = serializers.CharField(
        required=True,
        error_messages={
            "required": _("The name field is required"),
            "blank": _("Name field can't not be empty")
        }
    )
    description = serializers.CharField(
        required=False, allow_blank=True
    )
    
    def validate_name(self, value:str):
        org = self.context["org"]
        existed = self.Meta.model.objects.filter(name=value, org=org).exists()
        if existed:
            raise serializers.ValidationError(
                _("Organization already has a department with that name")
            )
        return value

    def create(self, validated_data:dict):
        org = self.context["org"]
        user = self.context['user']
        validated_data["org"] = org
        validated_data["created_by"] = user
        department = super().create(validated_data)
        org.departments.add(department)
        return department
