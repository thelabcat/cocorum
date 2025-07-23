#!/usr/bin/env python3
"""Cocorum Account and page API wrapper

Provides operations that involve apiKey.

WARNING: This does not currently work reliably. It's only in the module because
I was working on it and a critical fix for .uploadphp at the same time, and I
don't want to figure out how to Git that. Sorry!

Copyright 2025 Wilbur Jaywright.

This file is part of Cocorum.

Cocorum is free software: you can redistribute it and/or modify it under the terms of the GNU Lesser General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

Cocorum is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU Lesser General Public License for more details.

You should have received a copy of the GNU Lesser General Public License along with Cocorum. If not, see <https://www.gnu.org/licenses/>.

S.D.G."""

import requests
import bs4
from . import static, scraping

NotImplemented

class AccountAPI:
    """Do things that involve apiKey"""
    def __init__(self, scraper):
        """Do things that involve apiKey

        Args:
            scraper (cocorum.scraping.Scraper): A scraper instance
        """

        self.scraper = scraper
        self.apikey = scraper.get_acc_apikey()
        self.servicephp = self.scraper.servicephp

    # def upload_closed_captions(self)
    # def edit_channel(self)
    # def set_channel_restrictions(self)
    # def add_channel(self)
    # def reserve_channel(self)
    # def remove_from_checkout(self)
    # def get_invoices(self)
    # def sget_license_autorenew(self)
    # def open_license_description(self)
    # def add_syndication_account(self)

    def keyed_request(self, endpoint: str, action: str, params = {}, data = {}, method = "GET"):
        """Make a Rumble API request with the apiKey

        Args:
            endpoint (str): The URL path within Rumble to access, for example "/account".
            action (str): The "a" parameter to use.
            params (dict): Any other params to attach to the URL.
                Defaults to nothing.
            data (dict): Form data for the request.
                Defaults to nothing.
            method (str): The type of request to make.
                Defaults to "GET".

        Returns:
            request (requests.Request): The result."""

        params_all = {"apiKey": self.apikey, "a": action}
        params_all.update(params)

        r = requests.request(
            method,
            static.URI.rumble_base + endpoint,
            params = params_all,
            data = data,
            headers = static.RequestHeaders.user_agent,
            cookies = self.servicephp.session_cookie,
            timeout = static.Delays.request_timeout,
            )

        assert r.status_code == 200, f"Keyed request failed with status {r.status_code}:\n" + \
            r.text
        return r

    def get_video_info_settings(self, video_id):
        """Get the information and settings for a video we uploaded

        Args:
            video_id (int): The numeric ID of the video in base 10

        Returns:
            settings (cocorum.scraping.HTMLVideoSettings): The data"""

        r = self.keyed_request("/account/content", "edit", {"id": video_id}, method = "POST")
        soup = bs4.BeautifulSoup(r.text, features="html.parser")
        return scraping.HTMLVideoSettings(soup, self.servicephp)

    def set_video_info_settings(self, video_id, **kwargs):
        """Edit video properties
        Args:
            video_id (int): The numeric ID of the video to edit in base 10
            thumbnail (str): The on-server filename of the thumbnail to use.
                Defaults to None, no change.
            title (str): The new video title.
                Defaults to None, no change.
            description (str): The new video description.
                Defaults to None, no change.
            channel_featured (bool): Make this a featured video on the channel?
                Defaults to None, no change.
            profile_featured (bool): Make this a featured video on the userpage?
                Defaults to None, no change.
            visibility (str): Must be public, unlisted, or private.
                Defaults to None, no change.
            channel_id (int): The numeric ID of the channel to post this video under, or 0 for userpage.
                Defaults to None, no change.
            category_primary (int): The numeric ID of the primary category to put the video under.
                Defaults to None, no change.
            category_secondary (int): The numeric ID of the secondary category to put the video under, or 0 for nothing.
                Defaults to None, no change.
            placeholder (str): The on-server filename of the placeholder video to use for a livestream.
                Defaults to None, no change.

            TODO add support for the captions...
            """
        assert kwargs, "No changes to make"

        # Data keys that can be passed
        valid_keys = (
            "thumbnail",
            "title",
            "description",
            "channel_featured",
            "profile_featured",
            "visibility",
            "channel_id",
            "category_primary",
            "category_secondary",
            "placeholder",
            )

        # Mapping from argument names to form data names
        mapping = {
            "channel_featured": "is_featured_for_channel",
            "profile_featured": "is_featured_for_user",
            "channel_id": "channelId",
            "category_primary": "siteChannelId",
            "category_secondary": "mediaChannelId",
            }

        # base data with blank stubs for unsupported keys
        data = {
            "liveStreamingUnlistReplay": 0,
            "liveStreamingSourcePassthrough": 0,
            "closed_captions": {"uploads":{},"removals":{}},
            }

        # Figure out if some of the settings are staying the same
        old_data_needed = False
        for vk in valid_keys:
            if kwargs.get(vk) is None:
                old_data_needed = True
                break

        # Get the old data for the video and complete our form data with it
        if old_data_needed:
            old_data = self.get_video_info_settings(video_id)
            data.update({
                "title": old_data.title,
                "description": old_data.description,
                "tags": static.Misc.tag_split.join(old_data.tags),
                "is_featured_for_channel": "0", # str(old_data.channel_featured), TODO
                "is_featured_for_user": "0", # str(old_data.profile_featured), TODO
                "visibility": old_data.visibility,
                "channelId": str(old_data.channel[1]),
                "siteChannelId": str(old_data.category_primary[1]),
                "mediaChannelId": str(old_data.category_secondary[1]),
                })

        # Overwrite old data with new
        data.update(kwargs)

        # Remap argument names to form data names
        for k, v in mapping.items():
            if k in data:
                data[v] = data[k]
                del data[k]

        print(data)

        r = self.keyed_request(endpoint = "/account/content", action = "edit", params = {"id": video_id, "sid": 8}, data = data, method = "POST")

        assert r.text.strip() == static.Misc.video_edit_success, str(r.content)

    def get_closed_captions(self, video_id: int, lang = "en"):
        """Get the closed captions for a video

        Args:
            video_id (int): The numeric ID of the video in base 10.
            lang (str): The language of captions to check, in two-character code.
                Defaults to "en".

        Returns:
            captions (str | NoneType): The URL to the captions file,
                or None if they do not exist in this language.
        """

        v = self.keyed_request("/api/Media/GetClosedCaptions", params = {
            "mid": video_id,
            "language": lang,
            }).json()["return"]
        if not v:
            return None
        return v["path"]
