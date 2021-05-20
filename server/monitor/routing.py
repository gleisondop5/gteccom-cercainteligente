from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'^monitor[/]$', consumers.monitor.as_asgi()),
    re_path(r'^monitor[/][?]\w+[=]\w+[&]\w+[=]\w+$', consumers.monitor.as_asgi()),
]

# "/monitor/?group=monitor&name=" + id


# ^ e $ --> correspondem ao início e final da string, respectivamente