#!/usr/bin/env python3
"""Service.PHP interactions

Control Rumble via Service.PHP

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

import requests
import bs4
from . import scraping
from . import static
from . import utils
from .basehandles import *
from .jsonhandles import JSONObj


class APIUserBadge(JSONObj, BaseUserBadge):
    """A badge of a user as returned by the API"""

    def __init__(self, slug, jsondata):
        """A badge of a user as returned by the API.

    Args:
        slug (str): The string identifier of the badge.
        jsondata (dict): The JSON data block of the badge.
        """

        JSONObj.__init__(self, jsondata)
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


class APIComment(JSONObj, BaseComment):
    """A comment on a video as returned by a successful attempt to make it"""

    def __init__(self, jsondata, servicephp):
        """A comment on a video as returned by a successful attempt to make it

    Args:
        jsondata (dict): The JSON block for a single comment.
        servicephp (ServicePHP): The ServicePHP object that spawned us.
        """

        JSONObj.__init__(self, jsondata)
        self.servicephp = servicephp

        # Badges of the user who commented if we have them
        if self.get("comment_user_badges"):
            self.user_badges = {slug: APIUserBadge(slug, data) for slug, data in self["comment_user_badges"].items()}

    def __repr__(self):
        """String to represent this object"""
        return f"{type(self).__name__}(user_display='{self.user_display}', text=\"{self.text}\")"

    @property
    def comment_id(self):
        """The numeric ID of the comment"""
        return int(self["comment_id"])

    @property
    def text(self):
        """The text of the comment"""
        return self["comment_text"]

    @property
    def user_display(self):
        """The display name of the user who commented"""
        return self["comment_user_display"]

    @property
    def tree_size(self):
        """TODO"""
        return self["comment_tree_size"]


class APIContentVotes(JSONObj, BaseContentVotes):
    """Votes made on content"""

    def __str__(self):
        """The string form of the content votes"""
        return self.score_formatted

    @property
    def num_votes_up(self):
        """Upvotes on the content"""
        return self._jsondata.get("num_votes_up", 0)

    @property
    def num_votes_down(self):
        """Downvotes on the content"""
        return self._jsondata.get("num_votes_down", 0)

    @property
    def score(self):
        """Summed score of the content"""
        return self["score"]

    @property
    def votes(self):
        """The total number of votes on the content"""
        if not self["votes"]:
            return 0
        return self["votes"]

    @property
    def num_votes_up_formatted(self):
        """The upvotes on the content, formatted into a string"""
        return self._jsondata.get("num_votes_up_formatted", "0")

    @property
    def num_votes_down_formatted(self):
        """The downvotes on the content, formatted into a string"""
        return self._jsondata.get("num_votes_down_formatted", "0")

    @property
    def score_formatted(self):
        """The total votes on the content, formatted into a string"""
        return self._jsondata.get("score_formatted", "0")

    @property
    def content_type(self):
        """The type of content being voted on"""
        return self["content_type"]

    @property
    def content_id(self):
        """The numerical ID of the content being voted on"""
        return self["content_id"]


class APIUser(JSONObj, BaseUser):
    """User data as returned by the API"""

    def __init__(self, jsondata, servicephp):
        """User data as returned by the API.

    Args:
        jsondata (dict): The JSON data block of a single user.
        servicephp (ServicePHP): The ServicePHP object that spawned us.
        """

        JSONObj.__init__(self, jsondata)
        self.servicephp = servicephp

        # Our profile picture data
        self.__picture = None

    def __repr__(self):
        """String to represent this object"""
        return f"{type(self).__name__}(username='{self.username}', user_id={self.user_id})"

    @property
    def user_id(self):
        """The numeric ID of the user in base 10"""
        return self["id"]

    @property
    def user_id_b10(self):
        """The numeric ID of the user in base 10"""
        return self.user_id

    @property
    def user_id_b36(self):
        """The numeric ID of the user in base 36"""
        return utils.base_10_to_36(self.user_id)

    @property
    def username(self):
        """The username of the user"""
        return self["username"]

    @property
    def picture_url(self):
        """The URL of the user's profile picture"""
        return self["picture"]

    @property
    def picture(self):
        """The user's profile picture as a bytes string"""
        if not self.picture_url:  # The profile picture is blank
            return b''

        if not self.__picture:  # We never queried the profile pic before
            response = requests.get(self.picture_url, timeout=static.Delays.request_timeout)
            assert response.status_code == 200, "Status code " + str(response.status_code)

            self.__picture = response.content

        return self.__picture

    @property
    def verified_badge(self):
        """Is the user verified?"""
        return self["verified_badge"]

    @property
    def followers(self):
        """The number of followers this user has"""
        return self["followers"]

    @property
    def followed(self):
        """TODO -> Bool"""
        return self["followed"]


class APIPlaylist(JSONObj, BasePlaylist):
    """Playlist as returned by the API"""

    def __init__(self, jsondata, servicephp):
        """Playlist as returned by the API.

    Args:
        jsondata (dict): The JSON data block of a playlist.
        servicephp (ServicePHP): The ServicePHP object that spawned us.
        """

        JSONObj.__init__(self, jsondata)
        self.servicephp = servicephp
        self.user = APIUser(jsondata["user"], self.servicephp)

    @property
    def playlist_id(self):
        """The numeric playlist ID in base 64"""
        return self["id"]

    @property
    def title(self):
        """The title of the playlist"""
        return self["title"]

    @property
    def description(self):
        """The description of the playlist"""
        return self["description"]

    @property
    def visibility(self):
        """The visibility of the playlist"""
        return self["visibility"]

    @property
    def url(self):
        """The URL of the playlist"""
        return self["url"]

    @property
    def channel(self):
        """The channel the playlist is under, can be None"""
        return self["channel"]

    @property
    def created_on(self):
        """The time the playlist was created in seconds since epoch"""
        return utils.parse_timestamp(self["created_on"])

    @property
    def updated_on(self):
        """The time the playlist was last updated in seconds since epoch"""
        return utils.parse_timestamp(self["updated_on"])

    @property
    def permissions(self):
        """The permissions the ServicePHP user has on this playlist"""
        return self["permissions"]

    @property
    def num_items(self):
        """The number of items in the playlist"""
        return self["num_items"]

    @property
    def is_following(self):
        """TODO -> Bool"""
        return self["is_following"]

    @property
    def items(self):
        """The items of the playlist. TODO"""
        return self["items"]

    @property
    def extra(self):
        """TODO -> None, unknown"""
        return self["extra"]


class TwoFacAuth(JSONObj):
    """Handle and use the resposne data from the 2FA request"""

    def __init__(self, jsondata, servicephp):
        """Handle and use the resposne data from the 2FA request.

    Args:
        jsondata (dict): The JSON data block of the 2FA first step data.
        servicephp (ServicePHP): The ServicePHP object that spawned us.
        """

        JSONObj.__init__(self, jsondata)
        self.servicephp = servicephp

    def __repr__(self):
        """String to represent this object"""
        return f"{type(self).__name__}(<{self.servicephp.username}>)"

    @property
    def totp_id(self):
        """Is None when 2FA is disabled"""
        return self["totp_id"]

    @property
    def user_key(self):
        """Returns None when 2FA is disabled"""
        return self.get("user_key")

    @property
    def options(self) -> tuple:
        """The options we have for 2FA"""
        # 2FA is disabled it totp_id is None, so we have no options
        if not self.totp_id:
            return tuple()

        return tuple(
            option for option, available in self["options"].items()
            if available
            )

    def request_2fa_code(self, option: str = "authenticator"):
        """Tell Rumble to send the user a 2FA code

        Args:
            option (str): The 2FA option to use. Must be in self.options.
                Defaults to "authenticator" app.

        Returns:
            sent_to (str | None): The code destination, semi-censored.
                If 'authenticator' was used, returns None, as such apps
                generate the 2FA codes on demand."""

        assert self.options, "2FA is not enabled on this account"

        assert option in self.options, \
            f"Option '{option}' is not enabled on this account for 2FA"

        if option == "email":
            r = self.servicephp.sphp_request(
                "user.2fa.request_email_code",
                data={
                    "totp_id": self.totp_id,
                    "user_key": self.user_key,
                    },
                )
            return r.json()["data"]["sent_to"]

        if option == "phone":
            r = self.servicephp.sphp_request(
                "user.2fa.request_sms_code",
                data={
                    "totp_id": self.totp_id,
                    "user_key": self.user_key,
                    },
                )
            return r.json()["data"]["sent_to"]

        if option == "authenticator":
            # Nothing for us to do
            return None

        raise NotImplementedError(
            f"Cocorum does not support option '{option}' for 2FA."
            )


class ServicePHP:
    """Interact with Rumble's service.php API"""

    def __init__(self, username: str, session: (str | dict) = None):
        """Interact with Rumble's service.php API.

    Args:
        username (str): The username we will be working under.
        session (str | dict): A pre-existing session token.
            Defaults to None, await login.
            """

        # Set up initial auth data variables
        self.username = username
        self.session_cookie = None

        # Session is the token directly
        if isinstance(session, str):
            self.session_cookie = {static.Misc.session_token_key, session}

        # Session is a cookie dict
        elif isinstance(session, dict):
            assert session.get(static.Misc.session_token_key), f"Session cookie dict must have '{static.Misc.session_token_key}' as key."
            self.session_cookie = session

        # Session was passed but it is not anything we can use
        elif session is not None:
            raise ValueError(f"Session must be a token str or cookie dict, got {type(session)}")

        # If a session cookie was passed, test it
        assert not self.session_cookie\
            or utils.test_session_cookie(self.session_cookie), \
            "Session cookie is invalid."

        # Stored ID of the logged in user
        self.__user_id = None

    def __repr__(self):
        """String to represent this object"""
        return f"{type(self).__name__}(username={self.username}, <{'not ' * bool(self.session_cookie)}logged in>)"

    @property
    def user_id(self):
        """The numeric ID of the logged in user in base 10"""
        # We do not have a user ID, extract it from the unread notifications response
        if self.__user_id is None:
            j = self.sphp_request(
                "user.has_unread_notifications",
                method="GET",
                ).json()
            self.__user_id = utils.base_36_to_10(j["user"]["id"].removeprefix("_"))

        return self.__user_id

    @property
    def user_id_b10(self):
        """The numeric ID of the logged in user in base 10"""
        return self.user_id

    @property
    def user_id_b36(self):
        """The numeric ID of the logged in user in base 36"""
        return utils.base_10_to_36(self.user_id)

    def sphp_request(self, service_name: str, data: dict = {}, additional_params: dict = {}, logged_in=True, method="POST"):
        """Make a request to Service.PHP with common settings
        service_name: The name parameter of the specific PHP service
        data: Form data
        additional_params: Any additional query string parameters
        logged_in: The request should use the session cookie"""
        assert self.session_cookie or not logged_in, "Not logged in yet."

        params = {"name": service_name}
        params.update(additional_params)
        r = requests.request(
                method,
                static.URI.servicephp,
                params=params,
                data=data,
                headers=static.RequestHeaders.user_agent,
                cookies=self.session_cookie if logged_in else None,
                timeout=static.Delays.request_timeout,
                )
        assert r.status_code == 200, f"Service.PHP request for {service_name} failed: {r}\n{r.text}"
        # If the request json has a data -> success value, make sure it is True
        d = r.json().get("data")
        if isinstance(d, dict):
            assert d.get("success", True), f"Service.PHP request for {service_name} failed: \n{r.text}"
        # Data was not a dict but was not empty
        elif d:
            print(f"Service.PHP request for {service_name} did not fail but returned unknown data type {type(d)}: {d}")

        return r

    def get_hashed_password(self, password: str):
        """Use Rumble's salts to hash a pasword for login

    Args:
        password (str): The password to hash with the salts.

    Returns:
        hashed (str): The hashed password to use in the rest of the login.
        """

        # Get salts
        r = self.sphp_request(
            "user.get_salts",
            data={"username": self.username},
            logged_in=False,
            additional_params={"response_type": "session"}
            )
        salts = r.json()["data"]["salts"]

        return ",".join(utils.calc_password_hashes(password, salts))

    def get_2fa_first_step(self, password_hashes: str) -> TwoFacAuth:
        """Get 2FA info on our account as a first 2FA step

        Args:
            password_hashes (str): The hashed password.

        Returns:
            info (TwoFacAuth): Information on 2FA."""

        r = self.sphp_request(
            "user.2fa.first_step",
            data={
                "legacy_password": 1,  # TODO
                "login": self.username,
                "password": password_hashes,
                "redirect_url": static.URI.rumble_base,
                },
            logged_in=False
            )

        return TwoFacAuth(r.json()["data"], self)

    def login_basic(self, password: str):
        """Perform a basic password authentication as the first step of login.
            If successful, sets our session token and returns None.
            If incomplete, returns TwoFacAuth() for next step.

        Args:
            password (str): The password to login with.

        Returns:
            result (TwoFacAuth | None): The result of the first login step.
                None means login is complete.
            """

        # Get the password hash to start off
        ph = self.get_hashed_password(password)

        # Check for 2FA
        two_fac_info = self.get_2fa_first_step(ph)

        # 2FA is enabled
        if two_fac_info.totp_id:  # two_fac_auth.options:
            return two_fac_info

        # Get session token for non-2FA
        r = self.sphp_request(
                "user.login",
                data={
                    "username": self.username,

                    # Hash the password using the salts
                    "password_hashes": ph,
                    },
                logged_in=False,
                )

        j = r.json()
        session_token = j["data"]["session"]
        assert session_token, f"Login failed: No token returned\n{r.json()}"

        self.session_cookie = {static.Misc.session_token_key: session_token}
        return True

    def login_second_factor(self, two_fac_auth: TwoFacAuth, code: str) -> dict:
        """Complete login with a 2FA code.

        Args:
            two_fac_auth (TwoFacAuth): 2FA information on this account.
            code (str): The code to enter."""

        # If this fails, sphp_request will raise AssertionError
        r = self.sphp_request(
            "user.2fa.verify_totp",
            data={
                "code": code,
                "redirect_url": static.URI.rumble_base,
                "totp_id": two_fac_auth.totp_id,
                "user_key": two_fac_auth.user_key,
                },
            logged_in=False,
            )

        cookie_start = static.Misc.session_token_key + "="
        for piece in r.headers["Set-Cookie"].split():
            if piece.startswith(cookie_start):
                self.session_cookie = {static.Misc.session_token_key: piece.removeprefix(cookie_start).removesuffix(";")}
                return
        raise ValueError("Login failed: Did not find session token in 2FA response headers.")

    def chat_pin(self, stream_id, message, unpin: bool = False):
        """Pin or unpin a message in a chat.

    Args:
        stream_id (int, str): ID of the stream in base 10 or 36.
        message (int): Converting this to int must return a chat message ID.
        unpin (bool): If true, unpins a message instead of pinning it.
        """

        self.sphp_request(
            f"chat.message.{"un" * unpin}pin",
            data={
                "video_id": utils.ensure_b10(stream_id),
                "message_id": int(message),
                },
            )

    def mute_user(self, username: str, is_channel: bool = False, video: int = None, duration: int = None, total: bool = False):
        """Mute a user or channel by name.

    Args:
        username (str): The user to mute.
        is_channel (bool): Is this a channel name rather than a username?
        video (int): The video to mute the user on.
            Defaults to None.
        duration (int): How long the user will be muted for, in seconds.
            Defaults to infinity.
        total (bool): Is this a mute across all videos?
            Defaults to False, requires video if False.
            """

        self.sphp_request(
            "moderation.mute",
            data={
                "user_to_mute": username,
                "entity_type": ("user", "channel")[is_channel],
                "video": int(video),
                "duration": duration,
                "type": ("video", "total")[total],
                },
            )

    def unmute_user(self, record_id: int):
        """Unmute a user.

    Args:
        record_id: The numeric ID of the mute record to undo.
        """

        self.sphp_request(
            "moderation.unmute",
            data={
                "record_id": record_id,
                }
            )

    def _is_comment_elem(self, e):
        """Check if a beautifulsoup element is a comment.

    Args:
        e (bs4.Tag): The BeautifulSoup element to test.

    Returns:
        Result (bool): Did the element fit the criteria for being a comment?
        """

        return e.name == "li" and "comment-item" in e.get("class") and "comments-create" not in e.get("class")

    def comment_list(self, video_id):
        """Get the list of comments under a video.

    Args:
        video_id (str, int): The numeric ID of a video in base 10 or 36.

    Returns:
        Comments (list): A list of scraping.HTMLComment objects.
        """

        r = self.sphp_request(
            "comment.list",
            additional_params={
                "video": utils.ensure_b36(video_id),
                },
            method="GET",
            )
        soup = bs4.BeautifulSoup(r.json()["html"], features="html.parser")
        comment_elems = soup.find_all(self._is_comment_elem)
        return [scraping.HTMLComment(e, self) for e in comment_elems]

    def comment_add(self, video_id, comment: str, reply_id: int = 0):
        """Post a comment on a video.

    Args:
        video_id (int, str): The numeric ID of a video / stream in base 10 or 36.
        comment (str): What to say.
        reply_id (int): The ID of the comment to reply to.
            Defaults to zero (don't reply to anybody).

    Returns:
        Comment (APIComment): The comment, as parsed from the response data.
        """

        r = self.sphp_request(
                "comment.add",
                data={
                    "video": int(utils.ensure_b10(video_id)),
                    "reply_id": int(reply_id),
                    "comment": str(comment),
                    "target": "comment-create-1",
                    },
                )
        return APIComment(r.json()["data"], self)

    def comment_pin(self, comment_id: int, unpin: bool = False):
        """Pin or unpin a comment by ID.

    Args:
        comment_id (int): The numeric ID of the comment to pin/unpin.
        unpin (bool): If true, unpins instead of pinning comment.
        """

        self.sphp_request(
            f"comment.{"un" * unpin}pin",
            data={"comment_id": int(comment_id)},
            )

    def comment_delete(self, comment_id: int):
        """Delete a comment by ID.

    Args:
        comment_id (int): The numeric ID of the comment to delete.
        """

        self.sphp_request(
            "comment.delete",
            data={"comment_id": int(comment_id)},
            )

    def comment_restore(self, comment_id: int):
        """Restore a deleted comment by ID.

    Args:
        comment_id (int): The numeric ID of the comment to restore.
        """

        r = self.sphp_request(
            "comment.restore",
            data={"comment_id": int(comment_id)},
            )
        return APIComment(r.json()["data"], self)

    def rumbles(self, vote: int, item_id, item_type: int):
        """Post a like or dislike.

    Args:
        vote (int): -1, 0, or 1 (0 means clear vote).
        item_id (int): The numeric ID of whatever we are liking or disliking.
        item_type (int): 1 for video, 2 for comment.
        """

        r = self.sphp_request(
            "user.rumbles",
            data={
                "type": int(item_type),
                "id": utils.ensure_b10(item_id),
                "vote": int(vote),
                },
            )
        return APIContentVotes(r.json()["data"])

    def get_video_url(self, video_id):
        """Get the URL of a Rumble video.

    Args:
        video_id (int, str): The numeric ID of the video.

    Returns:
        URL (str): The URL of the video.
        """

        r = self.sphp_request(
            "media.share",
            additional_params={
                "video": utils.ensure_b36(video_id),
                "start": 0,
                },
            method="GET",
            )
        soup = bs4.BeautifulSoup(r.json()["html"], features="html.parser")
        elem = soup.find("div", attrs={"class": "fb-share-button share-fb"})
        return elem.attrs["data-url"]

    def playlist_add_video(self, playlist_id: str, video_id):
        """Add a video to a playlist.

    Args:
        playlist_id (str): The numeric ID of the playlist in base 64.
        video_id (int, str): The numeric ID of the video to add, in base 10 or 36.
        """

        print(self.sphp_request(
            "playlist.add_video",
            data={
                "playlist_id": str(playlist_id),
                "video_id": utils.ensure_b10(video_id),
                }
            ).text)

    def playlist_delete_video(self, playlist_id: str, video_id):
        """Remove a video from a playlist.

    Args:
        playlist_id (str): The numeric ID of the playlist in base 64.
        video_id (int, str): The numeric ID of the video to remove, in base 10 or 36.
        """

        print(self.sphp_request(
            "playlist.delete_video",
            data={
                "playlist_id": str(playlist_id),
                "video_id": utils.ensure_b10(video_id),
                }
            ).text)

    def playlist_add(self, title: str, description: str = "", visibility: str = "public", channel_id=None):
        """Create a new playlist.

    Args:
        title (str): The title of the playlist.
        description (str): Describe the playlist.
            Defaults to nothing.
        visibility (str): Set to public, unlisted, or private via string.
            Defaults to 'public'.
        channel_id (int, str): The ID of the channel to create the playlist under.
            Defaults to none.

    Returns:
        Playlist (APIPlaylist): The playlist as parsed from the response data.
        """

        r = self.sphp_request(
            "playlist.add",
            data = {
                "title": str(title),
                "description": str(description),
                "visibility": str(visibility),
                "channel_id": str(utils.ensure_b10(channel_id)) if channel_id else None,
            }
        )
        return APIPlaylist(r.json()["data"], self)

    def playlist_edit(self, playlist_id: str, title: str, description: str = "", visibility: str = "public", channel_id=None):
        """Edit the details of an existing playlist

    Args:
        playlist_id (str): The numeric ID of the playlist to edit in base 64.
        title (str): The title of the playlist.
        description (str): Describe the playlist.
            Defaults to nothing.
        visibility (str): Set to public, unlisted, or private via string.
            Defaults to 'public'.
        channel_id (int, str): The ID of the channel to have the playlist under.
            Defaults to none.

    Returns:
        Playlist (APIPlaylist): The playlist as parsed from the response data.
        """

        r = self.sphp_request(
            "playlist.edit",
            data = {
                "title": str(title),
                "description": str(description),
                "visibility": str(visibility),
                "channel_id": str(utils.ensure_b10(channel_id)) if channel_id else None,
                "playlist_id": str(playlist_id),
            }
        )
        return APIPlaylist(r.json()["data"], self)

    def playlist_delete(self, playlist_id: str):
        """Delete a playlist.

    Args:
        playlist_id (str): The numeric ID of the playlist to delete in base 64.
        """

        print(self.sphp_request(
            "playlist.delete",
            data={"playlist_id": str(playlist_id)},
            ).text)

    def raid_confirm(self, stream_id):
        """Confirm a raid, previously set up by command.

    Args:
        stream_id (int, str): The numeric ID of the stream to confirm the raid from, in base 10 or 36.
        """

        self.sphp_request(
            "raid.confirm",
            data={"video_id": utils.ensure_b10(stream_id)},
            )
