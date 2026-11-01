<h1><img src="https://raw.githubusercontent.com/thelabcat/cocorum/master/src/docs/assets/cocorum_icon.png" alt="" width="64"/> Cocorum: Rumble Live Stream API Python Wrapper</h1>

A Python wrapper for the Rumble Live Stream API v1.0 (beta), with some quality of life additions, such as:

- Automatic refresh when past the refresh_rate delay when querying any non_static property.
- All timespamps are parsed to seconds since Epoch, UTC timezone.
- Chat has new_messages and new_rants properties that return only messages and rants since the last time they were read.

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

## Table Of Contents

1. [Tutorials](tutorials.md)
2. [How-To Guides](how-to-guides.md)
3. [Reference](reference.md)
    1. [cocorum](modules_ref/cocorum_main.md)
    2. [cocorum.chatapi](modules_ref/cocorum_chatapi.md)
    3. [cocorum.servicephp](modules_ref/cocorum_servicephp.md)
    4. [cocorum.uploadphp](modules_ref/cocorum_uploadphp.md)
    5. [cocorum.scraping](modules_ref/cocorum_scraping.md)
    6. [cocorum.jsonhandles](modules_ref/cocorum_jsonhandles.md)
    7. [cocorum.basehandles](modules_ref/cocorum_basehandles.md)
    8. [cocorum.utils](modules_ref/cocorum_utils.md)
    9. [cocorum.static](modules_ref/cocorum_static.md)
4. [Explanation](explanation.md)

## Acknowledgements

Special thanks to GlobalGamer2015 for information on the SSE chat API, and to K4nji for help with the password hashing algorithm. Both helped with other API endpoints as well. Honorable mention to [a3r0id's RumblePy](https://github.com/a3r0id/RumblePy), a discontinued module that held the basis for logging in which I used.

I, Wilbur Jaywright, and my brand, Marswide BGL, have no official association with Rumble Corp. beyond that of a normal user and/or channel on the Rumble Video platform. This wrapper is not officially endorsed by Rumble Corp. or its subsidiaries.

S.D.G.
