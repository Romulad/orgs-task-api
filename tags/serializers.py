from rest_framework import serializers
from django.utils.translation import gettext_lazy as _

from .models import Tag
from organization.serializers import OrganizationSerializer

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

    class Meta(TagSerializer.Meta):
        fields = [
            *TagSerializer.Meta.fields,
            'org'
        ]
        extra_kwargs = {
            **TagSerializer.Meta.extra_kwargs,
        }