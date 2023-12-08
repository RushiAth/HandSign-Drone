import asyncio
import websockets
from functools import partial
from time import time


class TelloVideoWebsocketServer:
    def __init__(self, port):
        self._port = port
        self._clients = set()

    async def run(self):
        self._loop = asyncio.get_event_loop()
        server = await websockets.serve(self._handle_websocket, port=self._port)
        await server.wait_closed()

    async def _handle_websocket(self, websocket, request_path):
        client_id = len(self._clients)
        print(f'[server - websocket] client #{client_id} OPEN') 
        try:
            self._clients.add(websocket)

            await asyncio.sleep(60)

            # async for message in websocket:
            #     await self._handle_message(websocket, message)
        finally:
            self._clients.discard(websocket)
            print(f'[server - websocket] client #{client_id} CLOSE') 

    async def _handle_message(self, websocket, message):
        pass

    def broadcast_frame(self, frame):
        asyncio.run_coroutine_threadsafe(self._broadcast_frame(frame), self._loop)

    _broadcasting_frame = None

    async def _broadcast_frame(self, frame):
        if self._clients:
            print(f'[server - broadcast frame {frame.number}] START, clients {len(self._clients)}')

            if self._broadcasting_frame:
                print(f'[server - broadcast frame {frame.number}] ABORT, still broadcasting {self._broadcasting_frame.number}')
                return

            self._broadcasting_frame = frame

            chunks = self._make_chunks(frame.data) 
            print(f'[server - broadcast frame {frame.number}] {len(frame.data)} bytes -> {len(chunks)} chunks') 
            for client in self._clients:
                print(f'[server - broadcast frame {frame.number}] SEND') 
                try:
                    t0 = time()
                    for c in chunks:
                        await client.send(c)
                    dt = time() - t0
                    print(f'[server - broadcast frame {frame.number}] send took {dt:0.4f}s')
                except Exception as e:
                    print(f'[server - broadcast frame {frame.number}] ERROR sending: {e}')

            print(f'[server - broadcast frame {frame.number}] END') 
        self._broadcasting_frame = None

    def _make_chunks(self, data, chunk_size=65536):
        n = len(data)
        i = 0
        chunks = []
        while i < n:
            chunks.append(data[i:i+chunk_size])
            i += chunk_size
        return chunks
