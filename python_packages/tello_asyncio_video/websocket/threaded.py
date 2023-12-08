import asyncio
import threading
from ..app import run_tello_video_app
from .server import TelloVideoWebsocketServer


DEFAULT_SERVER_PORT = 22222

_current_frame = None

def run_tello_video_app_websocket(fly, 
                                  process_frame=None, 
                                  on_frame_decoded=None, 
                                  drone=None, 
                                  wait_for_wifi=True,
                                  extra_tasks=None,
                                  server_port=DEFAULT_SERVER_PORT):

    frame_available = threading.Condition()

    server = TelloVideoWebsocketServer(server_port)
    def run_server():
        print('[server] START')
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(server.run())
        print('[server] END')

    server_thread = threading.Thread(target=run_server)
    server_thread.start()

    def handle_frame(frame):
        server.broadcast_frame(frame)

    run_tello_video_app(fly, 
                        process_frame=process_frame, 
                        on_frame_decoded=handle_frame,
                        drone=drone,
                        wait_for_wifi=wait_for_wifi,
                        extra_tasks=extra_tasks)