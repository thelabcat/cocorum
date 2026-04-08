#!/usr/bin/env python3
"""Base handles

Abstract classes for objects with methods that are common between API and HTML versions

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

from typing import Optional, SupportsInt, TYPE_CHECKING
import requests
from . import static
from . import utils
if TYPE_CHECKING:
    from .servicephp import APIComment, APIPlaylist


class BaseUserBadge:
    """A badge on a username"""

    def __eq__(self, other) -> bool:
        """Check if this badge is equal to another.

    Args:
        other (str, HTMLUserBadge): Object to compare to.

    Returns:
        Comparison (bool, None): Did it fit the criteria?
        """

        # Check if the string is either our slug or our label in any language
        if isinstance(other, str):
            return other in (self.slug, self.label.values())

        # Check if the compared object has the same slug, if it has one
        if hasattr(other, "slug"):
            return self.slug == other.slug

        return False

    def __str__(self) -> str:
        """The chat user badge in string form"""
        return self.slug

    def __repr__(self) -> str:
        """String to represent this object"""
        return f"{type(self).__name__}(slug='{self.slug}')"

    @property
    def icon(self) -> bytes:
        """The badge's icon as a bytestring"""
        if not self.__icon:  # We never queried the icon before
            # TODO make the timeout configurable
            response = requests.get(
                self.icon_url, timeout=static.Delays.request_timeout)
            assert response.status_code == 200, "Status code " + \
                str(response.status_code)

            self.__icon = response.content

        return self.__icon


class BaseComment:
    """A comment on a Rumble video"""

    def __int__(self) -> int:
        """The comment in integer form (its ID)"""
        return self.comment_id

    def __str__(self) -> str:
        """The comment as a string (its text)"""
        return self.text

    @property
    def comment_id_b10(self) -> int:
        """The base 10 ID of the comment"""
        assert isinstance(
            self.comment_id, int), "Contact the Cocorum developers, this is probably their mistake"
        return self.comment_id

    @property
    def comment_id_b36(self) -> str:
        """The base 36 ID of the comment"""
        return utils.base_10_to_36(self.comment_id)

    def __eq__(self, other) -> bool:
        """Determine if this comment is equal to another.

    Args:
        other (int, str, HTMLComment, APIComment): Object to compare to.

    Returns:
        Comparison (bool, None): Did it fit the criteria?
        """

        # Check for direct matches first
        if isinstance(other, int):
            return self.comment_id_b10 == other
        if isinstance(other, str):
            return str(self) == other

        # Check for object attributes to match to
        if hasattr(other, "comment_id_b10"):
            return self.comment_id_b10 == other.comment_id_b10

        # Check conversion to integer last
        if hasattr(other, "__int__"):
            return self.comment_id_b10 == int(other)

        return False

    def pin(self, unpin: bool = False):
        """Pin or unpin this comment.

    Args:
        unpin (bool): If true, unpins instead of pinning comment.
        """

        return self.servicephp.comment_pin(self, unpin)

    def delete(self):
        """Delete this comment"""

        return self.servicephp.comment_delete(self)

    def restore(self) -> APIComment:
        """Un-delete this comment"""

        return self.servicephp.comment_restore(self)


class BaseContentVotes:
    """Likes and dislikes on a video or comment"""

    def __repr__(self) -> str:
        """String to represent this object"""
        return f"{type(self).__name__}(content_id={self.content_id}, score={self.score})"

    def __int__(self) -> int:
        """The integer form of the content votes"""
        return self.score

    def __eq__(self, other) -> bool:
        """Determine if this content votes is equal to another.

    Args:
        other (int, str, BaseContentVotes): Object to compare to.

    Returns:
        Comparison (bool, None): Did it fit the criteria?
        """

        # Check for direct matches first
        if isinstance(other, int):
            return self.score == other
        if isinstance(other, str):
            return str(self) == other

        # Check for object attributes to match to
        if hasattr(other, "score"):
            return self.score == other.score

        # Check conversion to integer last
        if hasattr(other, "__int__"):
            return self.score == int(other)

        return False


class BaseUser:
    """A Rumble user"""

    def __int__(self) -> int:
        """The user as an integer (it's ID in base 10)"""
        return self.user_id_b10

    def __eq__(self, other) -> bool:
        """Determine if this user is equal to another.

    Args:
        other (int, str, APIUser): Object to compare to.

    Returns:
        Comparison (bool, None): Did it fit the criteria?
        """

        # Check for direct matches first
        if isinstance(other, int):
            return self.user_id_b10 == other
        if isinstance(other, str):
            return str(other) in (self.user_id_b36, self.username)

        # Check for object attributes to match to
        if hasattr(other, "user_id"):
            return self.user_id_b10 == utils.ensure_b10(other.user_id)

        # Check conversion to integer last, in case another ID or something happens to match
        if hasattr(other, "__int__"):
            return self.user_id_b10 == int(other)

        return False

    @property
    def user_id_b10(self) -> int:
        """The numeric ID of the user in base 10"""
        return self.user_id

    @property
    def user_id_b36(self) -> str:
        """The numeric ID of the user in base 36"""
        return utils.base_10_to_36(self.user_id)

    def mute(self, duration: int = None, total: bool = False):
        """Mute this user.

    Args:
        duration (int): How long to mute the user in seconds.
            Defaults to infinite.
        total (bool): Wether or not they are muted across all videos.
            Defaults to False, just this video.
            """

        self.servicephp.mute(self, self.username, duration, total)

    def unmute(self):
        """Unmute this user."""
        self.servicephp.unmute(self.username)


class BasePlaylist:
    """A playlist of Rumble videos"""

    def __int__(self) -> int:
        """The playlist as an integer (it's ID in base 10)"""
        return self.playlist_id_b10

    def __str__(self) -> str:
        """The playlist as a string (it's ID in base 64)"""
        return self.playlist_id_b64

    def __repr__(self) -> str:
        """String to represent this object"""
        return f"{type(self).__name__}(playlist_id={self.playlist_id}, title=\"{self.title}\")"

    def __eq__(self, other) -> bool:
        """Determine if this playlist is equal to another.

    Args:
        other (int, str, HTMLPlaylist): Object to compare to.

    Returns:
        Comparison (bool, None): Did it fit the criteria?
        """

        # Check for direct matches first
        if isinstance(other, int):
            return self.playlist_id_b64 == other
        if isinstance(other, str):
            return str(other) == self.playlist_id_b64

        # # Check for object attributes to match to
        # if hasattr(other, "playlist_id_b10"):
        #     return self.playlist_id_b10 == other.playlist_id_b10

        # # Check conversion to integer last, in case another ID or something happens to match
        # if hasattr(other, "__int__"):
        #     return self.playlist_id_b10 == int(other)

        return False

    @property
    def playlist_id_b64(self) -> str:
        """The numeric ID of the playlist in base 64"""
        return self.playlist_id

    @property
    def playlist_id_b10(self) -> int:
        """The numeric ID of the playlist in base 10"""
        raise NotImplementedError("See Cocorum issue #22")
        # return utils.base_64_to_10(self.playlist_id)

    def add_video(self, video_id: SupportsInt | str):
        """Add a video to this playlist

    Args:
        video_id (SupportsInt | str): The numeric ID of the video to add, in base 10 or 36.
        """

        return self.servicephp.playlist_add_video(self.playlist_id, video_id)

    def delete_video(self, video_id: SupportsInt | str):
        """Remove a video from this playlist

    Args:
        video_id (SupportsInt | str): The numeric ID of the video to remove, in base 10 or 36.
        """

        self.servicephp.playlist_delete_video(self.playlist_id, video_id)

    def edit(self, title: str = None, description: str = None, visibility: str = None, channel_id: Optional[SupportsInt | str] = None) -> APIPlaylist:
        """Edit the details of this playlist. WARNING: The original object will probably be stale after this operation.

        Args:
            title (str): The title of the playlist.
                Defaults to staying the same.
            description (str): Describe the playlist.
                Defaults to staying the same.
            visibility (str): Set to public, unlisted, or private via string.
                Defaults to staying the same.
            channel_id (SupportsInt | str): The ID of the channel to have the playlist under. TODO: Cannot be retrieved!
                Defaults to resetting to None.

        Returns:
            playlist (APIPlaylist): The edit result.
        """

        if title is None:
            title = self.title
        if description is None:
            description = self.description
        if visibility is None:
            visibility = self.visibility
        # if channel_id is False:
        #     channel_id = self.channel_id

        return self.servicephp.playlist_edit(self.playlist_id, title, description, visibility, channel_id)

    def delete(self):
        """Delete this playlist"""

        self.servicephp.playlist_delete(self)
