#!/usr/bin/env python3
"""Tests for utils.video_id_from_url, with the network mocked.

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

import unittest
from unittest import mock

from cocorum import static, utils

EMBED_HTML = '<iframe src="https://rumble.com/embed/v2lh8yh/" width="1920"></iframe>'


def reply(status=200, html=EMBED_HTML):
    r = mock.Mock(status_code=status, text="")
    r.json.return_value = {"html": html}
    return r


class TestVideoIdFromUrl(unittest.TestCase):
    def test_embed_url_needs_no_request(self):
        with mock.patch.object(utils.requests, "get") as get:
            self.assertEqual(utils.video_id_from_url("https://rumble.com/embed/v2LH8YH/?pub=4"), "2lh8yh")
        get.assert_not_called()

    def test_watch_urls_and_slugs(self):
        inputs = (
            "https://rumble.com/v2o2oe5-synthwave-radio.html",
            "https://rumble.com/v2o2oe5-synthwave-radio.html?e9s=src_v1_ucp",
            "https://rumble.com/v2o2oe5",
            "rumble.com/v2o2oe5.html",
            "https://www.rumble.com/v2o2oe5-x.html",
            "v2o2oe5",
            "v2o2oe5-synthwave-radio.html",
        )
        for text in inputs:
            with self.subTest(text=text), mock.patch.object(utils.requests, "get", return_value=reply()) as get:
                self.assertEqual(utils.video_id_from_url(text), "2lh8yh")
                self.assertEqual(get.call_args.args[0], static.URI.oembed)
                kw = get.call_args.kwargs
                self.assertEqual(kw["params"], {"url": "https://rumble.com/v2o2oe5-.html"})
                self.assertIs(kw["headers"], static.RequestHeaders.user_agent)
                self.assertIs(kw["timeout"], static.Delays.request_timeout)

    def test_shorts_sent_bare(self):
        with mock.patch.object(utils.requests, "get", return_value=reply()) as get:
            self.assertEqual(utils.video_id_from_url("https://rumble.com/shorts/v5d871x?x=1"), "2lh8yh")
        self.assertEqual(get.call_args.kwargs["params"], {"url": "https://rumble.com/shorts/v5d871x"})

    def test_not_found(self):
        with mock.patch.object(utils.requests, "get", return_value=reply(404)), self.assertRaises(LookupError):
            utils.video_id_from_url("v2zzzzz")

    def test_no_embed_in_reply(self):
        with mock.patch.object(utils.requests, "get", return_value=reply(html="")), self.assertRaises(LookupError):
            utils.video_id_from_url("v2o2oe5")

    def test_bad_input(self):
        for text in ("", "https://example.com/v2o2oe5", "2lh8yh", "not a url"):
            with self.subTest(text=text), mock.patch.object(utils.requests, "get") as get:
                with self.assertRaises(ValueError):
                    utils.video_id_from_url(text)
                get.assert_not_called()


if __name__ == "__main__":
    unittest.main()
