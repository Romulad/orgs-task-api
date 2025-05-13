from rest_framework import serializers
from django.utils.translation import gettext_lazy as _

from .models import Organization, Department
from user.models import AppUser as User
from user.serializers import UserSerializer
from app_lib.email import send_invitation_success_email
from app_lib.authorization import auth_checker

class OrganizationSerializer(serializers.ModelSerializer):
    id = serializers.ReadOnlyField()
    created_at = serializers.ReadOnlyField()
    owner = UserSerializer(read_only=True)
    members = UserSerializer(many=True, read_only=True)
    name = serializers.ReadOnlyField()
    description = serializers.ReadOnlyField()
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


class CreateOrganizationSerializer(OrganizationSerializer):
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
    members = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=User.objects.select_related(
                "created_by"
            ).prefetch_related(
                "can_be_accessed_by"
            ),
        pk_field=serializers.UUIDField(),
        required=False,
    )
    owner = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.select_related(
                "created_by"
            ).prefetch_related(
                "can_be_accessed_by"
            ),
        pk_field=serializers.UUIDField(),
        required=False,
    )

    def __init__(self, instance=None, data=..., **kwargs):
        super().__init__(instance, data, **kwargs)
        self.fields['owner'].default = self.context.get("user")

    def validate_name(self, value:str):
        user = self.context["user"]
        existed = self.Meta.model.objects.filter(name=value, owner=user).exists()
        if existed:
            raise serializers.ValidationError(
                _("User already has an organization with that name")
            )
        return value

    def validate_owner(self, value:User):
        user = self.context["user"]
        is_allowed = auth_checker.has_access_to_obj(value, user)
        if not is_allowed:
            raise serializers.ValidationError(
                _("You can't add a user you didn't create or have access to as owner")
            )
        return value
    
    def validate(self, attrs):
        user = self.context["user"]
        owner = attrs.get("owner", None)
        members = attrs.get("members", None)

        if members is not None:
            if owner is not None:
                self.check_member_validity(members, owner)
            else:
                self.check_member_validity(members, user)

        return attrs
    
    def check_member_validity(self, members:list[User], owner:User):
        is_allowed = auth_checker.has_access_to_objs(members, owner)
        if not is_allowed:
            raise serializers.ValidationError(
                {"members": [
                    _("You can't add a user you didn't create or have access to as member")
                    ]
                }
            )
        return members
    
    def create(self, validated_data:dict):
        user = self.context["user"]
        members = validated_data.get("members", None)
        if validated_data.get("owner", None) is None:
            validated_data["owner"] = user
        validated_data["created_by"] = user
        created_instance = super().create(validated_data)
        if members is not None:
            send_invitation_success_email(
                members, created_instance.name
            )
        return created_instance


class UpdateOrganizationSerializer(CreateOrganizationSerializer):
    def validate_owner(self, value:User):
        instance = self.instance
        owner_id = instance.owner.id

        if value.id == owner_id:
            return value
        
        # trying to change the owner, check user has access to the new owner
        super().validate_owner(value)
        return value

    def validate(self, attrs:dict):
        members = attrs.get('members', None)
        owner = attrs.get('owner', None)
        all_members = self.instance.members.all()
        current_owner = self.instance.owner

        if owner is not None and members is not None:
            self.check_member_validity(members, owner)
        elif owner is not None and members is None:
            self.check_member_validity(all_members, owner)
        elif owner is None and members is not None and members != all_members:
                self.check_member_validity(members, current_owner)

        return attrs

    def update(self, instance, validated_data):
        instance = super().update(instance, validated_data)
        new_members = []
        if (all_members := validated_data.get("members", None)):
            existed_member_ids = [existed_mem.id for existed_mem in instance.members.all()]
            new_members = [
                new_member for new_member in all_members if not new_member.id in existed_member_ids
            ]
        send_invitation_success_email(new_members, instance.name)
        return instance


class DepartmentSerializer(serializers.ModelSerializer):
    id = serializers.ReadOnlyField()
    created_at = serializers.ReadOnlyField()
    org = OrganizationSerializer(read_only=True)
    name = serializers.ReadOnlyField()
    members = UserSerializer(many=True, read_only=True)
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
        return department


class UpdateDepartmentSerializer(CreateDepartmentSerializer):
    pass