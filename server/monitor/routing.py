from django.urls import re_path, path

from . import consumers

websocket_urlpatterns = [
    re_path(r'monitor/', consumers.monitorConsumer.as_asgi()),
    re_path(r'monitor/\?group=monitor&name=[a-zA-Z0-9-]+/', consumers.monitorConsumer.as_asgi()),
    re_path(r'monitor/\?group=agent&name=[a-zA-Z0-9-]+&camera_running=[a-zA-Z0-9-]+/', consumers.monitorConsumer.as_asgi()),
]

