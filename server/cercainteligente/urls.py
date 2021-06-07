from django.contrib import admin
from django.urls import path, include
    
urlpatterns = [
    # django admin
    path('admin/', admin.site.urls),
    # user management
    path('accounts/', include('allauth.urls')),
    path("", include("monitor.urls", namespace="monitor")),
    path('monitor/', include('monitor.urls')),
]
