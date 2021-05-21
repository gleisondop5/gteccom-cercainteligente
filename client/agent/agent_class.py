import asyncio, cv2, numpy, json, logging, logging.config, openalpr, threading
import errno, hashlib, psycopg2, random, string, time, uuid, websockets, zipfile
from datetime import datetime
from functools import partial
from glob import glob
from os import makedirs, path, rename, remove
from queue import Queue

from . import communication, processing


class Agent:


    STATUS_STOPPED = 0
    STATUS_WEBSOCKET_RUNNING = 1
    STATUS_CAMERA_RUNNING = 2


    def __init__(self, tag_slug):
        logging.config.fileConfig(path.join(path.dirname(path.abspath(__file__)), 'config', 'logging.conf'))

        self.tag_slug = tag_slug
        self.logger = logging.getLogger('agent')
        
        self._local_storage_lock = threading.Lock()
        self._local_storage_dir = path.join(path.expanduser('~'), 'agent-storage', 'local', tag_slug)
        try:
            makedirs(self._local_storage_dir)
        except OSError as error:
            if error.errno != errno.EEXIST: raise

        self._final_storage_dir = path.join(path.expanduser('~'), 'agent-storage', 'final')
        try:
            makedirs(self._final_storage_dir)
        except OSError as error:
            if error.errno != errno.EEXIST: raise

        self._communication_event_loop = None
        
        self._processing_rate_lock = threading.Lock()
        self._processing_counter = 0
        self._processing_counter_start = None
        self._processing_rate = 0.
        
        self._ws = None
        self._stream = None
        self._keep_running = False
        
        self.logger.info('%s\tinit' % self.tag_slug)


    def __del__(self):
        self.logger.info('%s\tdel' % self.tag_slug)


    @asyncio.coroutine
    def _communication_loop(self, ws_uri_mask):
        self.logger.debug('%s\tcommunication loop - begin' % self.tag_slug)
        try:
            open_callback = communication.CALLBACKS.get('open')
            error_callback = communication.CALLBACKS.get('error')
            close_callback = communication.CALLBACKS.get('close')
    
            while self._keep_running:
                try:
                    self.logger.info('%s\twebsocket - connecting...' % self.tag_slug)
                    self._ws = yield from websockets.connect(ws_uri_mask % ((self.status() & Agent.STATUS_CAMERA_RUNNING) == Agent.STATUS_CAMERA_RUNNING))
                    if self._ws.closed: raise Exception('Error connecting websocket')
                    try:
                        self.logger.info('%s\twebsocket - opened' % self.tag_slug)
                        if open_callback is not None: yield from open_callback(self, {})
                        while self._keep_running and not self._ws.closed:
                            msg = yield from self._ws.recv()
                            #self.logger.debug('\tmsg = %s' % msg)
                            data = json.loads(msg)
                            #self.logger.debug('\tdata = %s' % data)
                            payload = data['payload']
                            self.logger.debug('\tpayload = %s' % payload)
                            callback = communication.CALLBACKS.get(payload['event'])
                            self.logger.debug('\tcallback = %s' % callback)
                            if callback is not None and payload.get('message', self.tag_slug) == self.tag_slug: yield from callback(self, payload)
                        self.logger.info('%s\twebsocket - closed' % self.tag_slug)
                    finally:
                        if close_callback is not None: yield from close_callback(self, {})
                        yield from self._ws.close()
                except Exception as error:
                    self.logger.error('%s\twebsocket - exception handler, loop still running: "%s"' % (self.tag_slug, str(error)))
                    if error_callback is not None: yield from error_callback(self, {'error': error})
                    yield from asyncio.sleep(10)
        except:
            self.logger.exception('%s\tcommunication loop - end by exception' % self.tag_slug)
            raise
        self.logger.debug('%s\tcommunication loop - end' % self.tag_slug)
                

    def _run_communication(self, ws_uri_mask):
        self.logger.debug('%s\tcommunication thread - begin' % self.tag_slug)
        try:
            self._communication_event_loop = asyncio.new_event_loop()
            try:
                asyncio.set_event_loop(self._communication_event_loop)
                self._communication_event_loop.run_until_complete(self._communication_loop(ws_uri_mask))
            finally:
                self._communication_event_loop.close()
        except:
            self.logger.exception('%s\tcommunication thread - end by exception' % self.tag_slug)
            raise
        self.logger.debug('%s\tcommunication thread - end' % self.tag_slug)

                
    def _run_frame_worker(self, index, frame_queue, storage_queue, frame_callback):
        self.logger.debug('%s\tframe worker #%d - begin' % (self.tag_slug, index))
        try:
            alpr = openalpr.Alpr('br', path.join(path.dirname(path.abspath(__file__)), 'config', 'openalpr.conf'), 'openalpr/runtime_data/')
            if not alpr.is_loaded(): raise Exception('Error loading OpenALPR')
            try:
                alpr.set_top_n(10)
                frame, when = frame_queue.get()
                while frame is not None:
                    if frame_callback is not None: frame_callback(self, {'frame': frame, 'when': when})
                    for result in alpr.recognize_ndarray(frame)['results']:
                        coords = result['coordinates']
                        x, y = [point['x'] for point in coords], [point['y'] for point in coords]
                        storage_queue.put({
                            'info': {
                                'plate': result['plate'],
                                'confidence': result['confidence'],
                                'candidates': [{'plate': candidate['plate'], 'confidence': candidate['confidence']} for candidate in result['candidates']],
                                'when': when,
                                'camera': {
                                    'tag_slug': self.tag_slug,
                                },
                            },
                            'frame': frame,
                            'roi': frame[numpy.amin(y):numpy.amax(y), numpy.amin(x):numpy.amax(x), :],
                        })
                    with self._processing_rate_lock:
                        self._processing_counter += 1
                    frame_queue.task_done()
                    frame, when = frame_queue.get()
                frame_queue.task_done()
            finally:
                alpr.unload()
        except:
            self.logger.exception('%s\tframe worker #%d - end by exception' % (self.tag_slug, index))
            raise            
        self.logger.debug('%s\tframe worker #%d - end' % (self.tag_slug, index))
        

    def _run_local_storage_worker(self, index, storage_queue, plate_callback, error_callback):
        PASSWORD_CHARS = string.ascii_letters + string.digits
        PASSWORD_SIZE = 8
        self.logger.debug('%s\tlocal storage worker #%d - begin' % (self.tag_slug, index))
        try:
            data = storage_queue.get()
            while data is not None:
                if plate_callback is not None: plate_callback(self, data)
                try:
                    success, png = cv2.imencode('.png', data['roi'])
                    if not success: raise Exception('Error converting to PNG')
    
                    info = data['info']
                    filename = str(uuid.uuid4()) + '.zip'
                    password = ''.join(random.choice(PASSWORD_CHARS) for _ in range(PASSWORD_SIZE))
                    
                    with zipfile.ZipFile(path.join(self._local_storage_dir, filename), mode='w', compression=zipfile.ZIP_DEFLATED) as zf:
                        zf.writestr('info.json', json.dumps(info))
                        zf.writestr('roi.png', png.tostring())
                    
                    with open(path.join(self._local_storage_dir, filename), mode='rb') as fp:
                        md5sum = hashlib.md5()
                        for buf in iter(partial(fp.read, 128), b''):
                            md5sum.update(buf)
    
                    with self._local_storage_lock:
                        with open(path.join(self._local_storage_dir, filename + '.json'), 'w') as fp:
                            json.dump({
                                'who': self.tag_slug,
                                'when': info['when'],
                                'plate': info['plate'],
                                'filename': filename,
                                'password': password,
                                'md5sum': md5sum.hexdigest(),
                            }, fp)
                except Exception as error:
                    self.logger.error('%s\tlocal storage worker #%d - exception handler, loop still running: "%s"' % (self.tag_slug, index, str(error)))
                    if error_callback is not None: error_callback(self, {'error': error})
                finally:
                    storage_queue.task_done()
                data = storage_queue.get()
            storage_queue.task_done()
        except:
            self.logger.exception('%s\tlocal storage worker #%d - end by exception' % (self.tag_slug, index))
            raise            
        self.logger.debug('%s\tlocal storage worker #%d - end' % (self.tag_slug, index))
        
        
    def _run_final_storage_worker(self, database_uri, error_callback):
        self.logger.debug('%s\tfinal storage worker - begin' % (self.tag_slug, ))
        try:
            while self._keep_running:
                try:
                    with psycopg2.connect(database_uri) as conn:
                        with conn.cursor() as cur:
                            while self._keep_running:
                                files = glob(path.join(self._local_storage_dir, '*.json'))
                                if len(files) == 0:
                                    time.sleep(1)
                                    continue
                                
                                with self._local_storage_lock:
                                    json_filename = path.basename(files[0])
    
                                with open(path.join(self._local_storage_dir, json_filename), 'r') as fp:
                                    data = json.load(fp)
                                
                                cur.execute(
                                    'INSERT INTO monitor_detectedlicenseplate (detection_date, license_plate, data_filename, data_password, data_md5, camera_id) ' \
                                    'SELECT %s, %s, %s, %s, %s, monitor_camera.id FROM monitor_camera WHERE monitor_camera.tag_slug = %s',
                                    (data['when'], data['plate'], data['filename'], data['password'], data['md5sum'], data['who'])
                                )
                                conn.commit()
                                
                                rename(path.join(self._local_storage_dir, data['filename']), path.join(self._final_storage_dir, data['filename']))
                                remove(path.join(self._local_storage_dir, json_filename))
                except Exception as error:
                    self.logger.error('%s\tfinal storage worker - exception handler, loop still running: "%s"' % (self.tag_slug, str(error)))
                    if error_callback is not None: error_callback(self, {'error': error})
                    time.sleep(10)
        except:
            self.logger.exception('%s\tfinal storage worker - end by exception' % (self.tag_slug, ))
            raise            
        self.logger.debug('%s\tfinal storage worker - end' % (self.tag_slug, ))
        
        
    def _run_processing(self, video_path, database_uri, num_frame_workers, num_local_storage_workers, frame_queue_size, storage_queue_size):
        self.logger.debug('%s\tprocessing thread - begin' % self.tag_slug)
        try:
            open_callback = processing.CALLBACKS.get('open')
            frame_callback = processing.CALLBACKS.get('frame')
            plate_callback = processing.CALLBACKS.get('plate')
            close_callback = processing.CALLBACKS.get('close')
            error_callback = processing.CALLBACKS.get('error')
            
            frame_queue = Queue(maxsize=frame_queue_size)
            storage_queue = Queue(maxsize=storage_queue_size)
    
            frame_workers = [threading.Thread(target=self._run_frame_worker, args=(index, frame_queue, storage_queue, frame_callback, ), daemon=True) for index in range(num_frame_workers)]
            for worker in frame_workers: worker.start()
                
            local_storage_workers = [threading.Thread(target=self._run_local_storage_worker, args=(index, storage_queue, plate_callback, error_callback, ), daemon=True) for index in range(num_local_storage_workers)]
            for worker in local_storage_workers: worker.start()

            final_storage_worker = threading.Thread(target=self._run_final_storage_worker, args=(database_uri, error_callback, ), daemon=True)
            final_storage_worker.start()
                
            while self._keep_running:
                try:
                    self.logger.info('%s\tstream - connecting...' % self.tag_slug)
                    self._stream = cv2.VideoCapture(video_path)
                    if not self._stream.isOpened(): raise Exception('Error opening camera')
                    try:
                        self.logger.info('%s\tstream - opened' % self.tag_slug)
                        if open_callback is not None: open_callback(self, {})
                        while self._keep_running and self._stream.isOpened():
                            grabbed, frame = self._stream.read()
                            if not grabbed: break
                            when = datetime.now().isoformat(sep=' ')
                            frame_queue.put((frame, when))
                        self.logger.info('%s\tstream - closed' % self.tag_slug)
                    finally:
                        if close_callback is not None: close_callback(self, {})
                        self._stream.release()
                except Exception as error:
                    self.logger.error('%s\tstream - exception handler, loop still running: "%s"' % (self.tag_slug, str(error)))
                    if error_callback is not None: error_callback(self, {'error': error})
                    time.sleep(10)
    
            for _ in range(num_frame_workers): frame_queue.put((None, None))
            frame_queue.join()
            
            for _ in range(num_local_storage_workers): storage_queue.put(None)
            storage_queue.join()
        except:
            self.logger.exception('%s\tprocessing thread - end by exception' % self.tag_slug)
            raise
        self.logger.debug('%s\tprocessing thread - end' % self.tag_slug)
        
    
    def _run_processing_rate(self):
        while self._keep_running:
            with self._processing_rate_lock:
                self._processing_counter = 0
                self._processing_counter_start = time.time()
            time.sleep(10)
            with self._processing_rate_lock:
                self._processing_rate = self._processing_counter / (time.time() - self._processing_counter_start) 
        with self._processing_rate_lock:
            self._processing_counter = 0
            self._processing_counter_start = None
            self._processing_rate = 0.
    
    
    def status(self):
        result = Agent.STATUS_STOPPED
        if self._ws is not None and not self._ws.closed:
            result |= Agent.STATUS_WEBSOCKET_RUNNING
        if self._stream is not None and self._stream.isOpened():
            result |= Agent.STATUS_CAMERA_RUNNING
        return result
        
        
    def processing_rate(self):
        with self._processing_rate_lock:
            result = self._processing_rate
        return result
        

    def run(self, monitor, video_path, database_host, database_port, database_name, database_user, database_password, num_frame_workers=2, num_local_storage_workers=2, frame_queue_size=120, storage_queue_size=120):
        ws_uri_mask = 'ws://%s/monitor/?group=agent&name=%s&camera_running=%%d' % (monitor, self.tag_slug)
        database_uri = 'postgresql://%s:%s@%s:%s/%s' % (database_user, database_password, database_host, database_port, database_name)
        database_uri_masked = 'postgresql://%s:********@%s:%s/%s' % (database_user, database_host, database_port, database_name)
        self.logger.info('%s\trun - begin [ws_uri_mask="%s", video_path="%s", database_uri="%s", num_frame_workers=%d, num_local_storage_workers=%d, frame_queue_size=%d, storage_queue_size=%d]' % (self.tag_slug, ws_uri_mask, video_path, database_uri_masked, num_frame_workers, num_local_storage_workers, frame_queue_size, storage_queue_size))
        self._keep_running = True
        try:
            if self.status() != Agent.STATUS_STOPPED: raise Exception('The agent is running already')
            running_threads = [
                threading.Thread(target=self._run_communication, args=(ws_uri_mask, ), daemon=True),
                threading.Thread(target=self._run_processing, args=(video_path, database_uri, num_frame_workers, num_local_storage_workers, frame_queue_size, storage_queue_size, ), daemon=True),
                threading.Thread(target=self._run_processing_rate, daemon=True),
            ]
            for thread in running_threads: thread.start()
            for thread in running_threads: thread.join()
        except:
            self.logger.exception('%s\trun - end by exception' % self.tag_slug)
            raise
        finally:
            self._keep_running = False
        self.logger.info('%s\trun - end' % self.tag_slug)


    def stop(self):
        self._keep_running = False
        
        
    def send(self, data):
        self.logger.debug('%s\tsend (%s) - begin' % (self.tag_slug, data['type']))
        try:
            if self._communication_event_loop is not None and not self._communication_event_loop.is_closed():
                def the_send_task():
                    self._communication_event_loop.create_task(self._ws.send(json.dumps(data)))
                self._communication_event_loop.call_soon_threadsafe(the_send_task)
        except:
            self.logger.exception('%s\tsend - end by exception' % self.tag_slug)
            raise
        self.logger.debug('%s\tsend (%s) - end' % (self.tag_slug, data['type']))