#!/usr/bin/env python
# -*- coding: utf-8 -*-

import aiohttp
import asyncio
import json
import functools
import os
import sys


def coroutine(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        cr = func(*args, **kwargs)
        cr.send(None)
        return cr
    return wrapper


class DotDict(dict):
    def __init__(self, **kwargs):
        self.__dict__ = kwargs

DotDict.__getattr__ = DotDict.__getitem__


urls = DotDict(
    api=DotDict(
        chat_messages='https://api.gitter.im/v1/rooms/{room_id}/chatMessages',
        rooms='https://api.gitter.im/v1/rooms'
    ),
    stream=DotDict(
        chat_messages='https://stream.gitter.im/v1/rooms/{room_id}/chatMessages'
    )
)


try:
    token = os.environ['GITTER']
except KeyError:
    sys.exit(('GITTER env variable is missing. '
              'Go to https://developer.gitter.im/apps to get your token and set GITTER=<token>'))
headers = {
    'Authorization': 'Bearer ' + token
}

print('Authorization headers:')
print(headers)


@coroutine
def parse_stream(target):
    json_depth = 0
    buf = bytearray()
    while True:
        data = (yield)
        for c in data:
            if c == ord('{'):
                json_depth += 1
            if json_depth > 0:
                buf.append(c)
            if c == ord('}'):
                json_depth -= 1

        if buf and json_depth == 0:
            d = json.loads(buf.decode('utf-8'))
            target.send(d)
            buf = bytearray()


async def send_message(room_id, message):
    url = urls.api.chat_messages.format(room_id=room_id)
    async with aiohttp.post(url, data={'text': message}, headers=headers) as r:
        pass


async def join_room(room_uri):
    url = urls.api.rooms
    async with aiohttp.post(url, data={'uri': room_uri}, headers=headers) as r:
        j = await r.json()
        if 'error' in j:
            raise ValueError(j['error'] + ': {0}'.format(r))
        return j


async def get_messages(room_id, target):
    parser = parse_stream(target)
    url = urls.stream.chat_messages.format(room_id=room_id)
    async with aiohttp.get(url, headers=headers) as r:
        while True:
            chunk = await r.content.read(10)
            if not chunk:
                break
            parser.send(chunk)


class Room:
    def __init__(self, room_uri):
        self.room_uri = room_uri
        self.room = None

    async def join(self):
        if not self.room:
            self.room = await join_room(self.room_uri)

    async def send_message(self, message):
        if not self.room:
            await self.join()
        await send_message(self.room['id'], message)

    async def get_messages(self, target):
        if not self.room:
            await self.join()
        await get_messages(self.room['id'], target)
