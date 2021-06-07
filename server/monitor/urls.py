from django.urls import path

from . import views

app_name = "monitor"
urlpatterns = [
    path("", views.home, name="home"),
    path('mapa', views.index, name='index'),
    path('placaList', views.placaListView, name='placaList'),
    path('rtsp-panel/<int:controlpoint_id>/<str:monitor_id>/', views.rtsp_panel, name='rtsp-panel'),
    path('agent/<str:tag_slug>/start/', views.agent_start, name='agent-start'),
    path('camera/<str:tag_slug>/stream/open/<str:monitor_id>', views.camera_stream_open, name='camera-stream-open'),
    path('camera/<str:tag_slug>/stream/keep-alive/<str:monitor_id>', views.camera_stream_keep_alive, name='camera-stream-keep-alive'),
]
