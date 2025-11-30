from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('core.urls')),
    path('', include('django.contrib.auth.urls')),
    path('', include('core.web_urls')),
]
