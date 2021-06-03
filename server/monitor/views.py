import cv2, json, numpy, os, threading, time, logging
from django.shortcuts import render
from channels.layers import get_channel_layer
from django.conf import settings
from django.http import HttpResponse, JsonResponse, StreamingHttpResponse, HttpResponseServerError
from django.template import loader
from django.views.decorators import gzip
from queue import Queue, Full, Empty
from .models import Layer, ControlPoint, Camera


log_format = '%(asctime)s---%(levelname)s---%(filename)s---%(message)s'
logging.basicConfig(filename='tcc.log',
                    # w -> sobrescreve o arquivo a cada log
                    # a -> não sobrescreve o arquivo
                    filemode='w',
                    level=logging.DEBUG,
                    format=log_format)
logger = logging.getLogger('root')


video_streams = dict()

def test(request):
	return render(request, "monitor/test.html")


def index(request):
    context = {
        'layer_list': Layer.objects.all(),
        'controlpoint_list': ControlPoint.objects.all(),
        'camera_list': Camera.objects.all().order_by('controlpoint', 'direction', 'tag_slug'),
    }
    return render(request, "monitor/index.html", context)


def rtsp_panel(request, controlpoint_id, monitor_id):
    context = {
        'monitor_id': monitor_id,
        'controlpoint': ControlPoint.objects.get(pk=controlpoint_id),
        'camera_list': Camera.objects.filter(controlpoint=controlpoint_id).order_by('direction', 'tag_slug'),
    }
    return render(request, "monitor/rtsp-panel.html", context)


def agent_start(request, tag_slug):
    try:
        database = settings.DATABASES['default']
        camera = Camera.objects.get(tag_slug=tag_slug)
        command = 'nohup python3 -m gteccom-cercainteligente.client.agent --monitor "%s" --video "%s" --name "%s" --dbhost "%s" --dbport "%s" --dbname "%s" --dbuser "%s" --dbpwd "%s" > /dev/null 2>&1 &' % (
            request.get_host(),
            camera.rtsp_url,
            camera.tag_slug,
            database['HOST'], database['PORT'], database['NAME'], database['USER'], database['PASSWORD']
        )
        os.system('ssh %s@%s \'%s\'' % (camera.agent_user, camera.agent_server, command))
        return JsonResponse({'success': True})
    except Exception as error:
        return JsonResponse({'success': False, 'error': str(error)})


living_streams = dict()


class VideoCamera():
    def __init__(self):
        #self.video = cv2.VideoCapture("rtsp://192.168.1.7:8085/h264_ulaw.sdp")
        self.video = cv2.VideoCapture(0)

    def __del__(self):
        self.video.release()

    def get_frame(self):
        success,imgNp = self.video.read()
        resize = cv2.resize(imgNp, (640, 480), interpolation = cv2.INTER_LINEAR) 
        ret, jpeg = cv2.imencode('.jpg', resize)
        return jpeg.tobytes()

def _stream_gen(video):
    while True:
        frame = VideoCamera.get_frame(video)
        yield (b'--frame\r\n'b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n\r\n')


def camera_stream_open(request, tag_slug, monitor_id):
    return StreamingHttpResponse(_stream_gen(VideoCamera()), content_type='multipart/x-mixed-replace; boundary=frame')
        

def camera_stream_keep_alive(request, tag_slug, monitor_id):
    key = (tag_slug, monitor_id)
    if key in living_streams: 
        living_streams[key] = time.time()
        return JsonResponse({'success': True})
    else:
        return JsonResponse({'success': False})
