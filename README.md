<h1><img src="https://raw.githubusercontent.com/thelabcat/cocorum/master/src/docs/assets/cocorum_icon.png" alt="" width="64"/> Cocorum: Rumble Live Stream API Python Wrapper</h1>

A Python wrapper for the Rumble Live Stream API v1.0 (beta), with some quality of life additions, such as:

- Implementing a cache of the API data with an automatic time to live enforcer. If the stored API data is older than `refresh_rate` (and you are querying an endpoint that can actually change over time), the wrapper will automatically refresh in the background before handing you the fresh endpoint data.
- All timespamps are parsed to seconds since Epoch, UTC timezone.
- Additional `new_followers` and `new_subscribers`, plus `chat.new_messages` and `chat.new_rants` as endpoints that automatically clear themselves when read.

## Rumble Terms of Service status

Cocorum has no affiliation with Rumble. Wilbur Jaywright and Marswide BGL have no association with Rumble Corp. beyond that of a normal user and channel. Rumble has not endorsed this project.

[Rumble's Terms of Service](https://rumble.com/s/terms) prohibit "any form of automated software to interact with or access the Rumble Site ... without the prior written permission of Rumble." They prohibit "systematic retrieval of data or Content ... to create or compile ... a collection, compilation, library, database or directory." They also prohibit harvesting information about chat and forum users.

[Rumble's Live Stream API help page](https://rumblefaq.groovehq.com/help/how-to-use-rumble-s-live-stream-api) says that, for now, users have "full reign" on using and implementing the Rumble Live Stream API however they want. The author has requested written permission from Rumble. There has been no answer yet.

### Official Live Stream API

`RumbleAPI` (the main class in the `cocorum` package) calls the Live Stream API URL you pass in, the key URL from your Rumble account. Reading livestream chat through `RumbleAPI`, including `livestream.chat`, uses that same Live Stream API response.

### Undocumented internal endpoints

These modules use undocumented internal endpoints:

- `cocorum.servicephp` — `service.php` login and actions
- `cocorum.uploadphp` — `upload.php`
- `cocorum.chatapi` — the chat API and its SSE stream
- `cocorum.scraping` — HTML scraping of account and user pages

`cocorum.chatapi`, `cocorum.uploadphp`, and `cocorum.scraping` take a logged-in `ServicePHP` session for actions that need one, so those calls also go through `service.php`. Looking up a mute record from chat goes through `cocorum.scraping`.

`cocorum.accountapi` posts to account pages with a key read from account HTML. Treat it with the undocumented endpoints above. `cocorum.utils.video_id_from_url` calls Rumble's public oEmbed JSON endpoint to turn a watch URL into a video id. `cocorum.jsonhandles`, `cocorum.basehandles`, and `cocorum.static` hold shared types, constants, and limits. The chat send cooldown is `cocorum.static.Message.send_cooldown` (3 seconds).

### How to use this library

- Use it only on your own account or channel, or on streams you moderate.
- Respect Rumble chat's 3-second send limit.
- Do not use the scraping features for bulk collection of other users' data.
- If Rumble asks you to stop, stop.

## Installation:
You can find [this project on PyPi.org](https://pypi.org/project/cocorum/), and install it using any PyPi-compatible method (including Pip). Alternatively, you can view and download [the source code on GitHub](https://github.com/thelabcat/cocorum).

## Usage:

I recommend taking a gander at [the full documentation](https://thelabcat.github.io/cocorum/), but here's a basic intro:

For the most part, attributes that are not added features have the same name as the direct JSON counterparts, with the exception of adding prefixes to some things that have the same name in the JSON as Python builtin functions. For example, thing/id in JSON is thing.thing_id in this Python wrapper.

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

## Rumble internal API submodules
This part of Cocorum's wrapping is not part of the official Rumble Live Stream API. It includes the following submodules:
- chatapi
- servicephp
- uploadphp
- scraping
- utils (very rare cases)

Example usage of `cocorum.chatapi`:
```
from cocorum import chatapi

# Stream ID can be base 10 int or base 36 str
with chatapi.ChatAPI(stream_id = STREAM_ID) as chat:
    chat.clear_mailbox() # Erase messages that were still visible before we connected

    # Get messages for one minute
    start_time = time.time()
    while time.time() - start_time < 60 and (msg := chat.get_message()):
        print(msg.user.username, "said", msg)
```

## Conclusion
Hope this helps!

I, Wilbur Jaywright, and my brand, Marswide BGL, have no official association with Rumble Corp. beyond that of a normal user and/or channel on the Rumble Video platform. This wrapper is not officially endorsed by Rumble Corp. or its subsidiaries.

Copyright 2026 Wilbur Jaywright d.b.a. Marswide BGL.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

## S.D.G.
