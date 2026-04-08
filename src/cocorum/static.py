#!/usr/bin/env python3
"""Cocorum static variable definitions

Provides various data that, if changed, would need to change globally.

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

import re


class RequestHeaders:
    """Headers for various HTTPrequests"""

    user_agent = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/51.0.2704.103 Safari/537.36"
    }
    """Header with a fake user-agent string"""

    sse_api = {"Accept": "text/event-stream"}
    """Headers for the SSE chat API"""


class StaticAPIEndpoints:
    """API endpoints that don't change and shouldn't trigger a refresh"""

    main = [
        "user_id",
        "username",
        "channel_id",
        "channel_name",
    ]
    """Endpoints of the main API"""

    stream = ["id", "created_on"]
    """Endpoints of the stream subobject"""

    # # Endpoints of the subscriptions gift object
    # gifted_subs = [
    #     "total_gifts",
    #     "gift_type",
    #     "video_id",
    #     "purchased_by",
    #     ]


class URI:
    """URIs to various Rumble services"""

    rumble_base = "https://rumble.com"
    """Base URL to Rumble's website, for URLs that are relative to it"""

    login_test = rumble_base + "/login.php"
    """Test the session token by sending it here and checking the title"""

    mutes_page = rumble_base + "/account/moderation/muting?pg={page}"
    """Webpage with all the mutes on it, format with page number"""

    channels_page = rumble_base + "/user/{username}/channels"
    """Channels under a user, format with username"""

    playlists_page = rumble_base + "/my-library/playlists"
    """The logged-in user's playlist page"""

    account_page = rumble_base + "/account"
    """Account page"""

    servicephp = rumble_base + "/service.php"
    """The Service.PHP API"""

    uploadphp = "https://web5.rumble.com/upload.php"
    """The video upload PHP"""

    rumbot_suffix = "/api/ls"
    """RumBot passthrough API ending"""

    class ChatAPI:
        """URIs of the chat API"""

        base = "https://web7.rumble.com/chat/api/chat/{stream_id_b10}"
        """Rumble's internal chat URL for a stream, format this string with a stream_id_b10"""

        sse_stream = base + "/stream"
        """SSE stream of chat events"""

        message = base + "/message"
        """Message actions"""

        command = "https://rumble.com/chat/command"
        """Chat commands (does not use the base)"""


class Delays:
    """Various times for delays and waits"""

    request_timeout = 20
    """How long to wait before giving up on a network request, in seconds"""

    upload_request_timeout = 300
    """How long to wait before giving up on a video chunk upload, in seconds"""

    api_refresh_default = 10
    """How long to reuse old data from the main API, in seconds"""

    api_refresh_minimum = 5
    """Minimum refresh rate for the main API, as defined by Rumble"""


class Message:
    """For chat messages"""

    max_len = 200
    """Maximum chat message length"""

    send_cooldown = 3
    """How long to wait between sending messages"""

    command_prefix = "/"
    """Prefix Rumble uses for native command"""


class Upload:
    """Data relating to uploading videos"""

    chunksz = 10000000
    """Size of upload chunks in bytes, not sure if this can be changed"""

    api_ver = "1.3"
    """Upload API version to use"""

    max_filesize = 15 * (1000**3)
    """Maximum upload size in bytes, is 15GB as stated by Rumble"""


class Misc:
    """No idea where else to put this data"""

    base36 = "0123456789abcdefghijklmnopqrstuvwxyz"
    """Digits of the numerical base 36 that Rumble uses"""

    badges_as_glyphs = {
        "verified": "✅",
        "admin": "👑",
        "moderator": "🛡",
        "premium": "🗲",
        "locals": "♖",
        "recurring_subscription": "♖",
        "locals_supporter": "⛋",
        "whale-grey": "🐳",
        "whale-yellow": "🐳",
        "whale-blue": "🐳",
    }
    """Dictionary of badge slugs mapped to UTF-8 glyphs, for end-user convenience"""

    text_encoding = "utf-8"
    """Encoding for all text-bytes conversions"""

    badge_icon_size = "48"
    """Size of chat badge icons to retrieve, only valid one has long been the string 48"""

    timestamp_format = "%Y-%m-%dT%H:%M:%S%z"
    """Rumble's timestamp format in ISO 8601 designations"""

    session_token_key = "u_s"
    """Key of the session token within the session cookie dict"""

    find_acc_apikey = re.compile(
        r'(?<=var \$a = new Account\("AccountOverview",").*(?="\);)'
    )
    """RegEx to find the account API key in the https://rumble.com/account page source
    It looks like this: `var $a = new Account("AccountContent","##########");`"""

    tag_split = ", "
    """Characters that video tags are separated by"""

    video_edit_success = "Your changes have been saved!<br>Please allow up to 30 seconds for them to take effect."
    """Message that Rumble shows (in HTML) upon successful video edit"""

    class ContentTypes:
        """Types of content that can be rumbled on"""

        video = 1
        """A video or livestream"""

        comment = 2
        """A comment"""
