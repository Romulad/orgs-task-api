from rest_framework.routers import DefaultRouter
from django.urls import path

from .views import OrganizationViewset, DepartmentViewset

router = DefaultRouter()
router.register(r"orgs", OrganizationViewset, "orgs")

urlpatterns = [
    path(
        'orgs/<str:id>/departments/', 
        DepartmentViewset.as_view({
            "post": "create", 
            'get': "list",
            "delete": "bulk_delete"
        }),
        name="departments-list"
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
    )
]

urlpatterns += router.urls