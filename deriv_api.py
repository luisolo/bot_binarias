# deriv_api.py

import asyncio
import websockets
import json

class DerivAPI:
    def __init__(self, api_token):
        self.api_token = api_token
        self.websocket = None

    async def connect(self):
        self.websocket = await websockets.connect("wss://ws.derivws.com/websockets/v3")
        await self.authorize()

    async def authorize(self):
        auth_msg = json.dumps({
            "authorize": self.api_token
        })
        await self.websocket.send(auth_msg)
        response = await self.websocket.recv()
        return json.loads(response)

    async def send_request(self, data):
        if self.websocket is None:
            await self.connect()
        await self.websocket.send(json.dumps(data))
        response = await self.websocket.recv()
        return json.loads(response)

    async def get_tick_stream(self, symbol):
        if self.websocket is None:
            await self.connect()
        await self.websocket.send(json.dumps({
            "ticks": symbol
        }))
        while True:
            msg = await self.websocket.recv()
            yield json.loads(msg)

    async def close(self):
        if self.websocket:
            await self.websocket.close()
