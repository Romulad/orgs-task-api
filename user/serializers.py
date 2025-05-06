from rest_framework import serializers
from .models import AppUser


class UserSerializer(serializers.ModelSerializer):
    id = serializers.ReadOnlyField()
    date_joined = serializers.ReadOnlyField()
    first_name = serializers.CharField(min_length=3)
    class Meta:
        model = AppUser
        fields = [
            "id",
            "email",
            "first_name",
            "last_name",
            "date_joined"
        ]


class UserDetailSerializer(serializers.ModelSerializer):
    id = serializers.ReadOnlyField()
    date_joined = serializers.ReadOnlyField()
    first_name = serializers.CharField(min_length=3)
    class Meta:
        model = AppUser
        fields = [
            "id",
            "email",
            "first_name",
            "last_name",
            "is_owner",
            "is_manager",
            "orgs",
            "date_joined"
        ]