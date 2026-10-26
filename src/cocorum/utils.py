#!/usr/bin/env python3
"""Rumble API utilities

This submodule provides some utilities for working with the APIs.

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

S.D.G."""

import base64
import calendar
import hashlib
import time
from typing import Sequence, SupportsInt
import uuid
import requests
from . import static


class MD5Ex:
    """MD5 extended hashing utilities"""

    @staticmethod
    def hash(message: str) -> str:
        """Hash a string.

        Args:
            message (str): Message to hash.

        Returns:
            Hash (str): The hex digest hash result.
        """

        # Actually, we can except bytes, but if we got string, encode the string
        if isinstance(message, str):
            message = message.encode(static.Misc.text_encoding)

        return hashlib.md5(message).hexdigest()

    @staticmethod
    def hash_stretch(password: str, salt: str, iterations: int = 1024) -> str:
        """Stretch-hash a password with a salt.

        Args:
            password (str): The password to hash.
            salt (str): The salt to add to the password.
            iterations (int): Number of times to stretch the hashing.

        Returns:
            Hash (str): The completed stretched hash.
        """

        # Start with the salt and password together
        message = (salt + password).encode(static.Misc.text_encoding)

        # Make one hash of it
        current = MD5Ex.hash(message)

        # Then keep re-adding the password and re-hashing
        for _ in range(iterations):
            current = MD5Ex.hash(current + password)

        return current


def parse_timestamp(timestamp: str) -> float:
    """Parse a Rumble timestamp.

    Args:
        timestamp (str): Timestamp in Rumble's API format.

    Returns:
        Timestamp (float): The same timestamp value, in seconds since Epoch, UTC.
    """

    return calendar.timegm(time.strptime(timestamp, static.Misc.timestamp_format))


def form_timestamp(seconds: float) -> str:
    """Form a Rumble timestamp.

    Args:
        seconds (float): Timestamp in seconds since Epoch, UTC.

    Returns:
        Timestamp (str): The same timestamp value, in Rumble's API format.
    """

    return time.strftime(static.Misc.timestamp_format, time.gmtime(seconds))


def base_10_to_36(b10: SupportsInt) -> str:
    """Convert a base 10 number to base 36.

    Args:
        b10 (SupportsInt): The base 10 number.

    Returns:
        B36 (str): The same number in base 36.
    """

    b10 = int(b10)
    b36 = ""
    base_len = len(static.Misc.base36)
    while b10:
        b36 = static.Misc.base36[b10 % base_len] + b36
        b10 //= base_len

    return b36


def base_36_to_10(b36: str) -> int:
    """Convert a base 36 number to base 10.

    Args:
        b36 (str): The base 36 number.

    Returns:
        B10 (int): The same number in base 10.
    """

    return int(str(b36), 36)


def ensure_b36(num: SupportsInt | str, assume_10: bool = False) -> str:
    """No matter wether a number is base 36 or 10, return 36.

    Args:
        num (SupportsInt | str): The number in either base 10 or 36.
        assume_10 (bool): If the number is a string but looks like base 10, should we assume it is?
            Defaults to False.

    Returns:
        Number (str): The number in base 36.
    """

    # It is base 10
    if isinstance(num, int) or hasattr(num, "__int__"):
        return base_10_to_36(int(num))

    # It is a string or has a string conversion attribute
    if isinstance(num, str) or hasattr(num, "__str__"):
        num = str(num)

        # The string number is in base 10
        if num.isnumeric() and assume_10:
            return base_10_to_36(num)

    # It is base 36:
    return num


def ensure_b10(num: SupportsInt | str, assume_10: bool = False) -> int:
    """No matter wether a number is base 36 or 10, return 10.

    Args:
        num (SupportsInt | str): The number in either base 10 or 36.
        assume_10 (bool): If the number is a string but looks like base 10, should we assume it is?
            Defaults to False.

    Returns:
        Number (int): The number in base 10.
    """

    # It is base 10 or has an integer conversion method
    if isinstance(num, int) or hasattr(num, "__int__"):
        return int(num)

    # It is a string or has a string conversion attribute
    if isinstance(num, str) or hasattr(num, "__str__"):
        num = str(num)

        # The string number is in base 10
        if num.isnumeric() and assume_10:
            return int(num)

    # It is base 36:
    return base_36_to_10(num)


def base_36_and_10(num: SupportsInt | str, assume_10: bool = False):
    """Take a base 36 or base 10 number, and return both base 36 and 10.

    Args:
        num (SupportsInt | str): The number in either base 10 or 36.
        assume_10 (bool): If the number is a string but looks like base 10, should we assume it is?
            Defaults to False.

    Returns:
        B36 (str): The number in base 36.
        B10 (int): The number in base 10.
    """

    return ensure_b36(num, assume_10), ensure_b10(num, assume_10)


def video_id_from_url(url: str) -> str:
    """Get the real video ID (base 36) from a watch-page URL, a v-slug, or an embed URL.

    The ID in a watch-page URL is NOT the video ID. For example,
    https://rumble.com/v2o2oe5-title.html is video 157009049, which is 2lh8yh in
    base 36, and int("2o2oe5", 36) is a different number. Embed URLs
    (https://rumble.com/embed/v2lh8yh/) do carry the real ID and are read directly.
    For watch URLs and slugs, this asks Rumble's oEmbed endpoint, which returns JSON
    (no HTML page scraping).

    Args:
        url (str): https://rumble.com/v2o2oe5-title.html, https://rumble.com/v2o2oe5,
            v2o2oe5, v2o2oe5-title.html, https://rumble.com/shorts/v5d871x,
            or https://rumble.com/embed/v2lh8yh/ (auto detects and trims).

    Returns:
        Video ID (str): The real video ID in base 36, e.g. "2lh8yh".

    Raises:
        ValueError: The input is not a Rumble watch URL, slug, or embed URL.
        LookupError: Rumble has no video at that watch URL, or its reply had no embed ID.
    """

    text = str(url).strip()

    # Embed URLs already hold the real ID
    if m := static.RegEx.embed_url.search(text):
        return m.group(1).lower()

    vslug = url.removesuffix("/").rsplit("/", 1)[-1].split("-", 1)[0].split("?", 1)[0]
    assert vslug.startswith("v"), "Not a valid v-slug or URL containing one"

    lookup = f"{static.URI.rumble_base}/{vslug}-.html"

    r = requests.get(
        static.URI.oembed,
        params={"url": lookup},
        headers=static.RequestHeaders.user_agent,
        timeout=static.Delays.request_timeout,
    )
    if r.status_code == 404:
        raise LookupError(f"Rumble has no video at the v-slug {vslug}")
    assert r.status_code == 200, f"oEmbed request failed: {r}\n{r.text}"

    m = static.RegEx.embed_url.search(r.json().get("html", ""))
    if not m:
        raise LookupError(f"Rumble's oEmbed reply for {vslug} had no embed ID")
    return m.group(1).lower()


def badges_to_glyph_string(badges: list[str]) -> str:
    """Convert a list of badges into a string of glyphs.

    Args:
        badges (list[str]): A list of str or objects with __str__ method that are valid badge slugs.

    Returns:
        Glyphs (str): The badge list as a UTF-8 glyph string, uses ? for unknown badges.
        """

    out = ""
    for badge in badges:
        badge = str(badge)
        if badge in static.Misc.badges_as_glyphs:
            out += static.Misc.badges_as_glyphs[badge]
        else:
            out += "?"
    return out


def calc_password_hashes(password: str, salts: Sequence[str]) -> (str, str, str):
    """Hash a password for Rumble authentication.

    Args:
        password (str): The password to hash.
        salts (Sequence[str]): The three salts to use for hashing.

    Returns:
        Hashes (str, str, str): The three results of hashing.
        """

    # Stretch-hash the password with the first salt
    stretched1 = MD5Ex.hash_stretch(password, salts[0], 128)

    # Add the second salt to that result, and hash one more time
    final_hash1 = MD5Ex.hash(stretched1 + salts[1])

    # Stretch-hash the password with the third salt
    stretched2 = MD5Ex.hash_stretch(password, salts[2], 128)

    return final_hash1, stretched2, salts[1]


def generate_request_id() -> str:
    """Generate a UUID for API requests

    Returns:
        UUID (str): Random base64 encoded UUID.
    """

    random_uuid = uuid.uuid4().bytes + uuid.uuid4().bytes
    b64_encoded = base64.b64encode(
        random_uuid).decode(static.Misc.text_encoding)
    return b64_encoded.rstrip('=')[:43]
