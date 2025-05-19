from rest_framework import serializers
from .models import AppUser


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
    id = serializers.ReadOnlyField()
    created_at = serializers.ReadOnlyField()
    first_name = serializers.CharField(min_length=3)
    class Meta:
        model = AppUser
        fields = [
            "id",
            "email",
            "first_name",
            "last_name",
            "orgs",
            "created_at"
        ]