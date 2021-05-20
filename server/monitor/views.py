import cv2, json, numpy, os, threading, time, logging
from django.shortcuts import render
#from channels import Group
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


def index(request):
    #logger.info(f'=====> /views/index {request}')
    context = {
        'layer_list': Layer.objects.all(),
        'controlpoint_list': ControlPoint.objects.all(),
        'camera_list': Camera.objects.all().order_by('controlpoint', 'direction', 'tag_slug'),
    }
    return render(request, "monitor/index.html", context)
    #template = loader.get_template('monitor/index.html')
    #return HttpResponse(template.render(context, request))

def test(request):
    return render(request, "monitor/test.html", context={'text': 'Hello World'})


def rtsp_panel(request, controlpoint_id, monitor_id):
    logger.info(f'=====> /views/rtsp_panel {request, controlpoint_id, monitor_id}')
    context = {
        'monitor_id': monitor_id,
        'controlpoint': ControlPoint.objects.get(pk=controlpoint_id),
        'camera_list': Camera.objects.filter(controlpoint=controlpoint_id).order_by('direction', 'tag_slug'),
    }
    template = loader.get_template('monitor/rtsp-panel.html')
    return HttpResponse(template.render(context, request))



def agent_start(request, tag_slug):
    try:
        #logger.info(f'=====> /views/agent_start {request, tag_slug}')
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


def agent_stop(request, tag_slug):
    logger.info(f'=====> /views/agent_stop {request, tag_slug}')
    Group('agent').send({
        'text': json.dumps({
            'type': 'stop-request',
            'target': tag_slug,
        })
    })
    return JsonResponse({'success': True})
    
    
def agent_ask_processing_rate(request, tag_slug, monitor_id):
    logger.info(f'=====> /views/agent_ask_processing_rate {request, tag_slug, monitor_id}')
    Group('agent').send({
        'text': json.dumps({
            'type': 'processing-rate-request',
            'target': tag_slug,
            'who': monitor_id,
        })
    })
    return JsonResponse({'success': True})
    
    
living_streams = dict()


class _VideoStream(object):


    def __init__(self, tag_slug, monitor_id):
        self.TIMEOUT = 10  # in seconds
        self.QUEUE_SIZE = 60
        self._key = (tag_slug, monitor_id)
        self._frame_shape = (100, 100, 3)
        self._queue = Queue(maxsize=self.QUEUE_SIZE)
        threading.Thread(target=self._update, args=(Camera.objects.get(tag_slug=tag_slug).rtsp_url, ), daemon=True).start()


    def _update(self, video_path):
        video = cv2.VideoCapture(video_path)
        try:
            keep_running, frame = video.read()
            living_streams[self._key] = time.time()
            try:
                while keep_running and (time.time() - living_streams[self._key]) <= self.TIMEOUT:
                    frame = cv2.resize(frame, None, fx=0.25, fy=0.25, interpolation=cv2.INTER_CUBIC);
                    self._frame_shape = frame.shape
                    keep_running, jpeg = cv2.imencode('.jpg', frame)
                    if keep_running:
                        try: 
                            self._queue.put(jpeg.tostring(), timeout=self.TIMEOUT)
                        except Full:
                            keep_running = False
                        keep_running, frame = video.read()
            finally:
                del living_streams[self._key]                
        finally:
            video.release()

            
    def _make_no_signal_frame(self):
        text = 'No signal';
        font_face = cv2.FONT_HERSHEY_PLAIN;
        font_scale = 1;
        thickness = 1;
    
        frame = numpy.zeros(self._frame_shape, numpy.uint8)
        text_size, _ = cv2.getTextSize(text, font_face, font_scale, thickness);
        cv2.putText(frame, text, (5, 5 + text_size[1]), font_face, font_scale, (255, 255, 255), thickness)
    
        return cv2.imencode('.jpg', frame)[1].tostring()


    def get_frame(self):
        try:
            return True, self._queue.get(timeout=self.TIMEOUT)
        except Empty:
            return False, self._make_no_signal_frame()


def _stream_gen(video):
    success = True
    while success:
        success, jpeg = video.get_frame()
        yield b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + jpeg + b'\r\n\r\n'


@gzip.gzip_page
def camera_stream_open(request, tag_slug, monitor_id):
    try:
        response = StreamingHttpResponse(_stream_gen(_VideoStream(tag_slug, monitor_id)), content_type='multipart/x-mixed-replace;boundary=frame')
        return response 
    except HttpResponseServerError as error:
        return error
        
        
def camera_stream_keep_alive(request, tag_slug, monitor_id):
    key = (tag_slug, monitor_id)
    if key in living_streams: 
        living_streams[key] = time.time()
        return JsonResponse({'success': True})
    else:
        return JsonResponse({'success': False})