# Reference

For the most part, wrapper attributes that are not added features have the same name as the direct JSON counterparts, with the exception of adding prefixes to some things that have the same name in the JSON as Python builtin functions. For example, thing/id in JSON is thing.thing_id in the wrappers.

1. [cocorum](modules_ref/cocorum_main.md), the main Rumble Live Stream API wrapper.
2. [cocorum.chatapi](modules_ref/cocorum_chatapi.md), a wrapper for Rumble's internal chat API, can receive messages very quickly.
3. [cocorum.servicephp](modules_ref/cocorum_servicephp.md), a wrapper for Rumble's internal service.php API, needed for login.
4. [cocorum.uploadphp](modules_ref/cocorum_uploadphp.md), a wrapper for Rumble's upload.php API, used to upload videos.
5. [cocorum.scraping](modules_ref/cocorum_scraping.md), a way of getting data from Rumble HTML, wether from the web or the APIs for some reason. 
6. [cocorum.jsonhandles](modules_ref/cocorum_jsonhandles.md), abstract classes for handling JSON data blocks.
7. [cocorum.basehandles](modules_ref/cocorum_basehandles.md), abstract classes with common methods for both JSON and HTML wrappers.
8. [cocorum.utils](modules_ref/cocorum_utils.md), utility functions for local calculations or one-off checks.
9. [cocorum.static](modules_ref/cocorum_static.md), static global data used across the library.

S.D.G.
