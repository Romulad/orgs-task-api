from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field

from .app_permssions import get_perm_data
from user.models import AppUser
from user.lib import get_user_authorizations_per_org
from organization.models import Organization, Department
from perms.models import UserPermissions, Role
from tags.models import Tag
from tasks.models import Task


# ============= User =============
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
   

#========= Org ==================
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


class CreateUpdateOrgResponseSerializer(OrganizationDetailSerializer):
    owner = serializers.PrimaryKeyRelatedField(read_only=True)


#======= Depart =======
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


class CreateUpdateDepartResponseSerializer(DepartmentDeailSerializer):
    org = serializers.PrimaryKeyRelatedField(read_only=True)


# ======= Perm ========
class PermDataSerializer(serializers.Serializer):
    name = serializers.CharField()
    label = serializers.CharField()
    help_text = serializers.CharField()


class SimpleUserPermissionSerializer(serializers.ModelSerializer):
    perms = serializers.SerializerMethodField()

    class Meta:
        model = UserPermissions
        fields = [
            "perms"
        ]
    
    @extend_schema_field(field=PermDataSerializer(many=True))
    def get_perms(self, user_perm:UserPermissions):
        user_perms = user_perm.get_perms()
        return get_perm_data(user_perms)


class AddPermissionResponseSerializer(serializers.Serializer):
    added = serializers.ListSerializer(child=serializers.CharField())
    not_found = serializers.ListSerializer(child=serializers.CharField())


class RemovePermissionResponseSerializer(serializers.Serializer):
    removed = serializers.ListSerializer(child=serializers.CharField())
    not_found = serializers.ListSerializer(child=serializers.CharField())


class SimpleRoleSerializer(serializers.ModelSerializer):
    id = serializers.ReadOnlyField()
    name = serializers.ReadOnlyField()
    description = serializers.ReadOnlyField()
    created_at = serializers.ReadOnlyField()
    perms = serializers.ReadOnlyField(source="get_perms")

    class Meta:
        model = Role
        fields = [
            "id",
            "name",
            "description",
            "perms",
            "created_at"
        ]
    
    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation["perms"] = instance.get_perms()
        return representation
    

class RoleSerializer(SimpleRoleSerializer):
    org = OrganizationSerializer(read_only=True)

    class Meta:
        model = Role
        fields = [
            *SimpleRoleSerializer.Meta.fields,
            "org",
        ]


class RoleDetailSerializer(RoleSerializer):
    users = UserSerializer(many=True, read_only=True)
    can_be_accessed_by = UserSerializer(many=True, read_only=True)

    class Meta(RoleSerializer.Meta):
        fields = [
            *RoleSerializer.Meta.fields,
            "users",
            "can_be_accessed_by"
        ]


# ============ Tag =============
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



# ============= Task ==============
class TaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = Task
        fields = [
            "id",
            "name",
            "description",
            "due_date",
            "priority",
            "status",
            'estimated_duration',
            "actual_duration",
            "created_at",
        ]
        extra_kwargs = {
            'id': {'read_only': True},
            'name': {'read_only': True},
            'description': {'read_only': True},
            'due_date': {'read_only': True},
            'priority': {'read_only': True},
            'status': {'read_only': True},
            'estimated_duration': {'read_only': True},
            'actual_duration': {'read_only': True},
            'created_at': {'read_only': True},
        }


class TaskDetailSerializer(TaskSerializer):
    assigned_to = UserSerializer(many=True, read_only=True)
    tags = TagSerializer(many=True, read_only=True)
    depart = DepartmentSerializer(read_only=True)
    org = OrganizationSerializer(read_only=True)
    can_be_accessed_by = UserSerializer(many=True, read_only=True)

    class Meta(TaskSerializer.Meta):
        fields = [
            *TaskSerializer.Meta.fields,
            "assigned_to",
            "tags",
            "depart",
            "org",
            "can_be_accessed_by",
        ]


class CreateUpdateTaskResponseSerializer(TaskDetailSerializer):
    org = serializers.PrimaryKeyRelatedField(read_only=True)
    depart = serializers.PrimaryKeyRelatedField(read_only=True)


#======= User detail ==============
class AuthorizationField(serializers.Serializer):
    org = OrganizationSerializer(read_only=True)
    perms = PermDataSerializer(many=True, read_only=True)
    roles = SimpleRoleSerializer(many=True, read_only=True)


class UserDetailSerializer(UserSerializer):
    can_be_accessed_by = UserSerializer(many=True, read_only=True)
    authorizations = serializers.SerializerMethodField()

    class Meta(UserSerializer.Meta):
        fields = [
            *UserSerializer.Meta.fields,
            "can_be_accessed_by",
            "authorizations"
        ]
    
    @extend_schema_field(field=AuthorizationField(many=True))
    def get_authorizations(self, user):
        return get_user_authorizations_per_org(user)