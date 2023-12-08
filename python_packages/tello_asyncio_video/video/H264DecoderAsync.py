import asyncio
from inspect import iscoroutinefunction
from time import time

try:
    from h264decoder import H264Decoder
except ImportError:
    print('ImportError - failed to import h264decoder.H264Decoder')
    print('h264decoder requires manual building and installation - please see https://github.com/robagar/h264decoder for installation instructions')

from .types import DecodedFrame


class H264DecoderAsync:
    '''
    Decodes a stream of h.264 encoded video frames, making them available for
    analysis.
    '''

    def __init__(self):
        self._decoder = H264Decoder()
        self._frame_available = asyncio.Condition()
        self._decoded_frame = None
        self._frame_number = 0

    async def decode_frames(self, video_chunk_stream, on_frame_decoded=None):
        '''
        Begin decoding video frames.

        :param video_chunk_stream: The video data stream 
        :type video_chunk_stream: Asynchronous iterator of h.264 frame chunks
        :param on_frame_decoded: Optional callback called  for each successfully decoded frame. Must be fast!
        :type on_frame_decoded: Awaitable or plain function taking :class:`jetson_tello.types.DecodedFrame` 
        '''
        async for frame_chunk in video_chunk_stream:
            for (frame_data, width, height, row_size) in self._decoder.decode(frame_chunk):
                async with self._frame_available:
                    self._frame_number += 1
                    print(f'[H264DecoderAsync] frame {self._frame_number} {width}x{height}')
                    # print(f'[H264DecoderAsync] frame {self._frame_number} {dt:0.4f}s')
                    self._decoded_frame = DecodedFrame(self._frame_number, width, height, frame_data)
                    if on_frame_decoded:
                        if iscoroutinefunction(on_frame_decoded):
                            await on_frame_decoded(self._decoded_frame)
                        else:
                            on_frame_decoded(self._decoded_frame)
                    self._frame_available.notify_all()

    @property
    async def decoded_frame(self):
        '''
        The most recently decoded frame.
        :rtype: :class:`jetson_tello.types.DecodedFrame`
        '''
        async with self._frame_available:
            print(f'[H264DecoderAsync] get decoded frame, waiting...')
            await self._frame_available.wait()
            frame = self._decoded_frame
            print(f'[H264DecoderAsync] decoded frame {frame.number}')
            return frame
