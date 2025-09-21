<h1><img src="https://raw.githubusercontent.com/thelabcat/cocorum/main/src/docs/assets/cocorum_icon.png" alt="" width="64"/> Cocorum: Rumble Live Stream API Python Wrapper</h1>

A Python wrapper for the Rumble Live Stream API v1.0 (beta), with some quality of life additions, such as:

- Automatic refresh when past the refresh_rate delay when querying any non_static property.
- All timespamps are parsed to seconds since Epoch, UTC timezone.
- Chat has new_messages and new_rants properties that return only messages and rants since the last time they were read.

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

## Experimental internal API submodules
This part of Cocorum is not part of the official Rumble Live Stream API. It includes the following submodules:
- chatapi
- servicephp
- uploadphp
- scraping
- utils (very rare cases)

Example usage of `cocorum.chatapi`:
```
from cocorum import chatapi

chat = chatapi.ChatAPI(stream_id = STREAM_ID) # Stream ID can be base 10 or 36
chat.clear_mailbox() # Erase messages that were still visible before we connected

# Get messages for one minute
start_time = time.time()
while time.time() - start_time < 60 and (msg := chat.get_message()):
    print(msg.user.username, "said", msg)
```

## Conclusion
Hope this helps!

I, Wilbur Jaywright, and my brand, Marswide BGL, have no official association with Rumble Corp. beyond that of a normal user and/or channel on the Rumble Video platform. This wrapper is not officially endorsed by Rumble Corp. or its subsidiaries.

S.D.G.
