from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import *

router = DefaultRouter()
router.register(r"roles", RoleViewSet, "roles")

urlpatterns = [
    path("perms/", get_permissions_data, name="perm-list"),
    path("add/", AddPermissionView.as_view(), name="add-perms"),
    path("remove/", RemovePermissionView.as_view(), name="remove-perms"),
    *router.urls,
]