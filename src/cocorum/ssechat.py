#!/usr/bin/env python3
"""SSE chat display client

This part of cocorum is not part of the official Rumble Live Stream API, but may provide a more reliable method of ensuring all chat messages are received.

Example usage:
```
from cocorum import ssechat

chat = ssechat.SSEChat(stream_id = STREAM_ID) #Stream ID can be base 10 or 36
chat.clear_mailbox() #Erase messages that were still visible before we connected

while True:
    msg = chat.get_message() #Hangs until a new message arrives
    print(msg.user.username, ":", msg)
```
S.D.G."""

import json #For parsing SSE message data
import requests
import sseclient
from .localvars import *
from . import utils

class SSEChatObject():
    """Object in SSE chat API"""
    def __init__(self, jsondata, chat):
        """Pass the object JSON, and the parent SSEChat object"""
        self._jsondata = jsondata
        self.chat = chat

    def __getitem__(self, key):
        """Get a key from the JSON"""
        return self._jsondata[key]

class SSEChatter(SSEChatObject):
    """A user or channel in the SSE chat"""
    def __init__(self, jsondata, chat):
        """Pass the object JSON, and the parent SSEChat object"""
        super().__init__(jsondata, chat)
        self.__profile_pic = None #The stored profile picture of the user or channel as a URL

    def __eq__(self, other):
        """Compare this chatter with another"""
        #If the other is a string, check if it matches our username
        if isinstance(other, str):
            return self.username == other

        #If the other has a username attribute, check if it matches our own
        if hasattr(other, "username"):
            return self.username == other.username

    def __str__(self):
        """The chatter in string form"""
        return self.username

    @property
    def username(self):
        """The username"""
        return self["username"]

    @property
    def link(self):
        """The user's subpage of Rumble.com"""
        return self["link"]

    @property
    def profile_pic_url(self):
        """The URL of the chatter's profile picture, if they have one"""
        try:
            return self._jsondata["image.1"]
        except KeyError:
            return None

    @property
    def profile_pic(self):
        """The chatter's profile picture as a bytes string"""
        if not self.profile_pic_url: #The profile picture is blank
            return b''

        if not self.__profile_pic: #We never queried the profile pic before
            #TODO make the timeout configurable
            response = requests.get(self.profile_pic_url, timeout = DEFAULT_TIMEOUT)
            assert response.status_code == 200, "Status code " + str(response.status_code)

            self.__profile_pic = response.content

        return self.__profile_pic

class SSEChatUser(SSEChatter):
    """User in SSE chat"""
    def __init__(self, jsondata, chat):
        """Pass the object JSON, and the parent SSEChat object"""
        super().__init__(jsondata, chat)
        self.previous_channel_ids = [] #List of channels the user has appeared as, including the current one

    @property
    def user_id(self):
        """The numeric ID of the user"""
        return self["id"]

    @property
    def channel_id(self):
        """The numeric channel ID that the user is appearing with"""
        try:
            new = self["channel_id"]
        except KeyError: #This user is not appearing as a channel and so has no channel ID
            new = None
        if new not in self.previous_channel_ids: #Record the appearance of a new chanel appearance, including None
            self.previous_channel_ids.append(new)
        return new

    @property
    def is_follower(self):
        """Is this user following the livestreaming channel?"""
        return self["is_follower"]

    @property
    def color(self):
        """The color of our username (RGB tuple)"""
        return tuple(int(self["color"][i : i + 2], 16) for i in range(0, 6, 2))

    @property
    def badges(self):
        """Badges the user has"""
        return [self.chat.badges[badge_slug] for badge_slug in self["badges"]]

class SSEChatChannel(SSEChatter):
    """A channel in the SSE chat"""
    def __init__(self, jsondata, chat):
        """Pass the object JSON, and the parent SSEChat object"""
        super().__init__(jsondata, chat)

        #Find the user who has this channel
        for user in self.chat.users.values():
            if user.channel_id == self.channel_id or self.channel_id in user.previous_channel_ids:
                self.user = user
                break

    @property
    def is_appearing(self):
        """Is the user of this channel still appearing as it?"""
        return self.user.channel_id == self.channel_id #The user channel_id still matches our own

    @property
    def channel_id(self):
        """The ID of this channel"""
        return self["id"]

    @property
    def user_id(self):
        """The numeric ID of the user of this channel"""
        return self.user.user_id

class SSEChatUserBadge(SSEChatObject):
    """A badge of a user"""
    def __init__(self, slug, jsondata, chat):
        """Pass the slug, the object JSON, and the parent SSEChat object"""
        super().__init__(jsondata, chat)
        self.slug = slug #The unique identification for this badge
        self.__icon = None

    def __eq__(self, other):
        """Check if this badge is equal to another"""
        #Check if the string is either our slug or our label in any language
        if isinstance(other, str):
            return other in (self.slug, self.label.values())

        #Check if the compared object has the same slug, if it has one
        if hasattr(other, "slug"):
            return self.slug == other.slug

    def __str__(self):
        """The chat user badge in string form"""
        return self.slug

    @property
    def label(self):
        """A dictionary of lang:label pairs"""
        return self["label"]

    @property
    def icon_url(self):
        """The URL of the badge's icon"""
        return RUMBLE_BASE_URL + self["icons"][BADGE_ICON_SIZE]

    @property
    def icon(self):
        """The badge's icon as a bytestring"""
        if not self.__icon: #We never queried the icon before
            #TODO make the timeout configurable
            response = requests.get(self.icon_url, timeout = DEFAULT_TIMEOUT)
            assert response.status_code == 200, "Status code " + str(response.status_code)

            self.__icon = response.content

        return self.__icon

class SSEChatMessage(SSEChatObject):
    """A single chat message from the SSE API"""
    def __eq__(self, other):
        """Compare this chat message with another"""
        if isinstance(other, str):
            return self.text == other

        #Check if the other object's text matches our own, if it has such
        if hasattr(other, "text"):
            #Check if the other object's user ID matches our own, if it has one
            if hasattr(other, "user_id"):
                return (self.user_id, self.text) == (other.user_id, other.text)

            #Check if the other object's username matches our own, if it has one
            if hasattr(other, "username"):
                return (self.user.username, self.text) == (other.username, other.text)

            #No user identifying attributes, but the text does match
            return self.text == other.text

    def __str__(self):
        """The chat message in string form"""
        return self.text

    @property
    def message_id(self):
        """The unique numerical ID of the chat message"""
        return self["id"]

    @property
    def time(self):
        """The time the message was sent on, in seconds since the Epoch UTC"""
        return utils.parse_timestamp(self["time"])

    @property
    def user_id(self):
        """The numerical ID of the user who posted the message"""
        return self["user_id"]

    @property
    def channel_id(self):
        """The numeric ID of the channel who posted the message, if there is one"""
        try:
            return self["channel_id"]
        except KeyError: #This user is not appearing as a channel and so has no channel ID
            return None

    @property
    def text(self):
        """The text of the message"""
        return self["text"]

    @property
    def user(self):
        """Reference to the user who posted this message"""
        return self.chat.users[self.user_id]

    @property
    def channel(self):
        """Reference to the channel that posted this message, if there was one"""
        if not self.channel_id:
            return None

        return self.chat.channels[self.channel_id]

    @property
    def is_rant(self):
        """Is this message a rant?"""
        return "rant" in self._jsondata.keys()

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

class SSEChat():
    """Access the Rumble SSE chat api"""
    def __init__(self, stream_id):
        self.stream_id = utils.stream_id_ensure_b36(stream_id)

        self.__mailbox = [] #A mailbox if you will
        self.deleted_message_ids = [] #IDs of messages that were deleted, as reported by the client
        self.users = {} #Dictionary of users by user ID
        self.channels = {} #Dictionary of channels by channel ID
        self.badges = {}

        #Connect to the API
        self.url = SSE_CHAT_URL.format(stream_id_b10 = self.stream_id_b10)
        self.client = sseclient.SSEClient(self.url)
        self.chat_running = True
        self.parse_init_data(self.next_jsondata())

    def next_jsondata(self):
        """Wait for the next message from the SSE and parse the JSON"""
        if not self.chat_running: #Do not try to query a new message if chat is closed
            return

        message = next(self.client, None)
        if not message:
            self.chat_running = False #Chat has been closed
            return
        if not message.data: #Blank SSE event
            print("Blank SSE event:", message)
            #Self recursion should work so long as we don't get dozens of blank events in a row
            return self.next_jsondata()

        return json.loads(message.data)

    def parse_init_data(self, jsondata):
        """Extract initial chat data from the SSE init message JSON"""
        if jsondata["type"] != "init":
            print(jsondata)
            raise ValueError("That is not init json")

        #Parse pre-connection messages, users, and channels
        self.update_mailbox(jsondata)
        self.update_users(jsondata)
        self.update_channels(jsondata)

        #Load the chat badges
        self.load_badges(jsondata)

        self.rants_enabled = jsondata["data"]["config"]["rants"]["enable"]
        #subscription TODO
        #rant levels TODO
        self.message_length_max = jsondata["data"]["config"]["message_length_max"]

    def update_mailbox(self, jsondata):
        """Parse chat messages from an SSE data JSON"""
        #Add new messages
        self.__mailbox += [SSEChatMessage(message_json, self) for message_json in jsondata["data"]["messages"] if message_json["id"] not in self.__mailbox]

    def clear_mailbox(self):
        """Delete anything in the mailbox"""
        self.__mailbox = []

    def clear_deleted_message_ids(self):
        """Clear and return the list of deleted message IDs"""
        del_m = self.deleted_message_ids.copy()
        self.deleted_message_ids = []
        return del_m

    def update_users(self, jsondata):
        """Update our dictionary of users from an SSE data JSON"""
        for user_json in jsondata["data"]["users"]:
            try:
                self.users[user_json["id"]]._jsondata = user_json #Update an existing user's JSON
            except KeyError: #User is new
                self.users[user_json["id"]] = SSEChatUser(user_json, self)

    def update_channels(self, jsondata):
        """Update our dictionary of channels from an SSE data JSON"""
        for channel_json in jsondata["data"]["users"]:
            try:
                self.channels[channel_json["id"]]._jsondata = channel_json #Update an existing channel's JSON
            except KeyError: #Channel is new
                self.channels.update({channel_json["id"] : SSEChatChannel(channel_json, self)})

    def load_badges(self, jsondata):
        """Create our dictionary of badges given a dictionary of badges"""
        self.badges = {badge_slug : SSEChatUserBadge(badge_slug, jsondata["data"]["config"]["badges"][badge_slug], self) for badge_slug in jsondata["data"]["config"]["badges"].keys()}

    @property
    def stream_id_b10(self):
        """The chat ID in user"""
        return utils.stream_id_36_to_10(self.stream_id)

    def get_message(self):
        """Return the next chat message (parsing any additional data), waits for it to come in, returns None if chat closed"""
        #We don't already have messages
        while not self.__mailbox:
            jsondata = self.next_jsondata()

            #The chat has closed
            if not jsondata:
                return

            #Messages were deleted
            if jsondata["type"] in ("delete_messages", "delete_non_rant_messages"):
                self.deleted_message_ids += jsondata["data"]["message_ids"]

            #Re-initialize (could contain new messages)
            elif jsondata["type"] == "init":
                self.parse_init_data(jsondata)

            #New messages
            elif jsondata["type"] == "messages":
                #Parse messages, users, and channels
                self.update_mailbox(jsondata)
                self.update_users(jsondata)
                self.update_channels(jsondata)

            #Unimplemented event type
            else:
                print("API sent an unimplemented SSE event type")
                print(jsondata)

        return self.__mailbox.pop(0) #Return the first message in the mailbox, and then remove it from there
