def on_open(agent, data):
    agent.send({
        'type': 'type',
        'event': 'agent-update',
        'target-groups': ['monitor'],
        'who': agent.tag_slug,
        'camera_running': 1,
    })


def on_frame(agent, data):
    pass


def on_plate(agent, data):
    pass
    

def on_close(agent, data):
    agent.send({
        'type': 'type',
        'event': 'agent-update',
        'target-groups': ['monitor'],
        'who': agent.tag_slug,
        'camera_running': 0,
    })


def on_error(agent, data):
    pass


CALLBACKS = {
    'open': on_open,
    'frame': on_frame,
    'plate': on_plate,
    'close': on_close,
    'error': on_error,
}