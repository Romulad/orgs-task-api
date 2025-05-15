from rest_framework.routers import DefaultRouter
from django.urls import path

from .views import OrganizationViewset, DepartmentViewset

router = DefaultRouter()
router.register(r"orgs", OrganizationViewset, "orgs")

urlpatterns = [
    path(
        'orgs/<str:id>/departments/', 
        DepartmentViewset.as_view({"post": "create", 'get': "list"}),
        name="create-department"
    )
]

urlpatterns += router.urls