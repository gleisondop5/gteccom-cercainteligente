from django.urls import path

from . import views

app_name = "monitor"
urlpatterns = [
    path('', views.index, name='index'),
    path('monitoramento', views.monitor, name='monitoramento'),
    path('placaList', views.placaListView, name='placaList'),
    path('administracao', views.admin, name='administracao'),
    path('add-layer', views.add_layer, name='add_layer'),
    path('add-controlpoint', views.add_controlpoint, name='add_controlpoint'),
    path('add-camera', views.add_camera, name='add_camera'),
    path('rtsp-panel/<int:controlpoint_id>/<str:monitor_id>/', views.rtsp_panel, name='rtsp-panel'),
    path('agent/<str:tag_slug>/start/', views.agent_start, name='agent-start'),
    path('camera/<str:tag_slug>/stream/open/<str:monitor_id>', views.camera_stream_open, name='camera-stream-open'),
    path('camera/<str:tag_slug>/stream/keep-alive/<str:monitor_id>', views.camera_stream_keep_alive, name='camera-stream-keep-alive'),
]
