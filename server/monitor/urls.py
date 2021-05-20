from django.urls import path

from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('test', views.test, name='test'),
    path('rtsp-panel/<int:controlpoint_id>/<str:monitor_id>/', views.rtsp_panel, name='rtsp-panel'),
    path('agent/<str:tag_slug>/start/', views.agent_start, name='agent-start'),
    path('agent/<str:tag_slug>/stop/', views.agent_stop, name='agent-stop'),
    path('agent/<str:tag_slug>/ask-processing-rate/<str:monitor_id>', views.agent_ask_processing_rate, name='agent-ask-processing-rate'),
    path('camera/<str:tag_slug>/stream/open/<str:monitor_id>', views.camera_stream_open, name='camera-stream-open'),
    path('camera/<str:tag_slug>/stream/keep-alive/<str:monitor_id>', views.camera_stream_keep_alive, name='camera-stream-keep-alive'),
]
