#!/usr/bin/env python3
"""Scraping for Cocorum

Classes and utilities for extracting data from HTML, including that returned by the API.
S.D.G."""

import requests
import bs4
from . import static
from . import utils

class HTMLObj:
    """Abstract object scraped from bs4 HTML"""
    def __init__(self, elem):
        """Abstract object scraped from bs4 HTML

    Args:
        elem (bs4.Tag): The BeautifulSoup element to base our data on.
        """

        self._elem = elem

    def __getitem__(self, key):
        """Get a key from the element attributes

    Args:
        key (str): A valid attribute name.
        """

        return self._elem.attrs[key]

class HTMLUserBadge(HTMLObj):
    """A user badge as extracted from a bs4 HTML element"""
    def __init__(self, elem):
        """A user badge as extracted from a bs4 HTML element.

    Args:
        elem (bs4.Tag): The badge <img> element
        """

        super().__init__(elem)
        self.slug = elem.attrs["src"].split("/")[-1:elem.attrs["src"].rfind("_")]
        self.__icon = None

    def __eq__(self, other):
        """Check if this badge is equal to another.

    Args:
        other (str, HTMLUserBadge): Object to compare to.

    Returns:
        Comparison (bool, None): Did it fit the criteria?
        """

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

class HTMLComment(HTMLObj):
    """A comment on a video as returned by service.php comment.list"""
    def __init__(self, elem):
        """A comment on a video as returned by service.php comment.list

    Args:
        elem (bs4.Tag): The <li> element of the comment.
        """

        super().__init__(elem)

        #Badges of the user who commented if we have them
        badges_unkeyed = (HTMLUserBadge(badge_elem) for badge_elem in self._elem.find_all("li", attrs = {"class" : "comments-meta-user-badge"}))
        self.user_badges = {badge.slug : badge for badge in badges_unkeyed}

    def __int__(self):
        """The comment in integer form (its ID)"""
        return self.comment_id

    def __str__(self):
        """The comment as a string (its text)"""
        return self.text

    def __eq__(self, other):
        """Determine if this comment is equal to another.

    Args:
        other (int, str, HTMLComment): Object to compare to.

    Returns:
        Comparison (bool, None): Did it fit the criteria?
        """

        #Check for direct matches first
        if isinstance(other, int):
            return self.comment_id_b10 == other
        if isinstance(other, str):
            return str(self) == other

        #Check for object attributes to match to
        if hasattr(other, "comment_id"):
            return self.comment_id_b10 == utils.ensure_b10(other.comment_id)

        #Check conversion to integer last
        if hasattr(other, "__int__"):
            return self.comment_id_b10 == int(other)

    @property
    def is_first(self):
        """Is this comment the first one?"""
        return "comment-item-first" in self["class"]

    @property
    def comment_id(self):
        """The numeric ID of the comment in base 10"""
        return int(self["data-comment-id"])

    @property
    def comment_id_b10(self):
        """The base 10 ID of the comment"""
        return self.comment_id

    @property
    def comment_id_b36(self):
        """The base 36 ID of the comment"""
        return utils.base_10_to_36(self.comment_id)

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
        return HTMLContentVotes(self._elem.find("div", attrs = {"class" : "rumbles-vote"}))

class HTMLContentVotes(HTMLObj):
    """Votes made on content"""

    def __int__(self):
        """The integer form of the content votes"""
        return self.score

    def __str__(self):
        """The string form of the content votes"""
        #return self.score_formatted
        return str(self.score)

    def __eq__(self, other):
        """Determine if this content votes is equal to another.

    Args:
        other (int, str, HTMLContentVotes): Object to compare to.

    Returns:
        Comparison (bool, None): Did it fit the criteria?
        """

        #Check for direct matches first
        if isinstance(other, int):
            return self.score == other
        if isinstance(other, str):
            return str(self) == other

        #Check for object attributes to match to
        if hasattr(other, "score"):
            #if hasattr(other, "content_id") and hasattr(other, "content_type"):
            #    return self.score, self.content_id, self.content_type == other.score, other.content_id, other.content_type
            return self.score == other.score

        #Check conversion to integer last
        if hasattr(other, "__int__"):
            return self.score == int(other)

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

class HTMLPlaylist(HTMLObj):
    """A playlist as obtained from HTML data"""
    def __init__(self, elem, scraper):
        """A playlist as obtained from HTML data.

    Args:
        elem (bs4.Tag): The playlist class = "thumbnail__grid-item" element.
        scraper (Scraper): The HTML scraper object that spawned us.
        """

        super().__init__(elem)

        #The Scraper object that created this one
        self.scraper = scraper

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

    def __eq__(self, other):
        """Determine if this playlist is equal to another.

    Args:
        other (int, str, HTMLPlaylist): Object to compare to.

    Returns:
        Comparison (bool, None): Did it fit the criteria?
        """

        #Check for direct matches first
        if isinstance(other, int):
            return self.playlist_id_b10 == other
        if isinstance(other, str):
            return str(other) == self.playlist_id_b36

        #Check for object attributes to match to
        if hasattr(other, "playlist_id"):
            return self.playlist_id_b10 == utils.ensure_b10(other.playlist_id)

        #Check conversion to integer last, in case another ID or something happens to match
        if hasattr(other, "__int__"):
            return self.playlist_id_b10 == int(other)

    @property
    def _pagesoup(self):
        """The loaded page of the playlist"""
        if not self.__pagesoup:
            self.__pagesoup = self.scraper.soup_request(self.url)

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

class HTMLChannel(HTMLObj):
    """Channel under a user as extracted from their channels page"""

    def __str__(self):
        """The channel as a string (its slug)"""
        return self.slug

    def __int__(self):
        """The channel as an integer (its numeric ID)"""
        return self.channel_id_b10

    def __eq__(self, other):
        """Determine if this channel is equal to another.

    Args:
        other (int, str, HTMLChannel): Object to compare to.

    Returns:
        Comparison (bool, None): Did it fit the criteria?
        """

        #Check for direct matches first
        if isinstance(other, int):
            return self.channel_id_b10 == other
        if isinstance(other, str):
            return str(other) in (self.slug, self.channel_id_b36)

        #Check for object attributes to match to
        if hasattr(other, "channel_id"):
            return self.channel_id_b10 == utils.ensure_b10(other.channel_id)
        if hasattr(other, "slug"):
            return self.slug == other.slug

        #Check conversion to integer last, in case an ID or something happens to match but the other is not actually a channel
        if hasattr(other, "__int__"):
            return self.channel_id_b10 == int(other)

    @property
    def slug(self):
        """The unique string ID of the channel"""
        return self["data-slug"]

    @property
    def channel_id(self):
        """The numeric ID of the channel in base 10"""
        return int(self["data-id"])

    @property
    def channel_id_b10(self):
        """The numeric ID of the channel in base 10"""
        return self.channel_id

    @property
    def channel_id_b36(self):
        """The numeric ID of the channel in base 36"""
        return utils.base_10_to_36(self.channel_id)

    @property
    def title(self):
        """The title of the channel"""
        return self["data-title"]

class HTMLVideo(HTMLObj):
    """Video on a user or channel page as extracted from the page's HTML"""
    def __init__(self, elem):
        """Video on a user or channel page as extracted from the page's HTML.

    Args:
        elem (bs4.Tag): The class = "thumbnail__grid-item" video element.
        """

        super().__init__(elem)

        #The binary data of our thumbnail
        self.__thumbnail = None

    def __int__(self):
        """The video as an integer (it's numeric ID)"""
        return self.video_id_b10

    def __str__(self):
        """The video as a string (it's ID in base 36)"""
        return self.video_id_b36

    def __eq__(self, other):
        """Determine if this video is equal to another.

    Args:
        other (int, str, HTMLVideo): Object to compare to.

    Returns:
        Comparison (bool, None): Did it fit the criteria?
        """

        #Check for direct matches first
        if isinstance(other, int):
            return self.video_id_b10 == other
        if isinstance(other, str):
            return str(other) == self.video_id_b36

        #Check for object attributes to match to
        if hasattr(other, "video_id"):
            return self.video_id_b10 == utils.ensure_b10(other.video_id)
        if hasattr(other, "stream_id"):
            return self.video_id_b10 == utils.ensure_b10(other.stream_id)

        #Check conversion to integer last, in case another ID or something happens to match
        if hasattr(other, "__int__"):
            return self.video_id_b10 == int(other)

    @property
    def video_id(self):
        """The numeric ID of the video in base 10"""
        return int(self._elem.get("data-video-id"))

    @property
    def video_id_b10(self):
        """The numeric ID of the video in base 10"""
        return self.video_id

    @property
    def video_id_b36(self):
        """The numeric ID of the video in base 36"""
        return utils.base_10_to_36(self.video_id)

    @property
    def thumbnail_url(self):
        """The URL of the video's thumbnail image"""
        return self._elem.find("img", attrs = {"class" : "thumbnail__image"}).get("src")

    @property
    def thumbnail(self):
        """The video thumbnail as a binary string"""
        if not self.__thumbnail: #We never queried the thumbnail before
            response = requests.get(self.thumbnail_url, timeout = static.Delays.request_timeout)
            assert response.status_code == 200, "Status code " + str(response.status_code)

            self.__thumbnail = response.content

        return self.__thumbnail

    @property
    def video_url(self):
        """The URL of the video's viewing page"""
        return static.URI.rumble_base + self._elem.find("a", attrs = {"class" : "videostream__link link"}).get("href")

    @property
    def title(self):
        """The title of the video"""
        return self._elem.find("h3", attrs = {"class" : "thumbnail__title"}).get("title")

    @property
    def upload_date(self):
        """The time that the video was uploaded, in seconds since epoch"""
        return utils.parse_timestamp(self._elem.find("time", attrs = {"class" : "videostream__data--subitem videostream__time"}).get("datetime"))

class Scraper:
    """Scraper for general information"""
    def __init__(self, servicephp):
        """Scraper for general information.

    Args:
        servicephp (ServicePHP): A ServicePHP instance, for authentication.
        """

        self.servicephp = servicephp

    @property
    def session_cookie(self):
        """The session cookie we are logged in with"""
        return self.servicephp.session_cookie

    @property
    def username(self):
        """Our username"""
        return self.servicephp.username

    def soup_request(self, url: str):
        """Make a GET request to a URL, and return HTML beautiful soup for scraping.

    Args:
        url (str): The URL to query.

    Returns:
        Soup (bs4.BeautifulSoup): The webpage at the URL, logged-in version.
        """

        r = requests.get(
            url,
            cookies = self.session_cookie,
            timeout = static.Delays.request_timeout,
            headers = static.RequestHeaders.user_agent,
            )

        assert r.status_code == 200, f"Fetching page {url} failed: {r}\n{r.text}"
        return bs4.BeautifulSoup(r.text, features = "html.parser")

    def get_muted_user_record(self, username: str = None):
        """Get the record IDs for mutes.

    Args:
        username (str): Username to find record ID for.
            Defaults to None.

    Returns:
        Record (int, dict): Either the single user's mute record ID, or a dict of all username:mute record ID pairs.
        """

        #The page we are on
        pagenum = 1

        #username : record ID
        record_ids = {}

        #While there are more pages
        while True:
            #Get the next page of mutes and search for mute buttons
            soup = self.soup_request(static.URI.mutes_page.format(page = pagenum))
            elems = soup.find_all("button", attrs = {"class" : "unmute_action button-small"})

            #We reached the last page
            if not elems:
                break

            #Get the record IDs per username from each button
            for e in elems:
                #We were searching for a specific username and found it
                if username and e.attrs["data-username"] == username:
                    return e.attrs["data-record-id"]

                record_ids[e.attrs["data-username"]] = int(e.attrs["data-record-id"])

            #Turn the page
            pagenum +=1

        #Only return record IDs if we weren't searching for a particular one
        if not username:
            return record_ids

        #We were searching for a user and did not find them
        return None

    def get_channels(self, username: str = None):
        """Get all channels under a username.

    Args:
        username (str): The username to get the channels under.
            Defaults to None, use our own username.

    Returns:
        Channels (list): List of HTMLChannel objects.
        """

        if not username:
            username = self.username

        #Get the page of channels and parse for them
        soup = self.soup_request(static.URI.channels_page.format(username = username))
        elems = soup.find_all("div", attrs = {"data-type" : "channel"})
        return [HTMLChannel(e) for e in elems]

    def get_videos(self, username = None, is_channel = False, max_num = None):
        """Get the videos under a user or channel.

    Args:
        username (str): The name of the user or channel to search under.
            Defaults to ourselves.
        is_channel (bool): Is this a channel instead of a userpage?
            Defaults to False.
        max_num (int): The maximum number of videos to retrieve, starting from the newest.
            Defaults to None, return all videos.
            Note, rounded up to the nearest page.

    Returns:
        Videos (list): List of HTMLVideo objects.
        """

        #default to the logged-in username
        if not username:
            username = self.username

        #If this is a channel username, we will need a slightly different URL
        uc = ("user", "c")[is_channel]

        #The base userpage URL currently has all their videos / livestreams on it
        url_start = f"{static.URI.rumble_base}/{uc}/{username}"

        #Start the loop with:
        #- no videos found yet
        #- the assumption that there will be new video elements
        #- a current page number of 1
        videos = []
        new_video_elems = True
        pagenum = 1
        while new_video_elems and (not max_num or len(videos) < max_num):
            #Get the next page of videos
            soup = self.soup_request(f"{url_start}?page={pagenum}")

            #Search for video listings
            new_video_elems = soup.find_all("div", attrs = {"class" : "videostream thumbnail__grid--item"})

            #We found some video listings
            if new_video_elems:
                videos += [HTMLVideo(e) for e in new_video_elems]

            #Turn the page
            pagenum += 1

        return videos

    def get_playlists(self):
        """Get the playlists under the logged in user"""
        soup = self.soup_request(static.URI.playlists_page)
        return [HTMLPlaylist(elem, self) for elem in soup.find_all("div", attrs = {"class" : "playlist"})]
