from django.shortcuts import render
import cv2, json, numpy, os, threading, time, logging
from django.conf import settings
from django.http import HttpResponse, JsonResponse, StreamingHttpResponse, HttpResponseServerError
from django.template import loader
from django.views.decorators import gzip
from queue import Queue, Full, Empty
from .models import Layer, ControlPoint, Camera
from channels.layers import get_channel_layer
from django.template import Context, Template
from vidgear.gears import CamGear
#import random
import asyncio
#from vidgear.gears.asyncio import WebGear
#import uvicorn
from asgiref.sync import async_to_sync
from asgiref.sync import sync_to_async
from django_async_stream import AsyncStreamingHttpResponse
from starlette.responses import StreamingResponse







log_format = '%(asctime)s---%(levelname)s---%(filename)s---%(message)s'
logging.basicConfig(filename='tcc.log',
                    # w -> sobrescreve o arquivo a cada log
                    # a -> não sobrescreve o arquivo
                    filemode='w',
                    level=logging.DEBUG,
                    format=log_format)
logger = logging.getLogger('root')


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
    template = loader.get_template('monitor/rtsp-panel.html')
    return HttpResponse(template.render(context, request))



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


def agent_stop(request, tag_slug):
    Group('agent').send({
        'text': json.dumps({
            'type': 'stop-request',
            'target': tag_slug,
        })
    })
    return JsonResponse({'success': True})
    
    
def agent_ask_processing_rate(request, tag_slug, monitor_id):
    Group('agent').send({
        'text': json.dumps({
            'type': 'processing-rate-request',
            'target': tag_slug,
            'who': monitor_id,
        })
    })
    return JsonResponse({'success': True})
    
################################################################################################


   
living_streams = dict()


class _VideoStream(object):

    
    def __init__(self, tag_slug, monitor_id):
        #logger.info(f'=====> entrou em __init__')
        self.TIMEOUT = 10  # in seconds
        self.QUEUE_SIZE = 60
        self.tag_slug = tag_slug
        self._key = (tag_slug, monitor_id)
        self._frame_shape = (100, 100, 3)
        self._queue = Queue(maxsize=self.QUEUE_SIZE)
        #logger.info(f'=====> fim do __init__')
        #tread_frame = sync_to_async(threading.Thread(target=self._update, args=(Camera.objects.get(tag_slug=tag_slug).rtsp_url, ), daemon=True))
        #sync_to_async(tread_frame.start())
        #threading.Thread(target=self._update, args=(Camera.objects.get(tag_slug=tag_slug).rtsp_url, ), daemon=True).start()


    async def _update(self, video_path):
        #logger.info(f'=====> entrou em _update')
        self._queue = asyncio.Queue(maxsize=60)
        i=0
        video = cv2.VideoCapture(video_path)
        try:
            keep_running, frame = video.read()
            living_streams[self._key] = time.time()
            try:
                while keep_running and (time.time() - living_streams[self._key]) <= self.TIMEOUT:
                    frame = cv2.resize(frame, None, fx=0.25, fy=0.25, interpolation=cv2.INTER_CUBIC);
                    self._frame_shape = frame.shape
                    cv2.imwrite(str(i)+"novalampada.png", frame) 
                    i+=1
                    keep_running, jpeg = cv2.imencode('.jpg', frame)
                    if keep_running:
                        try: 
                            #logger.info(f'=====> insere na fila')
                            #asyncio.wait_for(self._queue.put(jpeg.tostring(), timeout=self.TIMEOUT))
                            await self._queue.put(jpeg.tostring())
                            #logger.info(f'=====> {self._queue.qsize()}')
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


    async def get_frame(self):
        #logger.info(f'=====> entrou em get_frame')
        await self.thread_atual()
        #logger.info(f'=====> passou por thread_atual')
        try:
            #return True, asyncio.wait_for(self._queue.get_nowait(timeout=self.TIMEOUT))
            #return True, asyncio.wait_for(await self._queue.get_nowait(timeout=self.TIMEOUT))
            #logger.info(f'=====> antes {self._queue.qsize()}')
            jpg = await self._queue.get()
            #logger.info(f'=====> depois {self._queue.qsize()}')
            return True, jpg
            #return True, await self._queue.get()
        #except asyncio.QueueEmpty:
        except Empty:
            #return True, self._make_no_signal_frame()
            return False, self._make_no_signal_frame()

    @sync_to_async
    def thread_atual(self):
        #logger.info(f'=====> entrou em thread_atual')
        tread_frame = threading.Thread(target= async_to_sync(self._update), args=(Camera.objects.get(tag_slug=self.tag_slug).rtsp_url, ), daemon=True)
        tread_frame.start()
        #logger.info(f'=====> iniciou a thread')


async def _stream_gen(video):
    success = True
    vet = []
    while success:
        #logger.info(f'=====> pegou o frame')
        success, jpeg = await video.get_frame()
        vet.append(jpeg)
        logger.info(f'=====> pegou o frame {len(vet)}')
        #logger.info(f'=====> pegou o frame {jpeg}')
        yield b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + jpeg + b'\r\n\r\n'
        #await asyncio.sleep(1)


#@gzip.gzip_page
#@sync_to_async
async def camera_stream_open(request, tag_slug, monitor_id):
    try:
        #logger.info(f'=====> antes de pegar os frames')
        #frames = [x async for x in _stream_gen(_VideoStream(tag_slug, monitor_id))]
        #logger.info(f'=====> pegou o frame {frames}')
        logger.info(f'=====> iniciou o pedido')
        obj_generator = async_to_sync([i async for i in _stream_gen(_VideoStream(tag_slug, monitor_id))])
        logger.info(f'=====>obj_generator')
        #for i in obj_generator:
        #    jpg = i
        response = StreamingHttpResponse(obj_generator, content_type='multipart/x-mixed-replace;boundary=frame')
        
        #response = StreamingHttpResponse(async_to_sync(_stream_gen(_VideoStream(tag_slug, monitor_id))), content_type='multipart/x-mixed-replace;boundary=frame')
        return response 

        #return AsyncStreamingHttpResponse(_stream_gen(_VideoStream(tag_slug, monitor_id)), content_type='multipart/x-mixed-replace;boundary=frame')
        #return StreamingResponse(_stream_gen(_VideoStream(tag_slug, monitor_id)), content_type='multipart/x-mixed-replace;boundary=frame')


    except HttpResponseServerError as error:
        return error
        
        
def camera_stream_keep_alive(request, tag_slug, monitor_id):
    key = (tag_slug, monitor_id)
    if key in living_streams: 
        living_streams[key] = time.time()
        return JsonResponse({'success': True})
    else:
        return JsonResponse({'success': True})




























































'''
_queue = Queue(maxsize=60)



def get_frame():
    options = {
        "CAP_PROP_FRAME_WIDTH": 320,
        "CAP_PROP_FRAME_HEIGHT": 240,
        "CAP_PROP_FPS": 60,
    }

    stream = CamGear(source=0, logging=True, **options).start()

    while True:

        frame = stream.read()
        logger.info(f'=====> {frame}')

        if frame is None:
            break

        jpeg = cv2.imencode('.jpg', frame)
        #_queue.put(jpeg.tostring(), timeout=10)
        #jpeg2 = jpeg.tostring()
        
        cv2.imshow("Output", frame)

        # check for 'q' key if pressed
        key = cv2.waitKey(1) & 0xFF
        if key == ord("q"):
            break
        

    # close output window
    cv2.destroyAllWindows()

    # safely close video stream
    stream.stop()

    return jpeg2



def _stream_gen():
    success = True
    while success:
        jpeg = get_frame()
        yield b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + jpeg + b'\r\n\r\n'
    

#@gzip.gzip_page
def camera_stream_open(request, tag_slug, monitor_id):
    logger.info(f'=====> stream')
    response = StreamingHttpResponse(_stream_gen(), content_type='multipart/x-mixed-replace;boundary=frame')
    return response

    
def camera_stream_keep_alive(request, tag_slug, monitor_id):
    return JsonResponse({'success': True})

'''































































































'''

FUNCIONA PARCIALMENTE


def get_frame():

    options = {"frame_size_reduction": 40, "frame_jpeg_quality": 80, "frame_jpeg_optimize": True, "frame_jpeg_progressive": False}

    #initialize WebGear app with suitable video file (for e.g `foo.mp4`) 
    web = WebGear(source = "rtsp://192.168.1.11:8080/h264_ulaw.sdp", logging = True, **options)

    #run this app on Uvicorn server at address http://0.0.0.0:8000/
    uvicorn.run(web(), host="127.0.0.1", port=8085)

   
def _stream_gen():
    success = True
    while success:
        #logger.info(f'=====> {self._queue.qsize()}')
        jpeg = get_frame()
        yield b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + jpeg + b'\r\n\r\n'
    

#@gzip.gzip_page
def camera_stream_open(request, tag_slug, monitor_id):
    logger.info(f'=====> stream')
    response = StreamingHttpResponse(get_frame(), content_type='multipart/x-mixed-replace;boundary=frame')
    return response

    
def camera_stream_keep_alive(request, tag_slug, monitor_id):
    return JsonResponse({'success': True})
    

'''



























































'''
 
living_streams = dict()



class _VideoStream(object):


    def __init__(self, tag_slug, monitor_id):
        logger.info(f'=====> Entrou no init')
        self.TIMEOUT = 10  # in seconds
        self.QUEUE_SIZE = 60
        self._key = (tag_slug, monitor_id)
        self._frame_shape = (100, 100, 3)
        self._queue = Queue(maxsize=self.QUEUE_SIZE)
        #logger.info(f'=====> Depois da Thread')
        logger.info(f'=====>{threading.current_thread().name}')
        threading.Thread(target=self._update, args=(Camera.objects.get(tag_slug=tag_slug).rtsp_url, ), daemon=True).start()


    def _update(self, video_path):
        #logger.info(f'=====> Entrou no update')
        video = cv2.VideoCapture(video_path)
        try:
            keep_running, frame = video.read()
            living_streams[self._key] = time.time()
            try:
                #logger.info(f'=====> Antes do while')
                while keep_running and (time.time() - living_streams[self._key]) <= self.TIMEOUT:
                    #logger.info(f'=====> Entrou no while')
                    frame = cv2.resize(frame, None, fx=0.25, fy=0.25, interpolation=cv2.INTER_CUBIC);
                    self._frame_shape = frame.shape
                    keep_running, jpeg = cv2.imencode('.jpg', frame)
                    if keep_running:
                        try: 
                            #logger.info(f'=====> {len(self._queue)}')
                            #logger.info(f'=====> Entrou no keep_running')
                            self._queue.put(jpeg.tostring(), timeout=self.TIMEOUT)
                            #logger.info(f'=====> passou no keep_running')
                            #logger.info(f'=====> {self._queue.qsize()}')
                        except Full:
                            logger.info(f'=====> except full')
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
            #logger.info(f'=====> {self._queue.qsize()}')
            return True, self._queue.get(timeout=self.TIMEOUT)
            #logger.info(f'=====> {self._queue.qsize()}')
        except Empty:
            logger.info(f'=====> no signal')
            return False, self._make_no_signal_frame()
            


def _stream_gen(video):
    success = True
    while success:
        #logger.info(f'=====> {self._queue.qsize()}')
        success, jpeg = video.get_frame()
        yield b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + jpeg + b'\r\n\r\n'


#@gzip.gzip_page
def camera_stream_open(request, tag_slug, monitor_id):
    try:
        logger.info(f'=====> stream')
        response = StreamingHttpResponse(_stream_gen(_VideoStream(tag_slug, monitor_id)), content_type='multipart/x-mixed-replace;boundary=frame')
        return response 
    except HttpResponseServerError as error:
        logger.info(f'=====> erro')
        return error
        
     
def camera_stream_keep_alive(request, tag_slug, monitor_id):
    pass
    
    key = (tag_slug, monitor_id)
    if key in living_streams: 
        living_streams[key] = time.time()
        return JsonResponse({'success': True})
    else:
        return JsonResponse({'success': False})
'''    




















'''

class _VideoStream(object):


    def __init__(self, tag_slug, monitor_id):
        logger.info(f'=====> Entrou no init')
        self.TIMEOUT = 10  # in seconds
        self.QUEUE_SIZE = 60 #tamanho da fila
        self._key = (tag_slug, monitor_id) # chave do dicionario living_streams
        self._frame_shape = (100, 100, 3)
        self._queue = []
        #self._queue = asyncio.Queue(maxsize=self.QUEUE_SIZE) #Construtor para uma fila FIFO
        #self._queue = Queue(maxsize=self.QUEUE_SIZE) #Construtor para uma fila FIFO
        #logger.info(f'=====> Antes da Thread')
        threading.Thread(target=self._update, args=(Camera.objects.get(tag_slug=tag_slug).rtsp_url, ), daemon=True, name='minha').start() #inicia a thread passando rtsp_url
        #logger.info(f'=====> Depois da Thread')
        logger.info(f'=====>{threading.current_thread().name}')

    def _update(self, video_path):
        logger.info(f'=====> Entrou no update')
        video = cv2.VideoCapture(video_path)
        logger.info(f'=====> Depois do CV2')
        try:
            keep_running, frame = video.read()
            living_streams[self._key] = time.time()
            try:
                logger.info(f'=====> Antes do while')
                while keep_running and (time.time() - living_streams[self._key]) <= self.TIMEOUT:
                    #logger.info(f'=====> Entrou no while')
                    frame = cv2.resize(frame, None, fx=0.25, fy=0.25, interpolation=cv2.INTER_CUBIC);
                    self._frame_shape = frame.shape
                    keep_running, jpeg = cv2.imencode('.jpg', frame)
                    if keep_running:
                        try: 
                            #logger.info(f'=====>antes add')
                            self._queue.append(jpeg.tostring())
                            #logger.info(f'=====>depois add')
                            #logger.info(f'=====>{type(jpeg.tostring())}')
                            
                            #self._queue.put_nowait(jpeg.tostring()) # coloque o item na fila 
                            #self._queue.put(jpeg.tostring(), timeout=self.TIMEOUT) # coloque o item na fila até o fim do TIMEOUT
                        except Full:
                            keep_running = False
                        keep_running, frame = video.read()
            finally:
                logger.info(f'=====>finally')
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
            frame_fila = []
            
            if len(self._queue) > 0:                
                frame_fila.append(self._queue[0])
                self._queue.remove(self._queue[0])
                logger.info(f'_lista {len(frame_fila)}')
                
                    
                
            
                return True, frame_fila[0]
            return True, self._make_no_signal_frame()
            #return True, self._queue.get(timeout=self.TIMEOUT) # remove o um item da fila. Se vazia levanta um except
        except Empty:
            
            return False, self._make_no_signal_frame()


def _stream_gen(video):
    success = True
    while success:
        success, jpeg = video.get_frame()
        yield b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + jpeg + b'\r\n\r\n'


@gzip.gzip_page
def camera_stream_open(request, tag_slug, monitor_id):
    response = StreamingHttpResponse(_stream_gen(_VideoStream(tag_slug, monitor_id)), content_type='multipart/x-mixed-replace;boundary=frame')

    response = StreamingHttpResponse(_stream_gen(_VideoStream(tag_slug, monitor_id)), content_type='multipart/x-mixed-replace;boundary=frame')
    return response

    try:
        response = StreamingHttpResponse(_stream_gen(_VideoStream(tag_slug, monitor_id)), content_type='multipart/x-mixed-replace;boundary=frame')
        return response 
    except HttpResponseServerError as e:
        return "aborted"
    

    #except HttpResponseServerError as error:
    #    return error
        
        
def camera_stream_keep_alive(request, tag_slug, monitor_id):
    key = (tag_slug, monitor_id)
    #logger.error(f'********>{key} {living_streams}')
    if key in living_streams: 
        living_streams[key] = time.time()
        return JsonResponse({'success': True})
    else:
        return JsonResponse({'success': False})
'''