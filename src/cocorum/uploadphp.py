"""
UploadPHP

Interact with Rumble's Upload.PHP API to upload videos.
S.D.G."""

import json
import mimetypes
import os
import random
import time
import bs4
import requests
from . import JSONObj
from . import static
from . import utils

class UploadResponse(JSONObj):
    """Response to a successful video upload"""
    @property
    def url(self):
        """The video viewing URL"""
        return self["url"]

    @property
    def fid(self):
        """The numeric ID of the uploaded video in base 10"""
        return int(self["fid"])

    @property
    def fid_b10(self):
        """The numeric ID of the uploaded video in base 10"""
        return self.fid

    @property
    def fid_b36(self):
        """The numeric ID of the uploaded video in base 36"""
        return utils.base_10_to_36(self.fid)

    @property
    def title(self):
        """The title of the video"""
        return self["title"]

    @property
    def embed(self):
        """HTML to use for embedding the video"""
        return self["embed"]

    @property
    def embed_monetize(self):
        """HTML to use for embedding the video with monetization"""
        return self["embedMonetize"]

class UploadPHP:
    """Upload videos to Rumble"""
    def __init__(self, servicephp):
        """Pass a ServicePHP object"""
        self.servicephp = servicephp

        #Primary and secondary video categories AKA site and media channels
        self.categories1 = {}
        self.categories2 = {}
        self.get_categories()

        self.__cur_file_size = None
        self.__cur_upload_id = None
        self.__cur_num_chunks = None

    def get_categories(self):
        """Load the primary and secondary categories from Rumble"""
        print("Loading categories")
        r = self.uphp_request({}, method = "GET")
        soup = bs4.BeautifulSoup(r.text, features = "html.parser")

        options_box1 = soup.find("input", attrs = {"id" : "category_primary"}).parent
        options_elems1 = options_box1.find_all("div", attrs = {"class" : "select-option"})
        self.categories1 = {e.string.strip() : int(e.attrs["data-value"]) for e in options_elems1}

        options_box2 = soup.find("input", attrs = {"id" : "category_secondary"}).parent
        options_elems2 = options_box2.find_all("div", attrs = {"class" : "select-option"})
        self.categories2 = {e.string.strip() : int(e.attrs["data-value"]) for e in options_elems2}

        return self.categories1, self.categories2

    @property
    def session_cookie(self):
        """Our Rumble session cookie to authenticate requests"""
        return self.servicephp.session_cookie

    def uphp_request(self, additional_params, method = "PUT", data: dict = None, timeout = static.Delays.request_timeout):
        """Make a request to Upload.PHP with common settings
        additional_params: Query string parameters to add to the base ones
        method: What method to use for the request.
            Defaults to PUT.
        data: Form data for the request.
            Defaults to None.
        timeout: Request timeout
            Defaults to static.Delays.request_timeout"""
        params = {"api": static.Upload.api_ver}
        params.update(additional_params)
        r = requests.request(
                method,
                static.URI.uploadphp,
                params = params,
                data = data,
                headers = static.RequestHeaders.user_agent,
                cookies = self.session_cookie,
                timeout = timeout,
                )
        assert r.status_code == 200, f"Upload.PHP request failed: {r}\n{r.text}"
        #If the request json has a data -> success value, make sure it is True

        return r

    def chunked_vidfile_upload(self, file_path):
        """Upload a video file to Rumble in chunks"""
        print("Uploading video in", self.__cur_num_chunks, "chunks")

        #Base upload params
        upload_params = {
            "chunkSz": static.Upload.chunksz,
            "chunkQty": self.__cur_num_chunks,
            }

        with open(file_path, "rb") as f:
            for i in range(self.__cur_num_chunks):
                print(f"Uploading chunk {i + 1}/{self.__cur_num_chunks}")
                #Parameters for this chunk upload
                chunk_params = upload_params.copy()
                chunk_params.update({
                    "chunk": f"{i}_{self.__cur_upload_id}.mp4",
                    })

                #Get permission to upload the chunk
                assert utils.options_check(
                    static.URI.uploadphp,
                    "PUT",
                    cookies = self.session_cookie,
                    params = chunk_params,
                    ), f"Chunk {i} upload failed at OPTIONS request."
                #Upload the chunk
                self.uphp_request(chunk_params, data = f.read(static.Upload.chunksz), timeout = 300) #Set static? TODO

        #Params for the merge request
        merge_params = upload_params.copy()
        merge_params.update({
            "merge": i,
            "chunk": f"{self.__cur_upload_id}.mp4",
            })

        #Tell the server to merge the chunks
        print("Merging chunks at server")
        r = self.uphp_request(merge_params)
        merged_video_fn = r.text
        print("Merged to", merged_video_fn)
        return merged_video_fn

    def unchunked_vidfile_upload(self, file_path):
        """Upload a video file to Rumble all at once"""
        print("Uploading video")

        with open(file_path, "rb") as f:
            #Get permission to upload the file
            assert utils.options_check(
                static.URI.uploadphp,
                "PUT",
                cookies = self.session_cookie,
                params = {"api": static.Upload.api_ver},
                ), "File upload failed at OPTIONS request."
            #Upload the file
            r = self.uphp_request({}, data = f.read(), timeout = 300) #Set static? TODO

        uploaded_fn = r.text
        print("Video file on server is", uploaded_fn)
        return uploaded_fn

    def upload_cthumb(self, file_path):
        """Upload a custom thumbnail"""
        print("Uploading custom thumbnail")
        ext = file_path.split(".")[-1]
        ct_server_filename = "ct-" + self.__cur_upload_id + "." + ext
        with open(file_path, "rb") as f:
            assert self.uphp_request(
                {"cthumb" : ct_server_filename},
                data = {"customThumb" : f.read()},
                ).text.strip() == ct_server_filename, "Unexpected thumbnail upload response"

        print("Thumbnail file on server is", ct_server_filename)
        return ct_server_filename

    def upload_video(self, file_path, title: str, category1, **kwargs):
        """Upload a video to Rumble
        file_path: Path to video file
        title: The video title
        category1: The primary category to upload to
        info_who, _when, _where, _ext_user: Metadata about the video
            Defaults to empty
        tags: String of comma-separated tags
            Defaults to empty
        category2: The secondary category to upload to
            Defaults to empty
        channel_id: Numeric ID of the channel to upload to
            Defaults to user page upload
        visibility: Public, unlisted, private
            Defaults to public
        availability: TODO
            Defaults to free.
        scheduled_publish: Time to publish the video to public in seconds since epoch.
            Defaults to publish immediately.
        thumbnail: Thumbnail to use. Set to index 0-2 for an auto thumbnail, or a file path for custom.
            Defaults to 0
        """
        assert os.path.exists(file_path), "Video file does not exist on disk"

        self.__cur_file_size = os.path.getsize(file_path)

        assert self.__cur_file_size < static.Upload.max_filesize, "File is too big"

        start_time = int(time.time() * 1000)

        #IDK if the second half of this is correct, TODO
        self.__cur_upload_id = f"{start_time}-{random.randrange(1000000) :06}"

        #Is the file large enough that it needs to be chunked
        if self.__cur_file_size > static.Upload.chunksz:
            #Number of chunks we will need to do, rounded up
            self.__cur_num_chunks = self.__cur_file_size // static.Upload.chunksz + 1
            server_filename = self.chunked_vidfile_upload(file_path)
        else:
            server_filename = self.unchunked_vidfile_upload(file_path)

        end_time = int(time.time() * 1000)

        #Get the uploaded duration
        r = self.uphp_request({"duration": server_filename})
        checked_duration = int(r.text)
        print("Server says video duration is", checked_duration)

        #Get thumbnails
        auto_thumbnails = self.uphp_request({"thumbnails" : server_filename}).json()

        thumbnail = kwargs.get("thumbnail", 0)

        #thumbnail is an auto index
        if isinstance(thumbnail, int):
            assert 0 <= thumbnail <= len(auto_thumbnails), "Thumbnail index is invalid"
            thumbnail = list(auto_thumbnails.keys())[thumbnail]

        #Thumbnail is path string
        elif isinstance(thumbnail, str):
            assert os.path.exists(thumbnail), "Thumbnail was a str but is not a valid path"
            thumbnail = self.upload_cthumb(thumbnail)

        #Unknown
        else:
            raise ValueError("Thumbnail argument is of unknown type")

        #Get the primary category
        if isinstance(category1, str):
            category1 = category1.strip()
            if category1.isnumeric():
                category1 = int(category1)
            else:
                category1 = self.categories1[category1]
        assert isinstance(category1, (int, float)), f"Primary category must be number or str name, got {type(category1)}"

        #Get the secondary category, but allow None
        category2 = kwargs.get("category2")
        if isinstance(category2, str):
            category2 = category2.strip()
            if category2.isnumeric():
                category2 = int(category1)
            else:
                category2 = self.categories2[category2]
        assert isinstance(category2, (int, float)) or category2 is None, f"Secondary category must be number or str name, got {type(category1)}"

        #Publish the upload
        updata = {
            "title": title,
            "description": kwargs.get("description", ""),
            "video[]": server_filename,
            "featured": "6", #Never seems to change
            "rights": "1",
            "terms": "1",
            "facebookUpload": "",
            "vimeoUpload": "",
            "infoWho": kwargs.get("info_who", ""),
            "infoWhen": kwargs.get("info_when", ""),
            "infoWhere": kwargs.get("info_where", ""),
            "infoExtUser": kwargs.get("info_ext_user", ""),
            "tags": kwargs.get("tags", ""),
            "channelId": str(utils.ensure_b10(kwargs.get("channel_id", 0))),
            "siteChannelId": str(category1),
            "mediaChannelId": str(category2),
            "isGamblingRelated": "false",
            "set_default_channel_id": "0", #Set to 1 to "Set this channel as default" on Rumble
            #Scheduled visibility takes precedent over visibility setting
            "visibility": kwargs.get("visibility", "public") if not kwargs.get("scheduled_publish") else "private",
            "availability": kwargs.get("availability", "free"),
            "file_meta": {
                "name": os.path.basename(file_path), #File name
                "modified": int(os.path.getmtime(file_path) * 1000), #Timestamp file was modified, miliseconds
                "size": self.__cur_file_size, #Exact length of entire MP4 file in bytes
                "type": mimetypes.guess_file_type(file_path)[0],
                "time_start": start_time, #Timestamp file started uploading, miliseconds
                "speed": int(self.__cur_file_size / (end_time - start_time) * 1000),
                "num_chunks": self.__cur_num_chunks,
                "time_end": end_time, #Timestamp we finished uploading, miliseconds
                },
            "schedulerDatetime": utils.form_timestamp(kwargs.get("scheduled_publish")) if kwargs.get("scheduled_publish") else "",
            "thumb": str(thumbnail),
            }

        print("Publishing uploaded video")
        r = self.uphp_request(
            {"form" : "1"},
            data = updata,
            method = "POST",
            )

        #Extract the json from the response HTML, and return it as an JSONObj derivative
        return UploadResponse(json.loads(r.text[r.text.find("{") : r.text.rfind("}") + 1]))
