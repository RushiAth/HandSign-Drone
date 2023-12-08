import asyncio
from time import time
from threading import Thread, Condition

from tello_asyncio import Tello

from ..video import H264DecoderAsync
from .server import run_server

DEFAULT_SERVER_PORT=22222

frame = None

def run_tello_video_app_with_mjpegstream(fly, on_frame_decoded, drone=None, wait_for_wifi=True, server_port=DEFAULT_SERVER_PORT):
    '''
    Not ready for use - basically works but with terrible lag
    '''
    frame_available = Condition()

    def _on_frame_decoded(f):
        global frame
        with frame_available:
            frame = f
            frame_available.notify()
            on_frame_decoded(frame)

    def fly_drone(fly, on_frame_decoded, drone, wait_for_wifi):    
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        if not drone:
            drone = Tello()

        async def main():
            print('[main] START')
            if wait_for_wifi:
                await drone.wifi_wait_for_network()
        
            await drone.connect()

            # begin video stream
            await drone.start_video()
            t0 = time()

            decoder = H264DecoderAsync()

            async def watch_video():
                ''' 
                Receive and decode all frames from the drone. Decoding each frame
                often relies on previous frame data, so all frames must be decoded.
                '''
                print('[watch video] START')
                await decoder.decode_frames(drone.video_chunk_stream, _on_frame_decoded)
                print('[watch video] END')


            try:
                # run all together until `fly` is complete
                finished, unfinished = await asyncio.wait(
                    [fly(drone), watch_video()], 
                    return_when=asyncio.FIRST_COMPLETED)

                # clean up
                for task in unfinished:
                    task.cancel()
                await asyncio.wait(unfinished)
            except Exception as e:
                print(f'Exception caught: {e}')
            finally:
                await drone.stop_video()
                await drone.disconnect()

        # run asyncio event loop
        loop.run_until_complete(main())
        print('[main] END')
   

    fly_drone_thread = Thread(target=fly_drone, daemon=True, args=(fly, on_frame_decoded, drone, wait_for_wifi))
    fly_drone_thread.start()

    run_server(frame_available, lambda: frame, server_port)
