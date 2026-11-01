<h1><img src="https://raw.githubusercontent.com/thelabcat/cocorum/master/src/docs/assets/cocorum_icon.png" alt="" width="64"/> Cocorum: Rumble Live Stream API Python Wrapper</h1>

A Python wrapper for the Rumble Live Stream API v1.0 (beta), with some quality of life additions, such as:

- Automatic refresh when past the refresh_rate delay when querying any non_static property.
- All timespamps are parsed to seconds since Epoch, UTC timezone.
- Chat has new_messages and new_rants properties that return only messages and rants since the last time they were read.

## Rumble Terms of Service status

As for `cocorum` toplevel module, `cocorum.static`, and most of `cocorum.utils`, [Rumble's Live Stream API help page](https://rumblefaq.groovehq.com/help/how-to-use-rumble-s-live-stream-api) says that, for now, users have "full reign" on using and implementing the Rumble Live Stream API however they want. However, [Rumble's Terms of Service](https://rumble.com/s/terms) prohibit "any form of automated software to interact with or access the Rumble Site ... without the prior written permission of Rumble." They prohibit "systematic retrieval of data or Content ... to create or compile ... a collection, compilation, library, database or directory." They also prohibit harvesting information about chat and forum users. The network functions in `cocorum.utils` and the entirety of the rest of the library fit this description. I just discovered this recently, so shortly after publishing this update, I will be requesting said written permission, and will update the library according to their reply.

### Even if Rumble says yes...

- Use this library only on your own account or channel, or on streams you moderate.
- Do not try to bypass any form of rate limits that Rumble may impose. This library is not intended to be used to harm Rumble or its users.
- Do not use any of the features for bulk collection of data.
- If Rumble asks you to stop, do.

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

I, Wilbur Jaywright, and my brand, Marswide BGL, have no official association with Rumble Corp. beyond that of a normal user and/or channel on the Rumble Video platform. This project is not officially endorsed by Rumble Corp. or its subsidiaries.

S.D.G.
