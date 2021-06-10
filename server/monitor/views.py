import cv2, json, numpy, os, threading, time, logging
from django.shortcuts import render, redirect, get_object_or_404
from channels.layers import get_channel_layer
from django.conf import settings
from django.http import HttpResponse, JsonResponse, StreamingHttpResponse, HttpResponseServerError
from django.template import loader
from django.views.decorators import gzip
from queue import Queue, Full, Empty
from django.contrib import messages
from .models import Layer, ControlPoint, Camera, DetectedLicensePlate
from .forms import LayerForm, ControlpointForm, CameraForm


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
    return render(request, "monitor/index.html")

def monitor(request):
    context = {
        'layer_list': Layer.objects.all(),
        'controlpoint_list': ControlPoint.objects.all(),
        'camera_list': Camera.objects.all().order_by('controlpoint', 'direction', 'tag_slug'),
    }
    return render(request, "monitor/monitor.html", context)


def placaListView(request):
    
    placa_list = Camera.objects.raw('SELECT layer.name as layer, controlpoint.name, controlpoint.address, controlpoint.latitude, controlpoint.longitude, camera.tag_slug, camera.direction, camera.ID, placa.license_plate, placa.detection_date ' 
                            'FROM monitor_layer as layer, monitor_controlpoint as controlpoint, monitor_camera as camera, monitor_detectedlicenseplate as placa ' 
                            'WHERE layer.id = controlpoint.layer_id and controlpoint.id = camera.controlpoint_id and camera.id = placa.camera_id')
    
    context = {'placa_list': placa_list}
    return render(request, "monitor/placaList.html", context)


def admin(request):
    context = {
        'layer_list': Layer.objects.all(),
        'controlpoint_list': ControlPoint.objects.all(),
        'camera_list': Camera.objects.all().order_by('controlpoint', 'direction', 'tag_slug'),
    }
    return render(request, "monitor/admin.html", context)

def add_layer(request):
    if request.method == "POST":
        form = LayerForm(request.POST)
        if form.is_valid():
            layer = form.save(commit=False)
            layer.save()
            return redirect('/administracao')
        else:
            return redirect('/erro')
    else:    
        form = LayerForm()
        return render(request, "monitor/add_layer.html", {'form': form})


def add_controlpoint(request):
    if request.method == "POST":
        form = ControlpointForm(request.POST)
        if form.is_valid():
            controlpoint = form.save(commit=False)
            controlpoint.save()
            return redirect('/administracao')
        else:
            return redirect('/erro')
    else:    
        form = ControlpointForm()
        return render(request, "monitor/add_controlpoint.html", {'form': form})

def add_camera(request):
    if request.method == "POST":
        form = CameraForm(request.POST)
        if form.is_valid():
            camera = form.save(commit=False)
            camera.save()
            return redirect('/administracao')
        else:
            return redirect('/erro')
    else:    
        form = CameraForm()
        return render(request, "monitor/add_camera.html", {'form': form})

def update_layer(request, id):
    layer = get_object_or_404(Layer, pk=id)
    form = LayerForm(instance=layer)
    if request.method == "POST":
        form = LayerForm(request.POST, instance=layer)
        if form.is_valid():
            layer.save()
            return redirect('/administracao') 
        else:
            return redirect('/erro')
    else:    
        return render(request, "monitor/update_layer.html", {'form': form, 'layer': layer})

def update_controlpoint(request, id):
    controlpoint = get_object_or_404(ControlPoint, pk=id)
    form = ControlpointForm(instance=controlpoint)
    if request.method == "POST":
        form = ControlpointForm(request.POST, instance=controlpoint)
        if form.is_valid():
            controlpoint.save()
            return redirect('/administracao') 
        else:
            return redirect('/erro')
    else:    
        return render(request, "monitor/update_controlpoint.html", {'form': form, 'layer': controlpoint})

def update_camera(request, id):
    camera = get_object_or_404(Camera, pk=id)
    form = CameraForm(instance=camera)
    if request.method == "POST":
        form = CameraForm(request.POST, instance=camera)
        if form.is_valid():
            camera.save()
            return redirect('/administracao') 
        else:
            return redirect('/erro')
    else:    
        return render(request, "monitor/update_camera.html", {'form': form, 'layer': camera})

def delete_layer(request, id):
    layer = get_object_or_404(Layer, pk=id)
    if request.method == "POST":
        layer.delete()
        messages.info(request, 'Layer excluído com sucesso')
        return redirect('/administracao')
    else:
        '''
        layer_list = Layer.objects.filter(pk=id)
        lista = DetectedLicensePlate.objects.filter(camera__controlpoint__layer__in=layer_list)
        logger.info(f'=====> {lista}')
        '''
        controlpoint_list = ControlPoint.objects.filter(layer=layer)
        camera_list = Camera.objects.filter(controlpoint__in=controlpoint_list)
        placa_list = DetectedLicensePlate.objects.filter(camera__in=camera_list)

        context = {
            'layer': layer,
            'controlpoint_list': controlpoint_list,
            'camera_list': camera_list,
            'placa_list': placa_list
        }
        return render(request, "monitor/delete_layer.html", context)

    
def delete_controlpoint(request, id):
    controlpoint = get_object_or_404(ControlPoint, pk=id)
    if request.method == "POST":
        controlpoint.delete()
        messages.info(request, 'Ponto de controle excluído com sucesso')
        return redirect('/administracao')
    else:
        camera_list = Camera.objects.filter(controlpoint=controlpoint)
        placa_list = DetectedLicensePlate.objects.filter(camera__in=camera_list)

        context = {
            'controlpoint': controlpoint,
            'camera_list': camera_list,
            'placa_list': placa_list
        }
        return render(request, "monitor/delete_controlpoint.html", context)

def delete_camera(request, id):
    camera = get_object_or_404(Camera, pk=id)
    if request.method == "POST":
        camera.delete()
        messages.info(request, 'Câmera excluído com sucesso')
        return redirect('/administracao')
    else:
        placa_list = DetectedLicensePlate.objects.filter(camera=camera)

        context = {
            'camera': camera,
            'placa_list': placa_list
        }
        return render(request, "monitor/delete_camera.html", context)

def erro(request):
    return render(request, "monitor/erro.html")


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
