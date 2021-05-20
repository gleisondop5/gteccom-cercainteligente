from django.contrib import admin
from django.urls import path
from django.conf.urls import include

urlpatterns = [
    path('monitor/', include('monitor.urls')),
    #path('rtsp-panel/', include('monitor.urls')),
    path('admin/', admin.site.urls),
    #path('monitor/home/', include('monitor.urls')),
]
