from django.contrib import admin
from django.conf import settings
from django.urls import path, include
from drf_spectacular.views import (
    SpectacularSwaggerView, 
    SpectacularAPIView, 
    SpectacularRedocView
)


urlpatterns = [
    path('', SpectacularSwaggerView.as_view(url_name='schema'), name="swagger"),
    path('auth/', include('auth_user.urls')),
    path('', include('user.urls')),
    path('perms/', include('perms.urls')),
    path('', include('organization.urls')),
    path('', include('tasks.urls')),
    path('api-auth/', include('rest_framework.urls')),
    path("api/schema", SpectacularAPIView.as_view(), name="schema"),
    path('redoc/', SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
]

if settings.DEBUG:
    urlpatterns.append(
        path('admin/', admin.site.urls)
    )