
import os
from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application
from channels.auth import AuthMiddlewareStack
import monitor.routing
import django_async_stream

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'cercainteligente.settings') #codigo django automático

# diz aos canais qual código executar quando uma solicitação HTTP é recebida pelo servidor de canais
application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": AuthMiddlewareStack(URLRouter(monitor.routing.websocket_urlpatterns)),# Aponta a configuração de roteamento raiz no módulo monitor.routing
})



#application = get_asgi_application()

django_async_stream.patch_application(get_asgi_application())

'''
Esta configuração de roteamento raiz especifica que quando uma conexão é feita com o servidor de desenvolvimento de canais, 
o ProtocolTypeRouterprimeiro inspecionará o tipo de conexão. Se for uma conexão WebSocket ( ws: // ou wss: // ), a conexão 
será fornecida ao AuthMiddlewareStack.

O AuthMiddlewareStackirá preencher o escopo da conexão com uma referência ao usuário autenticado no momento, semelhante a 
como o Django AuthenticationMiddlewarepopula o objeto de solicitação de uma função de visualização com o usuário autenticado 
no momento. (Os escopos serão discutidos posteriormente neste tutorial.) Em seguida, a conexão será fornecida ao URLRouter.

O URLRouterexaminará o caminho HTTP da conexão para encaminhá-la para um determinado consumidor, com base nos urlpadrões 
fornecidos.
'''
