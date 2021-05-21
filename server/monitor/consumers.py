import json, logging
from urllib.parse import parse_qs
from channels.generic.websocket import AsyncWebsocketConsumer, WebsocketConsumer
from channels.layers import get_channel_layer
from random import randint
from asyncio import sleep


log_format = '%(asctime)s---%(levelname)s---%(filename)s---%(message)s'
logging.basicConfig(filename='tcc.log',
                    # w -> sobrescreve o arquivo a cada log
                    # a -> não sobrescreve o arquivo
                    filemode='w',
                    level=logging.DEBUG,
                    format=log_format)
logger = logging.getLogger('root')


POSSIBLE_GROUPS = frozenset(["agent", "monitor"])


agents = dict()

class WSConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.accept()

        for i in range (1000):
            await self.send(json.dumps({'message': randint(-20, 20)}))
            await sleep(1)

class monitorConsumer(AsyncWebsocketConsumer):

    async def connect(self):        
        self.params = parse_qs(self.scope["query_string"].decode()) #pega o query_string        
        self.group = self.params.get('group', 'no_suplied')[0] #guarda o grupo (monitor). [0] pega só o nome sem os ['']
        self.name = self.params.get('name', 'no_suplied')[0] # guarda o name (id)
        self.room_group_name = self.group        

        if self.group in POSSIBLE_GROUPS and self.name != 'Not Supplied': 


            await self.channel_layer.group_add(
                self.room_group_name,
                self.channel_name
            )
            await self.accept() #aceita a conexão
            
            
            if self.group == 'agent':
                camera_running = int(self.params.get('camera_running', ('0'))[0])
                agents[self.name] = camera_running
                #logger.info(f'=====> agents: {agents}')
                await self.channel_layer.group_send("monitor", {
                    'type': 'send_message',
                    "event": "agent-connect",
                    'who': self.name, 
                    'camera_running': camera_running
                })
                
            elif self.group == 'monitor':
                await self.channel_layer.group_send(self.room_group_name, {
                    'type': 'send_message',
                    "event": "inventory",
                    'agents': list(agents.items())
                })

        else:
            await self.close()

        


    async def disconnect(self, close_code):
        if self.group == 'agent':

            await self.channel_layer.group_send(self.room_group_name, {
                    'type': 'send_message',
                    "event": "agent-disconnect",
                    'who': self.name
                })

            del agents[self.name]

            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )

            '''
            mensagem = json.dumps({'who': self.name})  
            await self.channel_layer.group_discard(
                'monitores',
                    {
                        'type': 'agent-disconnect',
                        'message': mensagem
                    }
            )
            '''

    async def receive(self, text_data): 
        
        logger.info(f'=====> Msg recebida: {text_data}') 

        response = json.loads(text_data)
        self.event = response.get("event", None)
        

        if self.event == 'stop-request':
                logger.info(f'=====> Msg enviada para agent (stop-request)') 
                message = response.get("message", None)
                await self.channel_layer.group_send("agent", {
                    'type': 'send_message',
                    "event": "stop-request",
                    'message': message
                })
        
        if self.event == 'ask-processing-rate':
                logger.info(f'=====> Msg enviada para agent (ask-processing-rate)') 
                message = response.get("message", None)
                monitor_id = response.get("target", None)
                await self.channel_layer.group_send("agent", {
                    'type': 'send_message',
                    "event": "processing-rate-request",
                    'who': monitor_id,
                    'message': message
                })

        if self.event == 'agent-processing-rate':
            logger.info(f'=====> Msg enviada por agent-processing-rate') 
            monitor_id = response.get("target", None)
            tag_slug = response.get("who", None)
            processing_rate = response.get("processing_rate", None)
            await self.channel_layer.group_send("monitor", {
                'type': 'send_message',
                "event": "agent-processing-rate",
                'target': monitor_id,
                'who': tag_slug,
                'message': processing_rate
            })

        if self.event == 'stop-agent':
            logger.info(f'=====> Msg enviada por stop-agent') 

            monitor = response.get("target-groups", None)
            tag_slug = response.get("who", None)
            camera_running = response.get("camera_running", None)

            await self.channel_layer.group_send("monitor", {
                'type': 'send_message',
                "event": "stop-agent",
                'target-groups': monitor,
                'who': tag_slug,
                'camera_running': camera_running
            })
        
        
    async def send_message(self, msg):
        #logger.info(f'=====> Msg enviada: {msg}') 
        await self.send(text_data=json.dumps({
            "payload": msg
        }))



