import json
from channels.generic.websocket import AsyncWebsocketConsumer
import urllib


POSSIBLE_GROUPS = frozenset(['agent', 'monitor'])


agents = dict()


class monitor(AsyncWebsocketConsumer):
    async def ws_connect(self):
        self.params = urllib.parse.parse_qs.scope['query_string'].decode()
        group = params.get('group', no_suplied) 
        name = params.get('name', no_suplied)
        
        if group in POSSIBLE_GROUPS and name != no_suplied:
            self.reply_channel.send({'accept': True})
            self.channel_session['group'] = group
            self.channel_session['name'] = name

            await self.channel_layer.group_add(self.reply_channel)
            
            if group == 'agent':
                camera_running = int(params.get('camera_running', ('0',))[0])
                agents[name] = camera_running
                await self.channel_layer.group_send(
                    {'text': json.dumps({
                    'type': 'agent-connect',
                    'who': name,
                    'camera_running': camera_running,
                })})
            elif group == 'monitor':
                self.reply_channel.send({'text': json.dumps({
                    'type': 'inventory',
                    'agents': list(agents.items())
                })})
        else:
           await self.reply_channel.send({'accept': False})


    async def ws_message(self, event):
        text = event['message']
        data = json.loads(text)
        
        if data['type'] == 'agent-update':
            agents[data['who']] = data['camera_running']
        
        for group in data.get('target-groups', POSSIBLE_GROUPS):
            self.reply_channel.send({'text': text})


    async def ws_disconnect(self, close_code):
        group = self.channel_session['group']
        name = self.channel_session['name']
        
        if group == 'agent':
            del agents[name]
            self.reply_channel.send({
                'text': json.dumps({
                'type': 'agent-disconnect',
                'who': name
            })})
        await self.channel_layer.group_discard(
            self.reply_channel
        )
