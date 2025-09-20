#!/usr/bin/env python3
"""Internal chat API client

Interface with the Rumble chat API to send and receive messages, etc.

Copyright 2025 Wilbur Jaywright.

This file is part of Cocorum.

Cocorum is free software: you can redistribute it and/or modify it under the terms of the GNU Lesser General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

Cocorum is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU Lesser General Public License for more details.

You should have received a copy of the GNU Lesser General Public License along with Cocorum. If not, see <https://www.gnu.org/licenses/>.

S.D.G."""

import time
import requests
import json5 as json # For parsing SSE message data
import sseclient
from .basehandles import *
from .jsonhandles import JSONObj, JSONUserAction
from .servicephp import ServicePHP
from . import scraping
from . import static
from . import utils


class ChatAPIObj(JSONObj):
    """Object in the internal chat API"""
    def __init__(self, jsondata, chat):
        """Object in the internal chat API

    Args:
        jsondata (dict): The JSON data block for the object.
        chat (ChatAPI): The ChatAPI object that spawned us.
        """

        JSONObj.__init__(self, jsondata)
        self.chat = chat


class Chatter(JSONUserAction, ChatAPIObj):
    """A user or channel in the internal chat API (abstract)"""
    def __init__(self, jsondata, chat):
        """A user or channel in the internal chat API (abstract)

    Args:
        jsondata (dict): The JSON data block for the user/channel.
        chat (ChatAPI): The ChatAPI object that spawned us.
        """
        ChatAPIObj.__init__(self, jsondata, chat)
        JSONUserAction.__init__(self, jsondata)

    @property
    def link(self):
        """The user's subpage of Rumble.com"""
        return self["link"]


class User(Chatter, BaseUser):
    """User in the internal chat API"""
    def __init__(self, jsondata, chat):
        """A user in the internal chat API

    Args:
        jsondata (dict): The JSON data block for the user.
        chat (ChatAPI): The ChatAPI object that spawned us.
        """

        Chatter.__init__(self, jsondata, chat)
        self.previous_channel_ids = [] # List of channels the user has appeared as, including the current one
        self._set_channel_id = None # Channel ID set from message
        self.servicephp = self.chat.servicephp

    @property
    def user_id(self):
        """The numeric ID of the user in base 10"""
        return int(self["id"])

    @property
    def channel_id(self):
        """The numeric channel ID that the user is appearing with in base 10"""

        # Try to get our channel ID from our own JSON (may be deprecated)
        try:
            new = int(self["channel_id"])

        # Rely on messages to have assigned our channel ID
        except KeyError:
            new = self._set_channel_id

        if new not in self.previous_channel_ids:  # Record the appearance of a new chanel appearance, including None
            self.previous_channel_ids.append(new)
        return new

    @property
    def channel_id_b10(self):
        """The numeric channel ID that the user is appearing with in base 10"""
        return self.channel_id

    @property
    def channel_id_b36(self):
        """The numeric channel ID that the user is appearing with in base 36"""
        if not self.channel_id:
            return
        return utils.base_10_to_36(self.channel_id)

    @property
    def is_follower(self):
        """Is this user following the livestreaming channel?"""
        return self["is_follower"]

    @property
    def color(self):
        """The color of our username (RGB tuple)"""
        return tuple(int(self["color"][i: i + 2], 16) for i in range(0, 6, 2))

    @property
    def badges(self):
        """Badges the user has"""
        try:
            return [self.chat.badges[badge_slug] for badge_slug in self["badges"]]

        # User has no badges
        except KeyError:
            return []


class Channel(Chatter):
    """A channel in the SSE chat"""

    def __init__(self, jsondata, chat):
        """A channel in the internal chat API

    Args:
        jsondata (dict): The JSON data block for the channel.
        chat (ChatAPI): The ChatAPI object that spawned us.
        """

        super().__init__(jsondata, chat)

        # Find the user who has this channel
        for user in self.chat.users.values():
            if user.channel_id == self.channel_id or self.channel_id in user.previous_channel_ids:
                self.user = user
                break

    @property
    def is_appearing(self):
        """Is the user of this channel still appearing as it?"""
        return self.user.channel_id == self.channel_id  # The user channel_id still matches our own

    @property
    def channel_id(self):
        """The ID of this channel in base 10"""
        return int(self["id"])

    @property
    def channel_id_b10(self):
        """The ID of this channel in base 10"""
        return self.channel_id

    @property
    def channel_id_b36(self):
        """The ID of this channel in base 36"""
        return utils.base_10_to_36(self.channel_id)

    @property
    def user_id(self):
        """The numeric ID of the user of this channel"""
        return self.user.user_id

    @property
    def user_id_b36(self):
        """The numeric ID of the user of this channel in base 36"""
        return self.user.user_id_b36

    @property
    def user_id_b10(self):
        """The numeric ID of the user of this channel in base 10"""
        return self.user.user_id_b10


class UserBadge(ChatAPIObj, BaseUserBadge):
    """A badge of a user"""

    def __init__(self, slug, jsondata, chat):
        """A user badge in the internal chat API

    Args:
        jsondata (dict): The JSON data block for the user badge.
        chat (ChatAPI): The ChatAPI object that spawned us.
        """

        ChatAPIObj.__init__(self, jsondata, chat)
        self.slug = slug  # The unique identification for this badge
        self.__icon = None

    @property
    def label(self):
        """A dictionary of lang:label pairs"""
        return self["label"]

    @property
    def icon_url(self):
        """The URL of the badge's icon"""
        return static.URI.rumble_base + self["icons"][static.Misc.badge_icon_size]


class GiftPurchaseNotification(ChatAPIObj):
    """A subscription gift under a message"""

    def __init__(self, jsondata, message):
        """A subscription gift under a message

    Args:
        jsondata (dict): The JSON data block for the message.
        message (Message): The ChatAPI message object we are under
        """

        super().__init__(jsondata, message.chat)
        self.message = message

    @property
    def total_gifts(self) -> int:
        """The number of subscriptions in this gift"""
        return self["total_gifts"]

    @property
    def gift_type(self) -> str:
        """TODO"""
        return self["gift_type"]

    @property
    def video_id(self) -> int:
        """The numeric ID of the stream this gift was sent on, in base 10"""
        return self.chat.stream_id_b10

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
        return self.message.user.username

    @property
    def creator_user_id(self) -> int:
        """The numeric ID of the user whose stream this gift was given on, in base 10"""
        return self["creator_user_id"]

    @property
    def creator_user_id_b10(self) -> int:
        """The numeric ID of the user whose stream this gift was given on, in base 10"""
        return self.creator_user_id

    @property
    def creator_user_id_b36(self) -> str:
        """The numeric ID of the user whose stream this gift was given on, in base 36"""
        return utils.base_10_to_36(self.creator_user_id)

    @property
    def creator_channel_id(self) -> int:
        """The numeric ID of the channel whose stream this gift was given on, in base 10 (can be zero)"""
        return self["creator_channel_id"] if self["creator_channel_id"] else 0

    @property
    def creator_channel_id_b10(self) -> int:
        """The numeric ID of the channel whose stream this gift was given on, in base 10 (can be zero)"""
        return self.creator_channel_id

    @property
    def creator_channel_id_b36(self) -> str:
        """The numeric ID of the channel whose stream this gift was given on, in base 36 (can be zero)"""
        return utils.base_10_to_36(self.creator_channel_id)


class Message(ChatAPIObj):
    """A single chat message in the internal chat API"""

    def __init__(self, jsondata, chat):
        """A single chat message in the internal chat API

    Args:
        jsondata (dict): The JSON data block for the message.
        chat (ChatAPI): The ChatAPI object that spawned us.
        """

        super().__init__(jsondata, chat)

        # Set the channel ID of our user if we can
        if self.user:
            self.user._set_channel_id = self.channel_id

        # Remember if we were deleted
        self.deleted = False

    def __eq__(self, other):
        """Compare this chat message with another

    Args:
        other (str, Message): Object to compare to.

    Returns:
        Comparison (bool, None): Did it fit the criteria?
        """

        if isinstance(other, str):
            return self.text == other

        # Check if the other object's text matches our own, if it has such
        if hasattr(other, "text"):
            # Check if the other object's user ID matches our own, if it has one
            if hasattr(other, "user_id"):
                # Check if the other object is a raid notification, if it says
                if hasattr(other, "raid_notification"):
                    return (self.user_id, self.text, self.raid_notification) == (other.user_id, other.text, other.raid_notification)

                return (self.user_id, self.text) == (other.user_id, other.text)

            # Check if the other object's username matches our own, if it has one
            if hasattr(other, "username"):
                # Check if the other object is a raid notification, if it says
                if hasattr(other, "raid_notification"):
                    return (self.user_id, self.text, self.raid_notification) == (other.user_id, other.text, other.raid_notification)

                return (self.user.username, self.text) == (other.username, other.text)

            # No user identifying attributes, but the text does match
            return self.text == other.text

    def __str__(self):
        """The chat message in string form"""
        return self.text

    def __int__(self):
        """The chat message in integer (ID) form"""
        return self.message_id

    @property
    def message_id(self):
        """The unique numerical ID of the chat message in base 10"""
        return int(self["id"])

    @property
    def message_id_b10(self):
        """The unique numerical ID of the chat message in base 10"""
        return self.message_id

    @property
    def message_id_b36(self):
        """The unique numerical ID of the chat message in base 36"""
        return utils.base_10_to_36(self.message_id)

    @property
    def time(self):
        """The time the message was sent on, in seconds since the Epoch UTC"""
        return utils.parse_timestamp(self["time"])

    @property
    def user_id(self):
        """The numerical ID of the user who posted the message in base 10"""
        return int(self["user_id"])

    @property
    def user_id_b10(self):
        """The numeric ID of the user in base 10"""
        return self.user_id

    @property
    def user_id_b36(self):
        """The numeric ID of the user in base 36"""
        return utils.base_10_to_36(self.user_id)

    @property
    def channel_id(self):
        """The numeric ID of the channel who posted the message, if there is one"""
        try:
            # Note: For some reason, channel IDs in messages alone show up as integers in the SSE events
            return int(self["channel_id"])
        except KeyError:  # This user is not appearing as a channel and so has no channel ID
            return None

    @property
    def channel_id_b10(self):
        """The ID of the channel who posted the message in base 10"""
        return self.channel_id

    @property
    def channel_id_b36(self):
        """The ID of the channel who posted the message in base 36"""
        if not self.channel_id:
            return
        return utils.base_10_to_36(self.channel_id)

    @property
    def text(self):
        """The text of the message"""
        return self["text"]

    @property
    def user(self):
        """Reference to the user who posted this message"""
        try:
            return self.chat.users[self.user_id]
        except KeyError:
            print(f"ERROR: Message {self.message_id} could not reference user {self.user_id} because chat has no records of them as of yet.")

    @property
    def channel(self):
        """Reference to the channel that posted this message, if there was one"""
        if not self.channel_id:
            return None

        return self.chat.channels[self.channel_id]

    @property
    def is_rant(self):
        """Is this message a rant?"""
        return "rant" in self._jsondata

    @property
    def rant_price_cents(self):
        """The price of the rant, returns 0 if message is not a rant"""
        if not self.is_rant:
            return 0
        return self["rant"]["price_cents"]

    @property
    def rant_duration(self):
        """The duration the rant will show for, returns 0 if message is not a rant"""
        if not self.is_rant:
            return 0
        return self["rant"]["duration"]

    @property
    def rant_expires_on(self):
        """When the rant expires, returns message creation time if message is not a rant"""
        if not self.is_rant:
            return self.time
        return utils.parse_timestamp(self["rant"]["expires_on"])

    @property
    def raid_notification(self):
        """Are we a raid notification? Returns associated JSON data if yes, False if no"""
        return self.get("raid_notification", False)

    @property
    def gift_purchase_notification(self):
        """Are we a gifted subs notification? Returns associated JSON data if yes, False if no

    Returns:
        Data (GiftPurchaseNotification | bool): A simple container for the data, or False"""

        if self.get("gift_purchase_notification"):
            return GiftPurchaseNotification(self["gift_purchase_notification"], self)

        return False

    def delete(self):
        """Delete this message from the chat"""
        return self.chat.delete(self)

    def pin(self):
        """Pin this message"""
        return self.chat.pin_message(self)

    def unpin(self):
        """Unpin this message if it was pinned"""
        return self.chat.unpin_message(self)


class ChatAPI():
    """The Rumble internal chat API"""

    def __init__(self, stream_id, servicephp: ServicePHP = None, history_len=1000):
        """The Rumble internal chat API

    Args:
        stream_id (int, str): Stream ID in base 10 int or base 36 str.
            WARNING: If a str is passed, this WILL ASSUME BASE 36
            even if only digits are present! Convert to int before passing
            if it is base 10.
        servicephp (ServicePHP): A logged in Service.PHP agent for two-way.
            Defaults to None, view chat as a guest.
        history_len (int): Length of message history to store.
            Defaults to 1000.
            """

        self.stream_id = utils.ensure_b36(stream_id)

        self.__mailbox = []  # A mailbox if you will
        self.__history = []  # Chat history
        self.history_len = history_len  # How many messages to store in history
        self.pinned_message = None  # If a message is pinned, it is assigned to this
        self.users = {}  # Dictionary of users by user ID
        self.channels = {}  # Dictionary of channels by channel ID
        self.badges = {}

        # Generate our URLs
        self.sse_url = static.URI.ChatAPI.sse_stream.format(stream_id_b10 = self.stream_id_b10)
        print("SSE stream URL:", self.sse_url)
        self.message_api_url = static.URI.ChatAPI.message.format(stream_id_b10 = self.stream_id_b10)

        #  Connect to SSE stream
        #  Note: We do NOT want this request to have a timeout
        self.response = requests.get(self.sse_url, stream = True, headers = static.RequestHeaders.sse_api)
        self.client = sseclient.SSEClient(self.response)
        self.event_generator = self.client.events()
        self.chat_running = True

        #  If we have session login, use it
        self.servicephp = servicephp
        if self.servicephp:
            self.scraper = scraping.Scraper(self.servicephp)
        else:
            self.scraper = None

        #  Parse the init data for the stream (must do AFTER we have servicephp)
        self.parse_init_data(self.__next_event_json())

        #  The last time we sent a message
        self.last_send_time = 0

    def close(self):
        """Close the chat connection"""
        self.response.close()
        self.chat_running = False

    @property
    def session_cookie(self):
        """The session cookie we are logged in with"""
        if self.servicephp:
            return self.servicephp.session_cookie
        return None

    @property
    def history(self):
        """The chat history, trimmed to history_len"""
        return tuple(self.__history)

    def send_message(self, text: str, channel_id: int = None):
        """Send a message in chat.

    Args:
        text (str): The message text.
        channel_id (int): Numeric ID of the channel to use.
            Defaults to None.

    Returns:
        ID (int): The ID of the sent message.
        User (User): Your current chat user information.
        """

        assert self.session_cookie, "Not logged in, cannot send message"
        assert len(text) <= static.Message.max_len, "Mesage is too long"
        curtime = time.time()
        assert self.last_send_time + static.Message.send_cooldown <= curtime, "Sending messages too fast"
        assert utils.options_check(self.message_api_url, "POST"), "Rumble denied options request to post message"
        r = requests.post(
            self.message_api_url,
            cookies = self.session_cookie,
            json = {
                "data": {
                    "request_id": utils.generate_request_id(),
                    "message": {
                        "text": text
                    },
                    "rant": None,
                    "channel_id": channel_id
                    }
                },
            #  headers = static.RequestHeaders.user_agent,
            timeout = static.Delays.request_timeout,
            )

        if r.status_code != 200:
            print("Error: Sending message failed,", r, r.text)
            return

        return int(r.json()["data"]["id"]), User(r.json()["data"]["user"], self)

    def command(self, command_message: str):
        """Send a native chat command

    Args:
        command_message (str): The message you would send to launch this command in chat.

    Returns:
        JSON (dict): The JSON returned by the command.
        """

        assert command_message.startswith(static.Message.command_prefix), "Not a command message"
        r = requests.post(
            static.URI.ChatAPI.command,
            data = {
                "video_id" : self.stream_id_b10,
                "message" : command_message,
                },
            cookies = self.session_cookie,
            headers = static.RequestHeaders.user_agent,
            timeout = static.Delays.request_timeout,
            )
        assert r.status_code == 200, f"Command failed: {r}\n{r.text}"
        return r.json()

    def delete_message(self, message):
        """Delete a message in chat.

    Args:
        message (int | Message): Object which when converted to integer is the target message ID.

    Returns:
        success (bool): Wether the operation succeeded or not.
            NOTE: Method will also print an error message if it failed.
        """

        assert not hasattr(message, "deleted") or not message.deleted, "Message was already deleted"

        assert self.session_cookie, "Not logged in, cannot delete message"
        assert utils.options_check(self.message_api_url + f"/{int(message)}", "DELETE"), "Rumble denied options request to delete message"

        r = requests.delete(
            self.message_api_url + f"/{int(message)}",
            cookies = self.session_cookie,
            #  headers = static.RequestHeaders.user_agent,
            timeout = static.Delays.request_timeout,
            )

        if r.status_code != 200:
            print("Error: Deleting message failed,", r, r.content.decode(static.Misc.text_encoding))
            return False

        if hasattr(message, "deleted"):
            message.deleted = True

        return True

    def pin_message(self, message):
        """Pin a message

        Args:
            message (int | Message): Converting this to int must return a chat message ID.
        """

        assert self.session_cookie, "Not logged in, cannot pin message"
        return self.servicephp.chat_pin(self.stream_id_b10, message)

    def unpin_message(self, message = None):
        """Unpin the pinned message

        Args:
            message (None | int | Message): Message to unpin, defaults to known pinned message.
        """

        assert self.session_cookie, "Not logged in, cannot unpin message"
        if not message:
            message = self.pinned_message
        assert message, "No known pinned message and ID not provided"
        return self.servicephp.chat_pin(self.stream_id_b10, message, unpin = True)

    def mute_user(self, user, duration: int = None, total: bool = False):
        """Mute a user.

    Args:
        user (str): Username to mute.
        duration (int): How long to mute the user in seconds.
            Defaults to infinite.
        total (bool): Wether or not they are muted across all videos.
            Defaults to False, just this video.
            """

        assert self.session_cookie, "Not logged in, cannot mute user"
        return self.servicephp.mute_user(
            username = str(user),
            is_channel = False,
            video = self.stream_id_b10,
            duration = duration,
            total = total
            )

    def unmute_user(self, user):
        """Unmute a user.

    Args:
        user (str): Username to unmute
        """

        assert self.session_cookie, "Not logged in, cannot unmute user"

        # If the user object has a username attribute, use that
        #  because most user objects will __str__ into their base 36 ID
        if hasattr(user, "username"):
            user = user.username

        record_id = self.scraper.get_muted_user_record(str(user))
        assert record_id, "User was not in muted records"
        return self.servicephp.unmute_user(record_id)

    def __next_event_json(self):
        """Wait for the next event from the SSE and parse the JSON"""
        if not self.chat_running: # Do not try to query a new event if chat is closed
            print("Chat closed, cannot retrieve new JSON data.")
            return

        try:
            event = next(self.event_generator, None)
        except requests.exceptions.ReadTimeout:
            print("Request read timeout.")
            event = None

        if not event:
            self.chat_running = False # Chat has been closed
            print("Chat has closed.")
            return
        if not event.data: # Blank SSE event
            print("Blank SSE event:>", event, "<:")
            # Self recursion should work so long as we don't get dozens of blank events in a row
            return self.__next_event_json()

        return json.loads(event.data)

    def parse_init_data(self, jsondata):
        """Extract initial chat data from the SSE init event JSON

    Args:
        jsondata (dict): The JSON data returned by the initial SSE connection.
        """

        if jsondata["type"] != "init":
            print(jsondata)
            raise ValueError("That is not init json")

        # Parse pre-connection users, channels, then messages
        self.update_users(jsondata)
        self.update_channels(jsondata)
        self.update_mailbox(jsondata)

        # Load the chat badges
        self.load_badges(jsondata)

        self.rants_enabled = jsondata["data"]["config"]["rants"]["enable"]
        # subscription TODO
        # rant levels TODO
        self.message_length_max = jsondata["data"]["config"]["message_length_max"]

    def update_mailbox(self, jsondata):
        """Parse chat messages from an SSE data JSON

    Args:
        jsondata (dict): A JSON data block from an SSE event.
        """

        # Add new messages
        self.__mailbox += [Message(message_json, self) for message_json in jsondata["data"].get("messages", []) if int(message_json["id"]) not in self.__mailbox]

    def clear_mailbox(self):
        """Delete anything in the mailbox"""
        self.__mailbox = []

    def update_users(self, jsondata):
        """Update our dictionary of users from an SSE data JSON

    Args:
        jsondata (dict): A JSON data block from an SSE event.
        """

        for user_json in jsondata["data"].get("users", []):
            try:
                self.users[int(user_json["id"])]._jsondata = user_json # Update an existing user's JSON
            except KeyError: # User is new
                self.users[int(user_json["id"])] = User(user_json, self)

    def update_channels(self, jsondata):
        """Update our dictionary of channels from an SSE data JSON

    Args:
        jsondata (dict): A JSON data block from an SSE event.
        """

        for channel_json in jsondata["data"].get("channels", []):
            try:
                self.channels[int(channel_json["id"])]._jsondata = channel_json # Update an existing channel's JSON
            except KeyError: # Channel is new
                self.channels.update({int(channel_json["id"]) : Channel(channel_json, self)})

    def load_badges(self, jsondata):
        """Create our dictionary of badges from an SSE data JSON

    Args:
        jsondata (dict): A JSON data block from an SSE event.
        """

        self.badges = {badge_slug : UserBadge(badge_slug, jsondata["data"]["config"]["badges"][badge_slug], self) for badge_slug in jsondata["data"]["config"]["badges"].keys()}

    @property
    def stream_id_b10(self):
        """The chat ID in use"""
        return utils.base_36_to_10(self.stream_id)

    def get_message(self):
        """Return the next chat message (parsing any additional data).
        Waits for it to come in, returns None if chat closed.

    Returns:
        result (Message | None): Either the next chat message or NoneType.
        """

        # We don't already have messages
        while not self.__mailbox:
            jsondata = self.__next_event_json()

            # The chat has closed
            if not jsondata:
                return

            # Messages were deleted
            if jsondata["type"] in ("delete_messages", "delete_non_rant_messages"):
                # Flag the messages in our history as being deleted
                for message in self.__history:
                    if message.message_id in jsondata["data"]["message_ids"]:
                        message.deleted = True


            # Re-initialize (could contain new messages)
            elif jsondata["type"] == "init":
                self.parse_init_data(jsondata)

            # Pinned message
            elif jsondata["type"] == "pin_message":
                self.pinned_message = Message(jsondata["data"]["message"], self)

            # New messages
            elif jsondata["type"] == "messages":
                # Parse users, channels, then messages
                self.update_users(jsondata)
                self.update_channels(jsondata)
                self.update_mailbox(jsondata)

            # Unimplemented event type
            else:
                print("API sent an unimplemented SSE event type")
                print(jsondata)

        m = self.__mailbox.pop(0) # Get the oldest message in the mailbox
        self.__history.append(m) # Add the message to the history

        # Make sure the history is not too long, clipping off the oldest messages
        del self.__history[ : max((len(self.__history) - self.history_len, 0))]

        # Return the next message from the mailbox
        return m
