from rest_framework.routers import DefaultRouter
from django.urls import path

from .views import OrganizationViewset, DepartmentViewset

router = DefaultRouter()
router.register(r"orgs", OrganizationViewset, "orgs")

urlpatterns = [
    *router.urls,
    path(
        'orgs/<str:id>/departments/', 
        DepartmentViewset.as_view({
            "post": "create", 
            'get': "list",
        }),
        name="departments-list"
    ),
    path(
        'orgs/<str:id>/departments/bulk-delete/',
        DepartmentViewset.as_view({
            "delete": "bulk_delete"
        }),
        name="departments-delete"
    ),
    path(
        'orgs/<str:id>/departments/<str:depart_id>/', 
        DepartmentViewset.as_view({
            "get": "retrieve", 
            "patch": "partial_update",
            "put": "update",
            "delete": "destroy"
        }),
        name="departments-detail"
    ),
]