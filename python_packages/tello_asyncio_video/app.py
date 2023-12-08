import asyncio

from tello_asyncio import Tello

from .video import H264DecoderAsync


def run_tello_video_app(fly, 
                        process_frame=None, 
                        on_frame_decoded=None, 
                        drone=None, 
                        wait_for_wifi=True,
                        extra_tasks=None):
    if not drone:
        drone = Tello()

    async def main():
        print('[main] START')
        if wait_for_wifi:
            await drone.wifi_wait_for_network()
    
        await drone.connect()

        # begin video stream
        await drone.start_video()

        decoder = H264DecoderAsync()

        async def watch_video():
            ''' 
            Receive and decode all frames from the drone. Decoding each frame
            often relies on previous frame data, so all frames must be decoded.
            '''
            try:
                print('[watch video] START')

                # decode all frames
                await decoder.decode_frames(drone.video_chunk_stream, on_frame_decoded)
            except Exception as e:
                print(f'[watch video] ERROR {e}')
            finally:
                print('[watch video] END')

        async def process_frames():
            ''' 
            Process frames when available without falling behind
            '''
            try:
                print('[process frames] START')
                while True:
                    # wait for next frame, skipping any that arrived during last iteration
                    frame = await decoder.decoded_frame

                    # call callback
                    if asyncio.iscoroutinefunction(process_frame):
                        await process_frame(frame)
                    else:
                        process_frame(frame)
            except Exception as e:
                print('[process frames] ERROR', e)
            finally:
                print('[process frames] END')

        try:
            # prepare tasks
            tasks = [
                asyncio.ensure_future(fly(drone)), 
                asyncio.ensure_future(watch_video())]

            if process_frame:
                tasks.append(asyncio.ensure_future(process_frames()))

            if extra_tasks:
                tasks.extend(extra_tasks)

            # run all together until `fly` is complete
            finished, unfinished = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)

            # clean up
            for task in unfinished:
                task.cancel()
            await asyncio.wait(unfinished)
        finally:
            await drone.stop_video()
            await drone.disconnect()

    # run asyncio event loop
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
    print('[main] END')
   

