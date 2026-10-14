#!/usr/bin/env python3
"""Chat SSE client tests that stay on localhost.

Copyright 2026 Wilbur Jaywright d.b.a. Marswide BGL.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

S.D.G.
"""

import json
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import urllib3.exceptions
from ld_eventsource.config import ErrorStrategy
from ld_eventsource.errors import HTTPStatusError

from cocorum import static
from cocorum.chatapi import ChatAPI, ChatClosed, _is_timeout, _rumble_sse_error_action


def _message(message_id, text, user_id="10"):
    return {
        "id": str(message_id),
        "time": "2026-01-01T00:00:00+0000",
        "user_id": user_id,
        "text": text,
    }


def _user(user_id="10", username="alice"):
    return {
        "id": user_id,
        "username": username,
        "link": f"/user/{username}",
        "color": "ff8800",
        "badges": [],
        "is_follower": False,
    }


def _event(event_type, messages):
    return {
        "type": event_type,
        "data": {
            "messages": messages,
            "users": [_user()],
            "channels": [],
            "config": {
                "rants": {"enable": False},
                "message_length_max": 200,
                "badges": {},
            },
        },
    }


def _sse(*events) -> bytes:
    chunks = [b": \n"]
    for event in events:
        chunks.append(b"data: " + json.dumps(event).encode() + b"\n\n")
    return b"".join(chunks)


class _Handler(BaseHTTPRequestHandler):
    # Chunked HTTP/1.1, same shape as Rumble's event stream: each event is its
    # own chunk, and the connection stays open after it.
    protocol_version = "HTTP/1.1"

    def do_GET(self):
        self.close_connection = True
        self.server.script.handle(self)

    def log_message(self, fmt, *args):
        return


class _Server(ThreadingHTTPServer):
    allow_reuse_address = True
    daemon_threads = True


class ScriptedSSEServer:
    """Local SSE server. Each entry is ("sse", body) or ("status", code)."""

    def __init__(self, responses):
        self.responses = list(responses)
        self.index = 0
        self.lock = threading.Lock()
        self.hold = threading.Event()
        self.http = _Server(("127.0.0.1", 0), _Handler)
        self.http.script = self
        self.thread = threading.Thread(target=self.http.serve_forever, daemon=True)
        self.thread.start()

    @property
    def url(self) -> str:
        host, port = self.http.server_address
        return f"http://{host}:{port}/stream"

    def handle(self, request: BaseHTTPRequestHandler):
        with self.lock:
            index = self.index
            self.index += 1
        if index < len(self.responses):
            kind, payload = self.responses[index]
        else:
            kind, payload = self.responses[-1]
        if kind == "status":
            request.send_response(payload)
            request.send_header("Content-Type", "text/html")
            request.send_header("Content-Length", "0")
            request.end_headers()
            return
        request.send_response(200)
        request.send_header("Content-Type", "text/event-stream")
        request.send_header("Cache-Control", "no-cache")
        request.send_header("Transfer-Encoding", "chunked")
        request.end_headers()
        chunk = f"{len(payload):X}\r\n".encode() + payload + b"\r\n"
        try:
            request.wfile.write(chunk)
            request.wfile.flush()
        except (BrokenPipeError, ConnectionResetError):
            return
        # Leave the stream open. The next chunk-size read blocks until the
        # client times out or close() shuts the socket down.
        self.hold.wait(30)

    def close(self):
        self.hold.set()
        self.http.shutdown()
        self.http.server_close()
        self.thread.join(timeout=5)


class ChatSSETests(unittest.TestCase):
    def setUp(self):
        self._old_sse_url = static.URI.ChatAPI.sse_stream
        self.server = None
        self.chat = None

    def tearDown(self):
        if self.chat is not None:
            self.chat.close()
            self.chat = None
        static.URI.ChatAPI.sse_stream = self._old_sse_url
        if self.server is not None:
            self.server.close()
            self.server = None

    def _serve(self, responses):
        self.server = ScriptedSSEServer(responses)
        static.URI.ChatAPI.sse_stream = self.server.url

    def _open(self, responses, **kwargs):
        self._serve(responses)
        self.chat = ChatAPI(1, **kwargs)
        return self.chat

    def test_error_strategy_timeout_reconnects_and_204_stops(self):
        timeout = urllib3.exceptions.ReadTimeoutError(None, None, "Read timed out.")
        action, nxt = _rumble_sse_error_action(timeout)
        self.assertTrue(_is_timeout(timeout))
        self.assertEqual(action, ErrorStrategy.CONTINUE)
        self.assertIsNone(nxt)

        action, _ = _rumble_sse_error_action(TimeoutError("timed out"))
        self.assertEqual(action, ErrorStrategy.CONTINUE)

        # A clean EOF is not an end event. Reconnect and let the status decide.
        action, _ = _rumble_sse_error_action(None)
        self.assertEqual(action, ErrorStrategy.CONTINUE)

        action, _ = _rumble_sse_error_action(ConnectionError("reset"))
        self.assertEqual(action, ErrorStrategy.CONTINUE)

        ended = HTTPStatusError(204)
        action, _ = _rumble_sse_error_action(ended)
        self.assertEqual(ended.status, 204)
        self.assertEqual(action, ErrorStrategy.FAIL)

        # 4xx is an error, not "the chat ended".
        action, _ = _rumble_sse_error_action(HTTPStatusError(400))
        self.assertEqual(action, ErrorStrategy.FAIL)

        # The same decisions come back through ErrorStrategy.apply.
        strategy = ErrorStrategy.from_lambda(_rumble_sse_error_action)
        self.assertEqual(strategy.apply(timeout)[0], ErrorStrategy.CONTINUE)
        self.assertEqual(strategy.apply(HTTPStatusError(204))[0], ErrorStrategy.FAIL)

    def test_replayed_init_is_deduped_after_timeout(self):
        first = _sse(_event("init", [_message(1, "hello"), _message(2, "world")]))
        replay = _sse(_event("init", [
            _message(1, "hello"),
            _message(2, "world"),
            _message(3, "extra"),
        ]))
        chat = self._open(
            [("sse", first), ("sse", replay)],
            read_timeout=0.6,
            reconnect_delay=0.05,
        )
        self.assertEqual(chat.get_message().text, "hello")
        self.assertEqual(chat.get_message().text, "world")
        started = time.monotonic()
        extra = chat.get_message()
        self.assertEqual(extra.text, "extra")
        self.assertEqual(extra.message_id, 3)
        self.assertLess(time.monotonic() - started, 5)
        self.assertEqual([m.text for m in chat.history], ["hello", "world", "extra"])
        self.assertTrue(chat.chat_running)

    def test_204_after_timeout_returns_none_and_calls_on_ended_once(self):
        ended = []
        chat = self._open(
            [
                ("sse", _sse(_event("init", [_message(1, "hello")]))),
                ("status", 204),
            ],
            read_timeout=0.6,
            reconnect_delay=0.05,
            on_ended=lambda: ended.append("ended"),
        )
        self.assertEqual(chat.get_message().text, "hello")
        started = time.monotonic()
        self.assertIsNone(chat.get_message())
        self.assertLess(time.monotonic() - started, 5)
        self.assertFalse(chat.chat_running)
        self.assertEqual(ended, ["ended"])
        self.assertIsNone(chat.get_message())
        self.assertEqual(ended, ["ended"])

    def test_messages_event_is_delivered(self):
        chat = self._open(
            [("sse", _sse(
                _event("init", []),
                _event("messages", [_message(7, "live")]),
            ))],
            read_timeout=5,
            reconnect_delay=0.05,
        )
        message = chat.get_message()
        self.assertEqual(message.text, "live")
        self.assertEqual(message.user.username, "alice")

    def test_close_from_another_thread_unblocks_get_message(self):
        ended = []
        chat = self._open(
            [("sse", _sse(_event("init", [])))],
            read_timeout=30,
            reconnect_delay=5,
            on_ended=lambda: ended.append("ended"),
        )
        box = {}

        def read():
            try:
                box["message"] = chat.get_message()
            except Exception as exc:
                box["error"] = exc

        reader = threading.Thread(target=read)
        reader.start()
        # Let the reader block in the socket read before we close.
        time.sleep(0.3)
        started = time.monotonic()
        chat.close()
        reader.join(timeout=2)
        self.assertFalse(reader.is_alive(), "close() did not unblock get_message()")
        self.assertNotIn("error", box)
        self.assertIsNone(box["message"])
        self.assertLess(time.monotonic() - started, 2)
        self.assertFalse(chat.chat_running)
        self.assertEqual(ended, ["ended"])
        chat.close()
        self.assertEqual(ended, ["ended"])

    def test_context_manager_closes(self):
        ended = []
        self._serve([("sse", _sse(_event("init", [])))])
        with ChatAPI(1, read_timeout=30, on_ended=lambda: ended.append("ended")) as chat:
            self.chat = chat
            self.assertTrue(chat.chat_running)
            with self.assertRaises(AttributeError):
                chat.chat_running = False
            self.assertTrue(chat.chat_running)
        self.assertFalse(chat.chat_running)
        self.assertEqual(ended, ["ended"])

    def test_context_manager_closes_when_body_raises(self):
        self._serve([("sse", _sse(_event("init", [])))])
        with self.assertRaises(RuntimeError):
            with ChatAPI(1, read_timeout=30) as chat:
                self.chat = chat
                raise RuntimeError("boom")
        self.assertFalse(self.chat.chat_running)

    def test_initial_204_raises_and_notifies(self):
        ended = []
        self._serve([("status", 204)])
        with self.assertRaises(ChatClosed):
            ChatAPI(1, on_ended=lambda: ended.append("ended"))
        self.assertEqual(ended, ["ended"])

    def test_initial_400_raises_without_on_ended(self):
        ended = []
        self._serve([("status", 400)])
        with self.assertRaises(HTTPStatusError) as caught:
            ChatAPI(1, on_ended=lambda: ended.append("ended"))
        self.assertEqual(caught.exception.status, 400)
        self.assertEqual(ended, [])

    def test_queued_messages_survive_close(self):
        chat = self._open(
            [("sse", _sse(_event("init", [_message(1, "hello"), _message(2, "world")])))],
            read_timeout=30,
        )
        chat.close()
        self.assertEqual(chat.get_message().text, "hello")
        self.assertEqual(chat.get_message().text, "world")
        self.assertIsNone(chat.get_message())


if __name__ == "__main__":
    unittest.main()
