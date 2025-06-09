from django.urls import path

from .views import *

urlpatterns = [
    path("add/", AddPermissionView.as_view(), name="add-perms"),
    path("remove/", RemovePermissionView.as_view(), name="remove-perms"),
]