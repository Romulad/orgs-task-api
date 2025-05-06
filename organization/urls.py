from rest_framework.routers import DefaultRouter

from .views import OrganizationViewset

router = DefaultRouter()
router.register(r"orgs", OrganizationViewset, "orgs")

urlpatterns = [

]

urlpatterns += router.urls