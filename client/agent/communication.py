import asyncio
from time import sleep
import time


@asyncio.coroutine
def on_open(agent, data):
    pass
    
    
@asyncio.coroutine
def on_close(agent, data):
    pass
    
    
@asyncio.coroutine
def on_error(agent, data):
    pass
    
    

def on_stop_request(agent, data):
    agent.stop()
    
    
@asyncio.coroutine
def on_processing_rate_request(agent, data):
    agent.send({
        'type': 'type',
        'event': 'agent-processing-rate',
        'target': data['who'],
        'who': agent.tag_slug,
        'processing_rate': '%1.2f' % agent.processing_rate(),
    })
    
    
CALLBACKS = {
    'open': on_open,
    'close': on_close,
    'error': on_error,
    'stop-request': on_stop_request,
    'processing-rate-request': on_processing_rate_request,
}