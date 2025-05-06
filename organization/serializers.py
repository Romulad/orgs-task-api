from rest_framework import serializers

from .models import Organization
from user.serializers import UserSerializer

class OrganizationSerializer(serializers.ModelSerializer):
    id = serializers.ReadOnlyField()
    created_at = serializers.ReadOnlyField()
    owner = UserSerializer()
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