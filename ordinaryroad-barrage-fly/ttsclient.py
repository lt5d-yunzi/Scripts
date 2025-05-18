#  Copyright 2023 OrdinaryRoad
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.


import argparse
import asyncio
import json
import logging
import pyttsx3
from asyncio import Event
from contextlib import asynccontextmanager
from datetime import timedelta
from typing import AsyncGenerator, Tuple

import aiohttp
from reactivestreams.subscriber import Subscriber
from reactivestreams.subscription import Subscription
from rsocket.helpers import single_transport_provider
from rsocket.payload import Payload
from rsocket.rsocket_client import RSocketClient
from rsocket.streams.stream_from_async_generator import StreamFromAsyncGenerator
from rsocket.transports.aiohttp_websocket import TransportAioHttpClient

subscribe_payload_json = {
    "data": {
        "taskIds": [],
        "cmd": "SUBSCRIBE"
    }
}

tts_engine = pyttsx3.init()

def tts_worker_once(text):
    try:
        tts_engine.say(text)
        tts_engine.runAndWait()  # 阻塞读完才返回
    except Exception as e:
        logging.warning(f"TTS朗读异常: {e}")

class ChannelSubscriber(Subscriber):
    def __init__(self, wait_for_responder_complete: Event, enable_tts: bool) -> None:
        super().__init__()
        self.subscription = None
        self._wait_for_responder_complete = wait_for_responder_complete
        self.enable_tts = enable_tts

    def on_subscribe(self, subscription: Subscription):
        self.subscription = subscription
        self.subscription.request(0x7FFFFFFF)

    def on_next(self, value: Payload, is_complete=False):
        try:
            msg_dto = json.loads(value.data)
            platform_map = {
                "BILIBILI": "B站",
                "HUYA": "虎牙",
                "DOYU": "斗鱼",
                "DOUYIN": "抖音",
                "KUAISHOU": "快手"
            }

            tts_text = None

            if msg_dto.get('type') == "DANMU":
                platform = platform_map.get(msg_dto.get('platform'), msg_dto.get('platform'))
                username = msg_dto['msg'].get('username', '未知用户')
                content = msg_dto['msg'].get('content', '[空内容]')

                safe_username = username if isinstance(username, str) else "异常用户名"
                safe_content = content if isinstance(content, str) else "[非文本消息]"

                msg = f"{platform}  {safe_username} ：{safe_content}"
                logging.info(msg)
                tts_text = msg

            elif msg_dto.get('type') == "GIFT":
                platform = platform_map.get(msg_dto.get('platform'), msg_dto.get('platform'))
                username = msg_dto['msg'].get('username', '神秘用户')
                gift_name = msg_dto['msg'].get('giftName', '未知礼物')
                gift_count = msg_dto['msg'].get('giftCount', 1)

                safe_username = username if isinstance(username, str) else "异常用户"
                safe_gift = str(gift_name) if gift_name else "虚拟礼物"
                safe_count = int(gift_count) if str(gift_count).isdigit() else 1

                msg = f"{platform}  {safe_username} ：赠送了{safe_gift}x{safe_count}"
                logging.info(msg)
                tts_text = msg

            if self.enable_tts and tts_text:
                tts_worker_once(tts_text)

        except (KeyError, json.JSONDecodeError, ValueError) as e:
            logging.warning(f"消息解析异常: {str(e)}")

        if is_complete:
            self._wait_for_responder_complete.set()

    def on_error(self, exception: Exception):
        logging.error('Error from server on channel' + str(exception))
        self._wait_for_responder_complete.set()

    def on_complete(self):
        logging.info('Completed from server on channel')
        self._wait_for_responder_complete.set()

@asynccontextmanager
async def connect(websocket_uri):
    async with aiohttp.ClientSession() as session:
        async with session.ws_connect(websocket_uri) as websocket:
            async with RSocketClient(
                    single_transport_provider(TransportAioHttpClient(websocket=websocket)),
                    keep_alive_period=timedelta(seconds=30),
                    max_lifetime_period=timedelta(days=1)
            ) as client:
                yield client

async def main(websocket_uri, enable_tts: bool):
    async with connect(websocket_uri) as client:
        channel_completion_event = Event()

        async def generator() -> AsyncGenerator[Tuple[Payload, bool], None]:
            yield Payload(
                data=json.dumps(subscribe_payload_json["data"]).encode()
            ), False
            await Event().wait()

        stream = StreamFromAsyncGenerator(generator)
        requested = client.request_channel(Payload(), stream)
        requested.subscribe(ChannelSubscriber(channel_completion_event, enable_tts))

        await channel_completion_event.wait()

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser()
    parser.add_argument('--uri', default='ws://localhost:9898', type=str, help="WebSocket 服务器地址")
    parser.add_argument('-t', action='append', required=True, help="任务ID")
    parser.add_argument('--enable-tts', action='store_true', help="启用 TTS 语音朗读")
    parser.add_argument('--rate', type=int, default=200, help="TTS语速，默认200")
    args = parser.parse_args()

    uri = args.uri
    subscribe_payload_json["data"]["taskIds"] = args.t
    tts_engine.setProperty('rate', args.rate)

    asyncio.run(main(uri, args.enable_tts))
