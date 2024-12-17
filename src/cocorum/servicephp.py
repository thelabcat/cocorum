#!/usr/bin/env python3
"""Service.PHP interactions

Control Rumble via Service.PHP
S.D.G."""

import requests
import bs4
from . import static
from . import utils
from . import JSONObj

class HTMLObj:
    """Abstract object scraped from bs4 HTML"""
    def __init__(self, elem):
        """Pass the bs4 base element"""
        self._elem = elem

    def __getitem__(self, key):
        """Get a key from the element attributes"""
        return self._elem.attrs[key]

class APIUserBadge(JSONObj):
    """A badge of a user as returned by the API"""
    def __init__(self, slug, jsondata):
        """Pass the slug, and the object JSON"""
        super().__init__(jsondata)
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
        return static.URI.rumble_base + self["icons"][static.Misc.badge_icon_size]

    @property
    def icon(self):
        """The badge's icon as a bytestring"""
        if not self.__icon: #We never queried the icon before
            #TODO make the timeout configurable
            response = requests.get(self.icon_url, timeout = static.Delays.request_timeout)
            assert response.status_code == 200, "Status code " + str(response.status_code)

            self.__icon = response.content

        return self.__icon

class ScrapedUserBadge(HTMLObj):
    """A user badge as extracted from a bs4 HTML element"""
    def __init__(self, elem):
        """Pass the bs4 badge img element"""
        super().__init__(elem)
        self.slug = elem.attrs["src"].split("/")[-1:elem.attrs["src"].rfind("_")]
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
        """The string label of the badge in whatever language the Service.PHP agent used"""
        return self["title"]

    @property
    def icon_url(self):
        """The URL of the badge's icon"""
        return static.URI.rumble_base + self["src"]

    @property
    def icon(self):
        """The badge's icon as a bytestring"""
        if not self.__icon: #We never queried the icon before
            #TODO make the timeout configurable
            response = requests.get(self.icon_url, timeout = static.Delays.request_timeout)
            assert response.status_code == 200, "Status code " + str(response.status_code)

            self.__icon = response.content

        return self.__icon

class APIComment(JSONObj):
    """A comment on a video as returned by a successful attempt to make it"""
    def __init__(self, jsondata):
        """Pass the JSON block for a single comment"""
        super().__init__(jsondata)

        #Badges of the user who commented if we have them
        if self.get("comment_user_badges"):
            self.user_badges = {slug : APIUserBadge(slug, data) for slug, data in self["comment_user_badges"].items()}

    def __int__(self):
        """The comment in integer form (its ID)"""
        return self.comment_id

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

class ScrapedComment(HTMLObj):
    """A comment on a video as returned by service.php comment.list"""
    def __init__(self, elem):
        """Pass the bs4 li element of the comment"""
        super().__init__(elem)

        #Badges of the user who commented if we have them
        badges_unkeyed = (ScrapedUserBadge(badge_elem) for badge_elem in self._elem.find_all("li", attrs = {"class" : "comments-meta-user-badge"}))
        self.user_badges = {badge.slug : badge for badge in badges_unkeyed}

    def __int__(self):
        """The comment in integer form (its ID)"""
        return self.comment_id

    @property
    def is_first(self):
        """Is this comment the first one?"""
        return "comment-item-first" in self["class"]

    @property
    def comment_id(self):
        """The numeric ID of the comment"""
        return int(self["data-comment-id"])

    @property
    def text(self):
        """The text of the comment"""
        return self._elem.find("p", attrs = {"class" : "comment-text"}).string

    @property
    def username(self):
        """The name of the user who commented"""
        return self["data-username"]

    @property
    def entity_type(self):
        """Wether the comment was made by a user or a channel"""
        return self["data-entity-type"]

    @property
    def video_id(self):
        """The base 10 ID of the video the comment was posted on"""
        return self["data-video-fid"]

    @property
    def video_id_b10(self):
        """The base 10 ID of the video the comment was posted on"""
        return self.video_id

    @property
    def video_id_b36(self):
        """The base 36 ID of the video the comment was posted on"""
        return utils.base_10_to_36(self.video_id)

    @property
    def actions(self):
        """Allowed actions on this comment based on the login used to retrieve it"""
        return self["data-actions"].split(",")

    @property
    def rumbles(self):
        """The votes on this comment"""
        return ScrapedContentVotes(self._elem.find("div", attrs = {"class" : "rumbles-vote"}))

class APIContentVotes(JSONObj):
    """Votes made on content"""
    def __int__(self):
        """The integer form of the content votes"""
        return self.score

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

class ScrapedContentVotes(HTMLObj):
    """Votes made on content"""

    def __int__(self):
        """The integer form of the content votes"""
        return self.score

    def __str__(self):
        """The string form of the content votes"""
        #return self.score_formatted
        return str(self.score)

    @property
    def score(self):
        """Summed score of the content"""
        return int(self._elem.find("span", attrs = {"class" : "rumbles-count"}).string)

    @property
    def content_type(self):
        """The type of content being voted on"""
        return int(self["data-type"])

    @property
    def content_id(self):
        """The numerical ID of the content being voted on"""
        return int(self["data-id"])

class APIUser(JSONObj):
    """User data as returned by the API"""
    def __init__(self, jsondata):
        """Pass the JSON data of a user"""
        super().__init__(jsondata)

        #Our profile picture data
        self.__picture = None

    def __int__(self):
        """The user as an integer (it's ID in base 10)"""
        return self.user_id_b10

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
        if not self.picture_url: #The profile picture is blank
            return b''

        if not self.__picture: #We never queried the profile pic before
            response = requests.get(self.picture_url, timeout = static.Delays.request_timeout)
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

class APIPlaylist(JSONObj):
    """Playlist as returned by the API"""
    def __init__(self, jsondata):
        """Pass the JSON data of a playlist"""
        super().__init__(jsondata)
        self.user = APIUser(jsondata["user"])

    def __int__(self):
        """The playlist as an integer (it's ID in base 10)"""
        return self.playlist_id_b10

    def __str__(self):
        """The playlist as a string (it's ID in base 36)"""
        return self.playlist_id_b36

    @property
    def playlist_id(self):
        """The numeric playlist ID in base 36"""
        return self["id"]

    @property
    def playlist_id_b36(self):
        """The numeric ID of the playlist in base 36"""
        return self.playlist_id

    @property
    def playlist_id_b10(self):
        """The numeric ID of the playlist in base 10"""
        return utils.base_36_to_10(self.playlist_id)

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

class ScrapedPlaylist(HTMLObj):
    """A playlist as obtained from HTML data"""
    def __init__(self, elem, sphp):
        """Pass the playlist thumbnail__grid-item bs4 element, and ServicePHP"""
        super().__init__(elem)

        self.sphp = sphp

        #The binary data of our thumbnail
        self.__thumbnail = None

        #The loaded page of the playlist
        self.__pagesoup = None

    def __int__(self):
        """The playlist as an integer (it's ID in base 10)"""
        return self.playlist_id_b10

    def __str__(self):
        """The playlist as a string (it's ID in base 36)"""
        return self.playlist_id_b36

    @property
    def _pagesoup(self):
        """The loaded page of the playlist"""
        if not self.__pagesoup:
            r = requests.get(
                self.url,
                cookies = self.sphp.session_cookie,
                timeout = static.Delays.request_timeout,
                headers = static.RequestHeaders.user_agent,
                )
            assert r.status_code == 200, "Request to playlist page failed: {r}"
            self.__pagesoup = bs4.BeautifulSoup(r.text, features = "html.parser")
        return self.__pagesoup

    @property
    def thumbnail_url(self):
        """The url of the playlist's thumbnail image"""
        return self._elem.find("img", attrs = {"class" : "thumbnail__image"}).get("src")

    @property
    def thumbnail(self):
        """The playlist thumbnail as a binary string"""
        if not self.__thumbnail: #We never queried the thumbnail before
            response = requests.get(self.thumbnail_url, timeout = static.Delays.request_timeout)
            assert response.status_code == 200, "Status code " + str(response.status_code)

            self.__thumbnail = response.content

        return self.__thumbnail

    @property
    def _url_raw(self):
        """The URL of the playlist page (without Rumble base URL)"""
        return self._elem.find("a", attrs = {"class" : "playlist__name link"}).get("href")

    @property
    def url(self):
        """The URL of the playlist page """
        return static.URI.rumble_base + self._url_raw

    @property
    def playlist_id(self):
        """The numeric ID of the playlist in base 36"""
        return self._url_raw.split("/")[-1]

    @property
    def playlist_id_b36(self):
        """The numeric ID of the playlist in base 36"""
        return self.playlist_id

    @property
    def playlist_id_b10(self):
        """The numeric ID of the playlist in base 10"""
        return utils.base_36_to_10(self.playlist_id)

    @property
    def _channel_url_raw(self):
        """The URL of the channel the playlist under (without base URL)"""
        return self._elem.find("a", attrs = {"class" : "channel__link link"}).get("href")

    @property
    def channel_url(self):
        """The URL of the base user or channel the playlist under"""
        return static.URI.rumble_base + self._channel_url_raw

    @property
    def is_under_channel(self):
        """Is this playlist under a channel?"""
        return self._channel_url_raw.startswith("/c/")

    @property
    def title(self):
        """The title of the playlist"""
        return self._pagesoup.find("h1", attrs = {"class" : "playlist-control-panel__playlist-name"}).string.strip()

    @property
    def description(self):
        """The description of the playlist"""
        return self._pagesoup.find("div", attrs = {"class" : "playlist-control-panel__description"}).string.strip()

    @property
    def visibility(self):
        """The visibility of the playlist"""
        return self._pagesoup.find("span", attrs = {"class" : "playlist-control-panel__visibility-state"}).string.strip().lower()

    @property
    def num_items(self):
        """The number of items in the playlist"""
        #This is doable but I just don't care right now
        NotImplemented

class ServicePHP:
    """Interact with Rumble's service.php API"""
    def __init__(self, username: str = None, password: str = None, session = None):
        """Pass the username and password or a session token (accepts cookie dict or base string)"""
        #Save the username and password
        self.username, self.password = username, password

        #Session is the token directly
        if isinstance(session, str):
            self.session_cookie = {static.Misc.session_token_key, session}
        #Session is a cookie dict
        elif isinstance(session, dict):
            assert session.get(static.Misc.session_token_key), f"Session cookie dict must have '{static.Misc.session_token_key}' as key."
            self.session_cookie = session
        #Session was passed but it is not anything we can use
        elif session is not None:
            raise ValueError(f"Session must be a token str or cookie dict, got {type(session)}")
        #Session was not passed, but credentials were
        elif username and password:
            self.session_cookie = self.login(username, password)
        #Neither session nor credentials were passed:
        else:
            raise ValueError("Must pass either userame and password, or a session token")

        assert utils.test_session_cookie(self.session_cookie), "Session cookie is invalid."

        #Stored ID of the logged in user
        self.__user_id = None

    @property
    def user_id(self):
        """The numeric ID of the logged in user in base 10"""
        #We do not have a user ID, extract it from the unread notifications response
        if self.__user_id is None:
            j = self.sphp_request(
                "user.has_unread_notifications",
                method = "GET",
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

    def sphp_request(self, service_name: str, data: dict = {}, additional_params: dict = {}, logged_in = True, method = "POST"):
        """Make a request to Service.PHP with common settings
        service_name: The name parameter of the specific PHP service
        data: Form data
        additional_params: Any additional query string parameters
        logged_in: The request should use the session cookie"""
        params = {"name" : service_name}
        params.update(additional_params)
        r = requests.request(
                method,
                static.URI.servicephp,
                params = params,
                data = data,
                headers = static.RequestHeaders.user_agent,
                cookies = self.session_cookie if logged_in else None,
                timeout = static.Delays.request_timeout,
                )
        assert r.status_code == 200, f"Service.PHP request for {service_name} failed: {r}\n{r.text}"
        #If the request json has a data -> success value, make sure it is True
        d = r.json().get("data")
        if isinstance(d, dict):
            assert d.get("success", True), f"Service.PHP request for {service_name} failed: \n{r.text}"
        #Data was not a dict but was not empty
        elif d:
            print(f"Service.PHP request for {service_name} did not fail but returned unknown data type {type(d)}: {d}")

        return r

    def login(self, username, password):
        """Obtain a session cookie and user ID from username and password"""
        #Get salts
        r = self.sphp_request(
                "user.get_salts",
                data = {"username": username},
                logged_in = False,
                )
        salts = r.json()["data"]["salts"]

        #Get session token
        r = self.sphp_request(
                "user.login",
                data = {
                    "username": username,

                    #Hash the password using the salts
                    "password_hashes": ",".join(utils.calc_password_hashes(password, salts)),
                    },
                logged_in = False,
                )
        j = r.json()
        session_token = j["data"]["session"]
        assert session_token, f"Login failed: No token returned\n{r.json()}"

        return {static.Misc.session_token_key: session_token}

    def chat_pin(self, stream_id, message, unpin: bool = False):
        """Pin or unpin a message in a chat
        stream_id: ID of the stream in base 10 or 36
        message: int(this) must return a chat message ID
        unpin: If true, unpins a message instead"""
        self.sphp_request(
            f"chat.message.{"un" * unpin}pin",
            data = {
                "video_id": utils.ensure_b10(stream_id),
                "message_id": int(message),
                },
            )

    def mute_user(self, username: str, is_channel: bool = False, video: int = None, duration: int = None, total: bool = False):
        """Mute a user or channel by name"""
        self.sphp_request(
            "moderation.mute",
            data = {
                "user_to_mute": username,
                "entity_type": ("user", "channel")[is_channel],
                "video": int(video),
                "duration": duration,
                "type": ("video", "total")[total],
                },
            )

    def unmute_user(self, record_id: int):
        """Unmute a user by record ID"""
        self.sphp_request(
            "moderation.unmute",
            data = {
                "record_id" : record_id,
                }
            )

    def is_comment_elem(self, e):
        """Check if a beautifulsoup element is a comment"""
        return e.name == "li" and "comment-item" in e.get("class") and "comments-create" not in e.get("class")

    def comment_list(self, video_id):
        """Get the list of comments under a video"""
        r = self.sphp_request(
            "comment.list",
            additional_params = {
                "video" : utils.ensure_b36(video_id),
                },
            method = "GET",
            )
        soup = bs4.BeautifulSoup(r.json()["html"], features = "html.parser")
        comment_elems = soup.find_all(self.is_comment_elem)
        return [ScrapedComment(e) for e in comment_elems]

    def comment_add(self, video_id: int, comment: str, reply_id: int = 0):
        """Post a comment on a video
        video_id: The numeric ID of a video / stream
        comment: What to say
        reply_id: The ID of the comment to reply to
            Defaults to zero (don't reply to anybody)"""
        r = self.sphp_request(
                "comment.add",
                data = {
                    "video": int(video_id),
                    "reply_id": int(reply_id),
                    "comment": str(comment),
                    "target": "comment-create-1",
                    },
                )
        return APIComment(r.json()["data"])

    def comment_pin(self, comment_id: int, unpin: bool = False):
        """Pin or unpin a comment by ID
        comment_id: Integer comment ID
        unpin: If true, unpins instead of pinning comment"""
        self.sphp_request(
            f"comment.{"un" * unpin}pin",
            data = {"comment_id": int(comment_id)},
            )

    def comment_delete(self, comment_id: int):
        """Delete a comment by ID"""
        self.sphp_request(
            "comment.delete",
            data = {"comment_id": int(comment_id)},
            )

    def comment_restore(self, comment_id: int):
        """Restore a deleted comment by ID"""
        r = self.sphp_request(
            "comment.restore",
            data = {"comment_id": int(comment_id)},
            )
        return APIComment(r.json()["data"])

    def rumbles(self, vote: int, item_id, item_type: int):
        """Post a like or dislike
        vote: -1, 0, or 1
        item_id: The numeric ID of whatever we are liking or disliking
        item_type: 1 for video, 2 for comment"""
        r = self.sphp_request(
            "user.rumbles",
            data = {
                "type" : int(item_type),
                "id" : utils.ensure_b10(item_id),
                "vote" : int(vote),
                },
            )
        return APIContentVotes(r.json()["data"])

    def get_video_url(self, video_id):
        """Get the URL of a Rumble video from Service.PHP's media.share"""
        r = self.sphp_request(
            "media.share",
            additional_params = {
                "video" : utils.ensure_b36(video_id),
                "start" : 0,
                },
            method = "GET",
            )
        soup = bs4.BeautifulSoup(r.json()["html"], features = "html.parser")
        elem = soup.find("div", attrs = {"class" : "fb-share-button share-fb"})
        return elem.attrs["data-url"]

    def get_playlists(self):
        """Get the playlists under the logged in user"""
        r = requests.get(
            "https://rumble.com/my-library/playlists",
            cookies = self.session_cookie,
            timeout = static.Delays.request_timeout,
            headers = static.RequestHeaders.user_agent,
            )

        assert r.status_code == 200, f"Fetching playlist page failed: {r}"
        soup = bs4.BeautifulSoup(r.text, features = "html.parser")
        return [ScrapedPlaylist(elem, self) for elem in soup.find_all("div", attrs = {"class" : "playlist"})]

    def playlist_add_video(self, playlist_id: str, video_id: int):
        """Add a video to a playlist"""
        print(self.sphp_request(
            "playlist.add_video",
            data = {
                "playlist_id": str(playlist_id),
                "video_id": utils.ensure_b10(video_id),
                }
            ).text)

    def playlist_delete_video(self, playlist_id: str, video_id: int):
        """Remove a video from a playlist"""
        print(self.sphp_request(
            "playlist.delete_video",
            data = {
                "playlist_id": str(playlist_id),
                "video_id": utils.ensure_b10(video_id),
                }
            ).text)

    def playlist_add(self, title: str, description: str = "", visibility: str = "public", channel_id: int = None):
        """Create a new playlist
        title: The title of the playlist.
        description: Describe the playlist.
            Defaults to nothing.
        visibility: Set to public, unlisted, or private via string.
            Defaults to public.
        channel_id: The ID of the channel to create the playlist under.
            Defaults to none."""
        r = self.sphp_request(
            "playlist.add",
            data = {
                "title": str(title),
                "description": str(description),
                "visibility": str(visibility),
                "channel_id": str(utils.ensure_b10(channel_id)) if channel_id else None,
            }
        )
        return APIPlaylist(r.json()["data"])

    def playlist_edit(self, playlist_id: str, title: str, description: str = "", visibility: str = "public", channel_id: int = None):
        """Edit the details of an existing playlist
        playlist_id: The ID of the playlist to edit.
        title: The title of the playlist.
        description: Describe the playlist.
            Defaults to nothing.
        visibility: Set to public, unlisted, or private via string.
            Defaults to public.
        channel_id: The ID of the channel to create the playlist under.
            Defaults to none."""

        r = self.sphp_request(
            "playlist.edit",
            data = {
                "title": str(title),
                "description": str(description),
                "visibility": str(visibility),
                "channel_id": str(utils.ensure_b10(channel_id)) if channel_id else None,
                "playlist_id": utils.ensure_b36(playlist_id),
            }
        )
        return APIPlaylist(r.json()["data"])

    def playlist_delete(self, playlist_id: str):
        """Delete a playlist"""
        print(self.sphp_request(
            "playlist.delete",
            data = {"playlist_id" : utils.ensure_b36(playlist_id)},
            ).text)
