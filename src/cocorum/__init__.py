#!/usr/bin/env python3
"""
Cocorum

An unofficial Python wrapper for the Rumble.com APIs

Copyright 2025 Wilbur Jaywright.

This file is part of Cocorum.

Cocorum is free software: you can redistribute it and/or modify it under the terms of the GNU Lesser General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

Cocorum is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU Lesser General Public License for more details.

You should have received a copy of the GNU Lesser General Public License along with Cocorum. If not, see <https://www.gnu.org/licenses/>.

This base module is a Python wrapper for the Rumble Live Stream API v1.0 (beta), with some quality of life additions, such as:
- Automatic refresh when past the refresh_rate delay when querying any non_static property.
- All timespamps are parsed to seconds since Epoch, UTC timezone.
- Chat has new_messages and new_rants properties that return only messages and rants since the last time they were read.


Modules exported by this package:

- `chatapi`: Provide the ChatAPI object for interacting with a livestream chat.
- `servicephp`: Provide the ServicePHP object for interacting with the service.php API.
- `uploadphp`: Provide the UploadPHP object for uploading videos.
- `scraping`: Provide functions and the Scraper object for getting various data via HTML scraping.
- `jsonhandles`: Abstract classes for handling JSON data blocks.
- `basehandles`: Abstract classes with common methods for both JSON and HTML wrappers.
- `utils`: Various utility functions for internal calculations and checks.
- `static`: Global data that does not change across the package.

Example usage:

```
from cocorum import RumbleAPI

## API_URL is Rumble Live Stream API URL with key
api = RumbleAPI(API_URL, refresh_rate = 10)

print(api.username)
## Should display your Rumble username

print("Latest follower:", api.latest_follower)
## Should display your latest follower, or None if you have none.

if api.latest_subscriber:
    print(api.latest_subscriber, f"subscribed for ${api.latest_subscriber.amount_dollars}")
## Should display your latest subscriber if you have one.

livestream = api.latest_livestream # None if there is no stream running

if livestream:
    print(livestream.title)
    print("Stream visibility is", livestream.visibility)

    # We will use this later
    STREAM_ID = livestream.stream_id

    print("Stream ID is", STREAM_ID)

    import time # We'll need this Python builtin for delays and knowing when to stop

    # Get messages for one minute
    start_time = time.time()

    # Continue as long as we haven't been going for a whole minute, and the livestream is still live
    while time.time() - start_time < 60 and livestream.is_live:
        # For each new message...
        for message in livestream.chat.new_messages:
            # Display it
            print(message.username, "said", message)

        # Wait a bit, just to keep the loop from maxxing a CPU core
        time.sleep(0.1)
```
S.D.G."""

import time
import warnings
import requests

# Make all submodules available from base name
from . import chatapi, servicephp, uploadphp, scraping, accountapi, jsonhandles, utils, static

from .jsonhandles import JSONObj, JSONUserAction

class Follower(JSONUserAction):
    """Rumble follower"""
    @property
    def followed_on(self):
        """When the follower followed, in seconds since Epoch UTC"""
        return utils.parse_timestamp(self["followed_on"])

class Subscriber(JSONUserAction):
    """Rumble subscriber"""
    def __eq__(self, other):
        """Is this subscriber equal to another?

    Args:
        other (str, JSONUserAction, Subscriber): The other object to compare to.

    Returns:
        Comparison (bool, None): Did it fit the criteria?
        """

        # Check if the compared string is our username
        if isinstance(other, str):
            return self.username == other

        # check if the compared number is our amount in cents
        # if isinstance(other, (int, float)):
            # return self.amount_cents == other

        # Check if the compared object's username matches our own, if it has one
        if hasattr(other, "username"):
            # Check if the compared object's cost amout matches our own, if it has one
            if hasattr(other, "amount_cents"):
                return self.amount_cents == other.amount_cents

            # Other object has no amount_cents attribute
            return self.username == other.username

    @property
    def user(self):
        """AFAIK this is being deprecated, use username instead"""
        return self["user"]

    @property
    def amount_cents(self):
        """The total subscription amount in cents"""
        return self["amount_cents"]

    @property
    def amount_dollars(self):
        """The subscription amount in dollars"""
        return self["amount_dollars"]

    @property
    def subscribed_on(self):
        """When the subscriber subscribed, in seconds since Epoch UTC"""
        return utils.parse_timestamp(self["subscribed_on"])

class StreamCategory(JSONObj):
    """Category of a Rumble stream"""

    @property
    def slug(self):
        """Return the category's slug, AKA it's ID"""
        return self["slug"]

    @property
    def title(self):
        """Return the category's title"""
        return self["title"]

    def __eq__(self, other):
        """Is this category equal to another?

    Args:
        other (str, StreamCategory): Other object to compare to.

    Returns:
        Comparison (bool, None): Did it fit the criteria?
        """

        # Check if the compared string is our slug or title
        if isinstance(other, str):
            return other in (self.slug, self.title)

        # Check if the compared object has the same slug, if it has one
        if hasattr(other, "slug"):
            return self.slug == other.slug

    def __str__(self):
        """The category in string form"""
        return self.title

class Livestream():
    """Rumble livestream"""
    def __init__(self, jsondata, api):
        """Rumble livestream

    Args:
        jsondata (dict): The JSON block for a single livestream.
        api (RumbleAPI): The Rumble Live Stream API wrapper that spawned us.
        """

        self._jsondata = jsondata
        self.api = api
        self.is_disappeared = False # The livestream is in the API listing
        self.__chat = LiveChat(self)

    def __eq__(self, other):
        """Is this stream equal to another?

    Args:
        other (str, int, Livestream): Object to compare to.

    Returns:
        Comparison (bool, None): Did it fit the criteria?
        """

        # Check if the compared string is our stream ID
        if isinstance(other, str):
            return self.stream_id == other # or self.title == other

        # check if the compared number is our chat ID (linked to stream ID)
        if isinstance(other, (int, float)):
            return self.stream_id_b10 == other

        # Check if the compared object has the same stream ID
        if hasattr(other, "stream_id"):
            return self.stream_id == utils.ensure_b36(other.stream_id)

        # Check if the compared object has the same chat ID
        if hasattr(other, "stream_id_b10"):
            return self.stream_id_b10 == other.stream_id_b10

    def __str__(self):
        """The livestream in string form (it's ID in base 36)"""
        return self.stream_id

    def __getitem__(self, key):
        """Return a key from the JSON, refreshing if necessary

    Args:
        key (str): A valid JSON key.
        """

        # The livestream has not disappeared from the API listing,
        # the key requested is not a value that doesn't change,
        # and it has been api.refresh rate since the last time we refreshed
        if (not self.is_disappeared) and (key not in static.StaticAPIEndpoints.stream) and (time.time() - self.api.last_refresh_time > self.api.refresh_rate):
            self.api.refresh()

        return self._jsondata[key]

    @property
    def stream_id(self):
        """The livestream ID in base 36"""
        return self["id"]

    @property
    def stream_id_b36(self):
        """The livestream ID in base 36"""
        return self.stream_id

    @property
    def stream_id_b10(self):
        """The livestream chat ID (stream ID in base 10)"""
        return utils.base_36_to_10(self.stream_id)

    @property
    def title(self):
        """The title of the livestream"""
        return self["title"]

    @property
    def created_on(self):
        """When the livestream was created, in seconds since the Epock UTC"""
        return utils.parse_timestamp(self["created_on"])

    @property
    def is_live(self):
        """Is the stream live?"""
        return self["is_live"] and not self.is_disappeared

    @property
    def visibility(self):
        """Is the stream public, unlisted, or private?"""
        return self["visibility"]

    @property
    def categories(self):
        """A list of our categories"""
        data = self["categories"].copy().values()
        return [StreamCategory(jsondata_block) for jsondata_block in data]

    @property
    def likes(self):
        """Number of likes on the stream"""
        return self["likes"]

    @property
    def dislikes(self):
        """Number of dislikes on the stream"""
        return self["dislikes"]

    @property
    def like_ratio(self):
        """Ratio of people who liked the stream to people who reacted total"""
        try:
            return self.likes / (self.likes + self.dislikes)

        except ZeroDivisionError:
            return None

    @property
    def watching_now(self):
        """The number of people watching now"""
        return self["watching_now"]

    @property
    def chat(self):
        """The livestream chat"""
        return self.__chat

class ChatMessage(JSONUserAction):
    """A single message in a Rumble livestream chat"""
    def __eq__(self, other):
        """Is this message equal to another?

    Args:
        other (str, ChatMessage): Object to compare to.

    Returns:
        Comparison (bool, None): Did it fit the criteria?
        """

        # Check if the compared string is our message
        if isinstance(other, str):
            return self.text == other

        # # Check if the compared message has the same username and text (not needed)
        # if type(other) == type(self):
        #     return (self.username, self.text) == (other.username, other.text)

        # Check if the compared object has the same text
        if hasattr(other, "text"):
            # Check if the compared object has the same username, if it has one
            if hasattr(other, "username"):
                return (self.username, self.text) == (other.username, other.text)

            return self.text == other.text # the other object had no username attribute

    def __str__(self):
        """Message as a string (its content)"""
        return self.text

    @property
    def text(self):
        """The message text"""
        return self["text"]

    @property
    def created_on(self):
        """When the message was created, in seconds since Epoch UTC"""
        return utils.parse_timestamp(self["created_on"])

    @property
    def badges(self):
        """The user's badges"""
        return tuple(self["badges"].values())

class Rant(ChatMessage):
    """A single rant in a Rumble livestream chat"""
    def __eq__(self, other):
        """Is this category equal to another?

    Args:
        other (str, ChatMessage): Object to compare to.

    Returns:
        Comparison (bool, None): Did it fit the criteria?
        """

        # Check if the compared string is our message
        if isinstance(other, str):
            return self.text == other

        # # Check if the compared rant has the same username, amount, and text (unneccesary?)
        # if type(other) == type(self):
        #     return (self.username, self.amount_cents, self.text) == (other.username, other.amount_cents, other.text)

        # Check if the compared object has the same text
        if hasattr(other, "text"):
            # Check if the compared object has the same username, if it has one
            if hasattr(other, "username"):
                # Check if the compared object has the same cost amount, if it has one
                if hasattr(other, "amount_cents"):
                    return (self.username, self.amount_cents, self.text) == (other.username, other.amount_cents, other.text)

                # Other object has no amount_cents attribute
                return (self.username, self.text) == (other.username, other.text)

            # Other object had no username attribute
            return self.text == other.text

    @property
    def expires_on(self):
        """When the rant will expire, in seconds since the Epoch UTC"""
        return self["expires_on"]

    @property
    def amount_cents(self):
        """The total rant amount in cents"""
        return self["amount_cents"]

    @property
    def amount_dollars(self):
        """The rant amount in dollars"""
        return self["amount_dollars"]

class LiveChat():
    """Reference for chat of a Rumble livestream"""
    def __init__(self, stream):
        """Reference for chat of a Rumble livestream

    Args:
        stream (dict): The JSON block of a single Rumble livestream.
        """

        self.stream = stream
        self.api = stream.api
        self.last_newmessage_time = 0 # Last time we were checked for "new" messages
        self.last_newrant_time = 0 # Last time we were checked for "new" rants

    def __getitem__(self, key):
        """Return a key from the stream's chat JSON"""
        return self.stream["chat"][key]

    @property
    def latest_message(self):
        """The latest chat message"""
        # This endpoint does not exist in the RUM Live Alerts LS API
        if self.api._rumbot_mode:
            print("ERROR: RUM Live Alerts does not pass full chat in its LS API.")
            return None

        if not self["latest_message"]:
            return None # No-one has chatted on this stream yet
        return ChatMessage(self["latest_message"])

    @property
    def recent_messages(self):
        """Recent chat messages"""
        # This endpoint does not exist in the RUM Live Alerts LS API
        if self.api._rumbot_mode:
            print("ERROR: RUM Live Alerts does not pass full chat in its LS API.")
            return []

        data = self["recent_messages"].copy()
        return [ChatMessage(jsondata_block) for jsondata_block in data]

    @property
    def new_messages(self):
        """Chat messages that are newer than the last time this was referenced"""
        # This endpoint does not exist in the RUM Live Alerts LS API
        if self.api._rumbot_mode:
            print("ERROR: RUM Live Alerts does not pass full chat in its LS API.")
            return []

        rem = self.recent_messages.copy()
        rem.sort(key=lambda x: x.created_on) # Sort the messages so the newest ones are last

        # There are no recent messages, or all messages are older than the last time we checked
        if not rem or rem[-1].created_on < self.last_newmessage_time:
            return []

        i = 0
        for i, m in enumerate(rem):
            if m.created_on > self.last_newmessage_time:
                break # i is now the index of the oldest new message

        self.last_newmessage_time = time.time()
        return rem[i:]

    @property
    def latest_rant(self):
        """The latest chat rant"""
        if not self["latest_rant"]:
            return None # No-one has ranted on this stream yet
        return Rant(self["latest_rant"])

    @property
    def recent_rants(self):
        """Recent chat rants"""
        data = self["recent_rants"].copy()
        return [Rant(jsondata_block) for jsondata_block in data]

    @property
    def new_rants(self):
        """Chat rants that are newer than the last time this was referenced"""
        rera = self.recent_rants.copy()
        rera.sort(key = lambda x: x.created_on) # Sort the rants so the newest ones are last

        # There are no recent rants, or all rants are older than the last time we checked
        if not rera or rera[-1].created_on < self.last_newrant_time:
            return []

        i = 0
        for i, r in enumerate(rera):
            if r.created_on > self.last_newrant_time:
                break # i is now the index of the oldest new rant

        self.last_newrant_time = time.time()
        return rera[i:]

class GiftedSub(JSONObj):
    """A single gift containing one or more subscriptions"""
#     def __init__(self, jsondata, api):
#         """A single gift containing one or more subscriptions
#
#     Args:
#         jsondata (dict): The JSON block for a single livestream.
#         api (RumbleAPI): The Rumble Live Stream API wrapper that spawned us.
#         """
#
#         self._jsondata = jsondata
#         self.api = api
#         self.is_disappeared = False # The gift is in the API listing
#
#
#     def __getitem__(self, key):
#         """Return a key from the JSON, refreshing if necessary
#
#     Args:
#         key (str): A valid JSON key.
#         """
#
#         # The gift has not disappeared from the API listing,
#         # the key requested is not a value that doesn't change,
#         # and it has been api.refresh rate since the last time we refreshed
#         if (not self.is_disappeared) and (key not in static.StaticAPIEndpoints.gifted_subs) and (time.time() - self.api.last_refresh_time > self.api.refresh_rate):
#             self.api.refresh()
#
#         return self._jsondata[key]

    @property
    def total_gifts(self) -> int:
        """The number of subscriptions in this gift"""
        return self["total_gifts"]

    @property
    def gift_type(self) -> str:
        """TODO"""
        return self["gift_type"]

    @property
    def remaining_gifts(self) -> int:
        """Subscriptions from the gift that have yet to apply to a user
    WARNING: This is shallow! I have no way to reliably ID particular gifts to update the GiftedSub data."""
        return self["remaining_gifts"]

    @property
    def video_id(self) -> int:
        """The numeric ID of the stream this gift was sent on, in base 10"""
        return self["video_id"]

    @property
    def video_id_b10(self) -> int:
        """The numeric ID of the stream this gift was sent on, in base 10"""
        return self.video_id

    @property
    def video_id_b36(self) -> str:
        """The numeric ID of the stream this gift was sent on, in base 36"""
        return utils.base_10_to_36(self.video_id)

    @property
    def purchased_by(self) -> str:
        """The username of who purchased this gift"""
        return self["purchased_by"]


class RumbleAPI():
    """Rumble Live Stream API wrapper"""

    def __init__(self, api_url, refresh_rate = static.Delays.api_refresh_default, rumbot: bool = False):
        """Rumble Live Stream API wrapper

    Args:
        api_url (str): The Rumble API URL, with the key.
        refresh_rate (int, float): How long to reuse queried data before refreshing.
            Defaults to static.Delays.api_refresh_default.
        rumbot (bool): The api_url points to an instance of RUM Live Alerts.
            The API URL for this would usually be http://localhost:9843/api/ls
            Useful to avoid rate limits, but some data is not passed through.
            Defaults to False.
        """

        self.refresh_rate = refresh_rate
        self._rumbot_mode = rumbot
        self.last_refresh_time = 0
        self.last_newfollower_time = time.time()
        self.last_newsubscriber_time = time.time()
        self.__livestreams = {}
#        self.__gifted_subs = {}
        self._jsondata = {}
        self.api_url = api_url

        # Warn about refresh rate being below minimum
        if self.refresh_rate < static.Delays.api_refresh_minimum:
            warnings.warn(f"Cocorum set to over-refresh, rate of {self.refresh_rate} seconds (less than {static.Delays.api_refresh_minimum})." + \
                "Superscript must self-limit or Rumble will reject queries!")

    @property
    def api_url(self):
        """Our API URL"""
        return self.__api_url

    @api_url.setter
    def api_url(self, url):
        """Set a new API URL, and refresh

    Args:
        url (str): The new API URL to use.
        """

        self.__api_url = url
        self.refresh()

    def __getitem__(self, key):
        """Return a key from the JSON, refreshing if necessary

    Args:
        key (str): A valid JSON key.
        """

        # This is not a static key, and it's time to refresh our data
        if key not in static.StaticAPIEndpoints.main and time.time() - self.last_refresh_time > self.refresh_rate:
            self.refresh()

        return self._jsondata[key]

    def check_refresh(self):
        """Refresh only if we are past the refresh rate"""
        if time.time() - self.last_refresh_time > self.refresh_rate:
            self.refresh()

    def refresh(self):
        """Reload data from the API"""
        self.last_refresh_time = time.time()
        response = requests.get(self.api_url, headers = static.RequestHeaders.user_agent, timeout = static.Delays.request_timeout)
        assert response.status_code == 200, "Status code " + str(response.status_code)

        self._jsondata = response.json()

        # If we are in RUM Live Alerts mode, remove padding
        if self._rumbot_mode:
            self.__unpad_jsondata()

        # Remove livestream references that are no longer listed
        listed_ids = [jsondata["id"] for jsondata in self._jsondata["livestreams"]]
        for stream_id in self.__livestreams.copy():
            if stream_id not in listed_ids:
                self.__livestreams[stream_id].is_disappeared = True
                del self.__livestreams[stream_id]

        # Update livestream references' JSONs in-place
        for jsondata in self._jsondata["livestreams"]:
            try:
                # Update the JSON of the stored livestream
                self.__livestreams[jsondata["id"]]._jsondata = jsondata

            except KeyError: # The livestream has not been stored yet
                self.__livestreams[jsondata["id"]] = Livestream(jsondata, self)

    def __unpad_jsondata(self):
        """Remove padding from JSON data we retrieved from RUM Live Alerts"""

        # Nullify blank latest follower
        if not self._jsondata["followers"]["latest_follower"]["username"]:
            self._jsondata["followers"]["latest_follower"] = None

        # Remove blank recent followers
        self._jsondata["followers"]["recent_followers"] =\
            [f for f in self._jsondata["followers"]["recent_followers"] if f["username"]]

        # Nullify blank latest subscriber
        if not self._jsondata["subscribers"]["latest_subscriber"]["username"]:
            self._jsondata["subscribers"]["latest_subscriber"] = None

        # Remove blank recent subscribers
        self._jsondata["subscribers"]["recent_subscribers"] =\
            [f for f in self._jsondata["subscribers"]["recent_subscribers"] if f["username"]]

        # Remove blank livestreams
        self._jsondata["livestreams"] =\
            [l for l in self._jsondata["livestreams"] if l["id"]]

        # For each real Livestream
        for l in self._jsondata["livestreams"]:
            # Nullify blank latest Rant
            if not l["chat"]["latest_rant"]["username"]:
                l["chat"]["latest_rant"] = None

            # Remove blank recent rants
            l["chat"]["recent_rants"] =\
                [r for r in l["chat"]["recent_rants"] if r["username"]]

    @property
    def data_timestamp(self):
        """The timestamp on the last data refresh"""
        # Definitely don't ever trigger a refresh on this
        return self._jsondata["now"]

    @property
    def api_type(self):
        """Type of API URL in use, user or channel"""
        return self["type"]

    @property
    def user_id(self):
        """The user ID in base 36"""
        return self["user_id"]

    @property
    def user_id_b36(self):
        """The user ID in base 36"""
        return self.user_id

    @property
    def user_id_b10(self):
        """The user ID in base 10"""
        return utils.base_36_to_10(self.user_id)

    @property
    def username(self):
        """The username"""
        return self["username"]

    @property
    def channel_id(self):
        """The channel ID, if we are a channel"""
        return self["channel_id"]

    @property
    def channel_name(self):
        """The channel name, if we are a channel"""
        return self["channel_name"]

    @property
    def num_followers(self):
        """The number of followers of this user or channel"""
        return self["followers"]["num_followers"]

    @property
    def num_followers_total(self):
        """The total number of followers of this account across all channels"""
        return self["followers"]["num_followers_total"]

    @property
    def latest_follower(self):
        """The latest follower of this user or channel"""
        if not self["followers"]["latest_follower"]:
            return None # No-one has followed this user or channel yet
        return Follower(self["followers"]["latest_follower"])

    @property
    def recent_followers(self):
        """A list of recent followers"""
        data = self["followers"]["recent_followers"].copy()
        return [Follower(jsondata_block) for jsondata_block in data]

    @property
    def new_followers(self):
        """Followers that are newer than the last time this was checked (or newer than RumbleAPI object creation)"""
        recent_followers = self.recent_followers

        nf = [follower for follower in recent_followers if follower.followed_on > self.last_newfollower_time]
        nf.sort(key = lambda x: x.followed_on)

        self.last_newfollower_time = time.time()

        return nf

    @property
    def num_subscribers(self):
        """The number of subscribers of this user or channel"""
        return self["subscribers"]["num_subscribers"]

    @property
    def num_subscribers_total(self):
        """The total number of subscribers of this account across all channels"""
        return self["subscribers"]["num_subscribers_total"]

    @property
    def latest_subscriber(self):
        """The latest subscriber of this user or channel"""
        if not self["subscribers"]["latest_subscriber"]:
            return None # No-one has subscribed to this user or channel yet
        return Subscriber(self["subscribers"]["latest_subscriber"])

    @property
    def recent_subscribers(self):
        """A list of recent subscribers (shallow)"""
        data = self["subscribers"]["recent_subscribers"].copy()
        return [Subscriber(jsondata_block) for jsondata_block in data]

    @property
    def new_subscribers(self):
        """Subscribers that are newer than the last time this was checked (or newer than RumbleAPI object creation)"""
        recent_subscribers = self.recent_subscribers

        ns = [subscriber for subscriber in recent_subscribers if subscriber.subscribed_on > self.last_newsubscriber_time]
        ns.sort(key = lambda x: x.subscribed_on)

        self.last_newsubscriber_time = time.time()

        return ns

    @property
    def livestreams(self):
        """A dictionairy of our livestreams"""
        self.check_refresh()
        return self.__livestreams

    @property
    def latest_livestream(self):
        """Return latest livestream to be created. Use this to get a single running livestream"""
        if not self.livestreams:
            return None # No livestreams are running
        return max(self.livestreams.values(), key = lambda x: x.created_on)

    @property
    def latest_gifted_sub(self):
        """The latest subscriptions gift sent on the user or channel.
    WARNING: This is shallow! I have no way to reliably ID particular gifts to update the GiftedSub data."""
        # This endpoint does not exist in the RUM Live Alerts LS API
        if self._rumbot_mode:
            print("ERROR: RUM Live Alerts does not pass this in its LS API.")
            return None

        return GiftedSub(self["latest_gifted_sub"])

    @property
    def recent_gifted_subs(self):
        """The most recent subscriptions gifts sent on the user or channel.
    WARNING: This is shallow! I have no way to reliably ID particular gifts to update the GiftedSub data."""
        # This endpoint does not exist in the RUM Live Alerts LS API
        if self._rumbot_mode:
            print("ERROR: RUM Live Alerts does not pass this in its LS API.")
            return []

        return [GiftedSub(jsondata) for jsondata in self["recent_gifted_subs"]]
