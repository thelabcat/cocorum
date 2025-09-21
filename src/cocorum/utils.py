#!/usr/bin/env python3
"""Rumble API utilities

This submodule provides some utilities for working with the APIs.

Copyright 2025 Wilbur Jaywright.

This file is part of Cocorum.

Cocorum is free software: you can redistribute it and/or modify it under the
terms of the GNU Lesser General Public License as published by the Free
Software Foundation, either version 3 of the License, or (at your option) any
later version.

Cocorum is distributed in the hope that it will be useful, but WITHOUT ANY
WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A
PARTICULAR PURPOSE. See the GNU Lesser General Public License for more details.

You should have received a copy of the GNU Lesser General Public License along
with Cocorum. If not, see <https://www.gnu.org/licenses/>.

S.D.G."""

import base64
import calendar
import hashlib
import time
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

    # Trims off the 6 TODO characters at the end
    return calendar.timegm(time.strptime(timestamp[:-6], static.Misc.timestamp_format))


def form_timestamp(seconds: float, suffix = "+00:00") -> str:
    """Form a Rumble timestamp.

    Args:
        seconds (float): Timestamp in seconds since Epoch, UTC.

    Returns:
        Timestamp (str): The same timestamp value, in Rumble's API format.
        """

    return time.strftime(static.Misc.timestamp_format, time.gmtime(seconds)) + suffix


def base_10_to_36(b10) -> str:
    """Convert a base 10 number to base 36.

    Args:
        b10 (int): The base 10 number.

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


def base_36_to_10(b36) -> int:
    """Convert a base 36 number to base 10.

    Args:
        b36 (str): The base 36 number.

    Returns:
        B10 (int): The same number in base 10.
        """

    return int(str(b36), 36)


def ensure_b36(num, assume_10 = False) -> str:
    """No matter wether a number is base 36 or 10, return 36.

    Args:
        num (int, str): The number in either base 10 or 36.
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


def ensure_b10(num, assume_10 = False) -> int:
    """No matter wether a number is base 36 or 10, return 10.

    Args:
        num (int, str): The number in either base 10 or 36.
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
            return base_10_to_36(num), int(num)

    # It is base 36:
    return base_36_to_10(num)


def base_36_and_10(num, assume_10 = False):
    """Take a base 36 or base 10 number, and return both base 36 and 10.

    Args:
        num (int, str): The number in either base 10 or 36.
        assume_10 (bool): If the number is a string but looks like base 10, should we assume it is?
            Defaults to False.

    Returns:
        B36 (str): The number in base 36.
        B10 (int): The number in base 10.
        """

    return ensure_b36(num, assume_10), ensure_b10(num, assume_10)


def badges_to_glyph_string(badges) -> str:
    """Convert a list of badges into a string of glyphs.

    Args:
        badges (list): A list of str or objects with __str__ method that are valid badge slugs.

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


def calc_password_hashes(password: str, salts):
    """Hash a password for Rumble authentication.

    Args:
        password (str): The password to hash.
        salts (iter): The three salts to use for hashing.

    Returns:
        Hashes (iter): The three results of hashing.
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
    b64_encoded = base64.b64encode(random_uuid).decode(static.Misc.text_encoding)
    return b64_encoded.rstrip('=')[:43]


def test_session_cookie(session_cookie: dict) -> bool:
    """Test if a session cookie dict is valid.

    Args:
        session_cookie (dict): The session cookie dict to test.

    Returns:
        Result (bool): Is the cookie dict valid?
        """

    r = requests.get(
            static.URI.login_test,
            cookies=session_cookie,
            headers=static.RequestHeaders.user_agent,
            timeout=static.Delays.request_timeout,
        )

    assert r.status_code == 200, f"Testing session token failed: {r}"

    title = r.text.split("<title>")[1].split("</title>")[0]

    # If the session token is invalid, it won't log us in and "Login" will still be shown
    return "Login" not in title


def options_check(url: str, method: str, origin=static.URI.rumble_base, cookies: dict = {}, params: dict = {}) -> bool:
    """Check of we are allowed to do method on url via an options request

    Args:
        url (str): The URL to check at.
        method (str): The HTTP method to check permission for.
        origin (str): The origin header of the options request.
            Defaults to static.URI.rumble_base
        cookies (dict): Cookie dict to use in the request.
            Defaults to no cookies.
        params (dict): Parameters to use in the request.
            Defaults to no parameters.

    Returns:
        Result (bool): Is the HTTP method allowed at the URL?
        """

    r = requests.options(
        url,
        headers={
            'Access-Control-Request-Method': method.upper(),
            'Access-Control-Request-Headers': 'content-type',
            'Origin': origin,
            },
        cookies=cookies,
        params=params,
        timeout=static.Delays.request_timeout,
        )
    return r.status_code == 200
