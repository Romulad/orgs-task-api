from rest_framework import serializers
from django.utils.translation import gettext_lazy as _

from .models import Tag
from organization.serializers import OrganizationSerializer
from user.serializers import UserSerializer
from app_lib.queryset import queryset_helpers
from app_lib.authorization import auth_checker
from app_lib.app_permssions import CAN_CREATE_TAG
from app_lib.common_error_messages import ORG_ACCESS_ISSUE_MESSAGE

class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ['id', 'name', 'description', 'created_at']
        extra_kwargs = {
            'id': {'read_only': True},
            'name': {'read_only': True},
            'description': {'read_only': True},
            'created_at': {'read_only': True},
        }


class TagDetailSerializer(TagSerializer):
    org = OrganizationSerializer(read_only=True)
    can_be_accessed_by = UserSerializer(read_only=True, many=True)

    class Meta(TagSerializer.Meta):
        fields = [
            *TagSerializer.Meta.fields,
            'org',
            'can_be_accessed_by'
        ]
        extra_kwargs = {
            **TagSerializer.Meta.extra_kwargs,
        }


class CreateTagSerializer(TagDetailSerializer):
    name = serializers.CharField(
        required=True,
        max_length=255,
        allow_blank=False,
    )
    description = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
    )
    org = serializers.PrimaryKeyRelatedField(
        required=True,
        queryset=queryset_helpers.get_org_queryset()
    )
     
    def validate_org(self, org):
        user = self.context['request'].user
        error_obj = serializers.ValidationError(
            ORG_ACCESS_ISSUE_MESSAGE
        )

        if auth_checker.has_access_to_obj(org, user):
            return org
        
        if (
            not self.instance and 
            auth_checker.has_permission(user, org, CAN_CREATE_TAG)
        ):
            return org
        
        raise error_obj
    
    def assert_name_uniqueness(self, name, org_id):
        if Tag.objects.filter(
            name=name, org__id=org_id
        ).exists():           
            raise serializers.ValidationError( 
                _("Tag with this name already exists in the organization.")
            )
    
    def validate_name(self, name):
        org_id = self.initial_data.get("org", "")
        if org_id:
            self.assert_name_uniqueness(name, org_id)
        # org will be validate at the org validation step if missing or invalid
        return name
    
    def create(self, validated_data):
        user = self.context['request'].user
        validated_data["created_by"] = user

        created_tag = super().create(validated_data)

        return created_tag


class UpdateTagSerializer(CreateTagSerializer):
    description = serializers.CharField(
        required=True,
        allow_blank=True,
    )

    def validate_name(self, name):
        if self.instance.name == name:
            return name
        
        if self.initial_data.get("org"):
            return super().validate_name(name)
        
        self.assert_name_uniqueness(name, self.instance.org.id)

        return name

    def validate_org(self, org):
        if self.instance.org.id == org.id:
            return org
        
        # validate user permission over org
        super().validate_org(org)

        # ensure the new org does not have a tag with the same already
        # This validation make sens when the name is not include in the request
        # data, otherwise the validation will be done during name validation
        if self.initial_data.get("name", None) is None:
            self.assert_name_uniqueness(self.instance.name, org.id)

        return org