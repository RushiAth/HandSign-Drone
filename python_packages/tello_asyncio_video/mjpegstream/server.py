from http.server import HTTPServer, BaseHTTPRequestHandler
from io import BytesIO
from PIL import Image
from time import time


def run_server(frame_available, get_frame, port):

    t0 = time()

    class RequestHandler(BaseHTTPRequestHandler):
        # protocol_version = 'HTTP/1.1'

        def do_GET(self):
            print(f'[server] GET {self.path}')

            if self.path == '/':
                self.get_root()
            elif self.path == '/mjpegstream':
                self.get_mjpegstream()
            else:
                self.send_response(404)    

        def get_root(self):
            self.send_response(200)
            self.send_header("Content-type", "text/html")

            content = bytes('''<!doctype html>
<html lang=en>
  <head>
    <meta charset=utf-8>
    <title>Tello Async Video</title>
    <h1>Tello Async Video</h1>
    <img src="mjpegstream" />
  </head>
  <body>
    
  </body>
</html>
''', 'utf-8')

            content_length = len(content)
            self.send_header('Content-length', f'{content_length}')
            self.end_headers()
            self.wfile.write(content)


        BOUNDARY = 'mjpegstream_boundary'
        JPEG_QUALITY = 75

        def get_mjpegstream(self):
            self.send_response(200)
            # self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate, pre-check=0, post-check=0, max-age=0')
            # self.send_header('Pragma', 'no-cache')
            self.send_header('Content-Type', 'multipart/x-mixed-replace; boundary=' + self.BOUNDARY)
            # self.send_header('Connection', 'close')
            self.end_headers()

            while True:
                with frame_available:
                    print(f'[mjpegstream] waiting for frame...')
                    frame_available.wait()
                    frame = get_frame()
                    print(f'[mjpegstream] got frame {frame.number}') 

                    frame_t0 = time()
                    content = self.frame_to_jpeg_data(frame)
                    content_length = len(content)

                    dt = time() - frame_t0
                    print(f'[mjpegstream] frame {frame.number}: encoded jpeg after {dt:0.4f}s') 

                    self.wfile.write(f'\n--{self.BOUNDARY}'.encode('utf-8'))

                    # timestamp = time()
                    # self.send_header('X-Timestamp', f'{timestamp}')
                    self.send_header('Content-type', 'image/jpeg')
                    self.send_header('Content-length', f'{content_length}')
                    self.end_headers()

                    self.wfile.write(content)
     
                    dt = time() - frame_t0
                    print(f'[mjpegstream] frame {frame.number}: wrote output after {dt:0.4f}s') 
                    
                    
                    t = time()
                    frame_time = t - t0
                    dt = t - frame_t0
                    fps = 1.0/dt
                    print(f'[mjpegstream] FRAME {frame.number} at t={frame_time:0.4f} took {dt:0.4f}s ({fps:0.1f} fps)')


        def frame_to_jpeg_data(self, frame):
            image = Image.frombytes('RGB', (frame.width, frame.height), frame.data)
            buf = BytesIO()
            image.save(buf, 'jpeg', quality=self.JPEG_QUALITY)
            return buf.getvalue()                    

    
    server = HTTPServer(('', port), RequestHandler)
    server.serve_forever()

