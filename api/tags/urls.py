from rest_framework.routers import DefaultRouter

from .views import TagViewSet

router = DefaultRouter()
router.register(r'tags', TagViewSet, 'tags')

urlpatterns = [
    *router.urls
]