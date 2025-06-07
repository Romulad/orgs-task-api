from rest_framework import serializers
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.models import AnonymousUser

from .models import Organization, Department
from user.models import AppUser as User
from user.serializers import UserSerializer
from app_lib.email import send_invitation_success_email
from app_lib.authorization import auth_checker
from app_lib.fn import get_diff_objs

class OrganizationSerializer(serializers.ModelSerializer):
    id = serializers.ReadOnlyField()
    created_at = serializers.ReadOnlyField()
    owner = UserSerializer(read_only=True)
    name = serializers.ReadOnlyField()
    description = serializers.ReadOnlyField()
    class Meta:
        model = Organization
        fields = [
            "id",
            "name",
            "description",
            "owner",
            "created_at"
        ]


class OrganizationDetailSerializer(OrganizationSerializer):
    members = UserSerializer(many=True, read_only=True)
    can_be_accessed_by = UserSerializer(many=True, read_only=True)
    class Meta(OrganizationSerializer.Meta):
        fields = [
            *OrganizationSerializer.Meta.fields,
            "members",
            "can_be_accessed_by"
        ]


class CreateOrganizationSerializer(OrganizationDetailSerializer):
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
        owner_user = self.context.get("user")
        if not isinstance(owner_user, AnonymousUser):
            self.fields['owner'].default = owner_user

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

        if members:
            if owner:
                self.check_member_validity(members, owner)
            else:
                self.check_member_validity(members, user)

        return attrs
    
    def check_member_validity(self, members:list[User], owner:User):
        is_allowed = auth_checker.has_access_to_objs(members, owner)
        if not is_allowed:
            raise serializers.ValidationError(
                {"members": [
                    _("You or the owner you specified can't add a user you didn't create or have access to as member")
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
    description = serializers.CharField(
        required=True, allow_blank=True
    )
    members = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=User.objects.select_related(
                "created_by"
            ).prefetch_related(
                "can_be_accessed_by"
            ),
        pk_field=serializers.UUIDField(),
        required=True,
    )
    owner = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.select_related(
                "created_by"
            ).prefetch_related(
                "can_be_accessed_by"
            ),
        pk_field=serializers.UUIDField(),
        required=True,
    )

    def validate_name(self, value):
        org_name = self.instance.name
        if org_name == value:
            return value
        return super().validate_name(value)
    
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

        if owner and members:
            self.check_member_validity(members, owner)
        elif owner and not members:
            self.check_member_validity(all_members, owner)
        elif not owner and members and members != all_members:
                self.check_member_validity(members, current_owner)

        return attrs

    def update(self, instance, validated_data):
        new_members = []
        if (all_members := validated_data.get("members", None)):
            existed_member_ids = [existed_mem.id for existed_mem in instance.members.all()]
            new_members = [
                new_member for new_member in all_members if not new_member.id in existed_member_ids
            ]
        updated_obj = super().update(instance, validated_data)
        send_invitation_success_email(new_members, instance.name)
        return updated_obj


class DepartmentSerializer(serializers.ModelSerializer):
    id = serializers.ReadOnlyField()
    name = serializers.ReadOnlyField()
    description = serializers.ReadOnlyField()
    org = OrganizationSerializer(read_only=True)
    created_at = serializers.ReadOnlyField()

    class Meta:
        model = Department
        fields = [
            'id',
            'name',
            'description',
            'org',
            'created_at',
        ]


class DepartmentDeailSerializer(DepartmentSerializer):
    members = UserSerializer(many=True, read_only=True)
    can_be_accessed_by = UserSerializer(many=True, read_only=True)

    class Meta(DepartmentSerializer.Meta):
        fields = [
            *DepartmentSerializer.Meta.fields,
            "members",
            "can_be_accessed_by"
        ]


class CreateDepartmentSerializer(DepartmentDeailSerializer):
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
    
    def validate_name(self, value:str):
        org = self.context["org"]
        existed = self.Meta.model.objects.filter(name=value, org=org).exists()
        if existed:
            raise serializers.ValidationError(
                _("Organization already has a department with that name")
            )
        return value

    def validate_members(self, members:list[User]):
        org = self.context["org"]
        org_owner = org.owner
        is_valid = auth_checker.has_access_to_objs(members, org_owner)
        if not is_valid:
            raise serializers.ValidationError(
                _("The org owner need to have full access over members")
            )
        return members

    def create(self, validated_data:dict):
        org = self.context["org"]
        user = self.context['user']

        new_members = []
        if (depart_members := validated_data.get("members", None)):
            org_members = org.members.all()
            new_members = [
                new_member for new_member in depart_members if new_member not in org_members
            ]
        
        validated_data["created_by"] = user
        validated_data["org"] = org
        department = super().create(validated_data)

        if new_members:
            org.members.add(*new_members)
            send_invitation_success_email(new_members, org.name)

        return department


class UpdateDepartmentSerializer(CreateDepartmentSerializer):
    name = serializers.CharField(
        required=True,
        error_messages={
            "required": _("The name field is required"),
            "blank": _("Name field can't not be empty")
        }
    )
    description = serializers.CharField(
        required=True,
    )
    org = serializers.PrimaryKeyRelatedField(
        queryset=Organization.objects.select_related(
                "created_by", "owner"
            ).prefetch_related(
                "can_be_accessed_by", "members"
            ),
        pk_field=serializers.UUIDField(),
        required=True,
    )
    members = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=User.objects.select_related(
                "created_by"
            ).prefetch_related(
                "can_be_accessed_by"
            ),
        pk_field=serializers.UUIDField(),
        required=True,
    )

    def validate_name(self, value):
        existed_name = self.instance.name
        if existed_name == value:
            return value
        existed_org = self.instance.org
        self.context["org"] = existed_org
        return super().validate_name(value)

    def validate_org(self, org:Organization):
        existed_org = self.instance.org

        if existed_org.id == org.id:
            return org
        
        # want to change org for the depart, check if he has access to the new org
        user = self.context["user"]
        is_allowed = auth_checker.has_access_to_obj(org, user)
        if not is_allowed:
            raise serializers.ValidationError(
                _("You don't have access to the new org")
            )
        return org
    
    def validate_members(self, members):
        existed_org = self.instance.org
        self.context["org"] = existed_org
        return super().validate_members(members)

    def validate(self, attrs:dict):
        members_error = serializers.ValidationError({
            "members": [_("The org owner need to have a full access over department members")]
        })
        instance = self.instance
        org = attrs.get('org', None)
        members = attrs.get('members', None)

        if org and members and org.id == instance.org.id:
            return attrs
        elif org and not members:
            if not auth_checker.has_access_to_objs(
                instance.members.all(), org.owner
            ):
                raise members_error
        elif org and members:
            if not auth_checker.has_access_to_objs(
                members, org.owner
            ):
                raise members_error
        elif not org and members:
            if not auth_checker.has_access_to_objs(
                members, instance.org.owner
            ):
                raise members_error
            
        return attrs

    def update(self, instance, validated_data):
        new_member =[]
        members = validated_data.get("members", None)
        org = validated_data.get("org", None)
        if org:
            if members:
                new_member = get_diff_objs(members, org.members.all())
                org.members.add(*new_member) if new_member else ""
            else:
                new_member = get_diff_objs(instance.members.all(), org.members.all())
                org.members.add(*new_member) if new_member else ""
        else:
            if members:
                new_member = get_diff_objs(members, instance.org.members.all())
                instance.org.members.add(*new_member) if new_member else ""

        updated_data = super().update(instance, validated_data)

        if new_member:
            send_invitation_success_email(
                new_member, org.name if org else instance.org.name
            )
        
        return updated_data