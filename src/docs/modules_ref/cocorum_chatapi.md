# cocorum.chatapi

The primary use from this module is the `ChatAPI` class, a wrapper for Rumble's internal chat API. This class includes links to the chat-related methods of `ServicePHP()` (muting users for example). If you wish to use any two-way chat features, you must first create an instance of `cocorum.servicephp.ServicePHP()`, and then pass it to this class upon initialization. 
All other classes are supporting sub-classes.

`get_message()` returns `None` when the live chat ends. Rumble does not send an "ended" SSE event. A read timeout (90 seconds by default) reconnects, and HTTP 204 on that connection means the chat is over. Replayed `init` messages are skipped by message id. `close()` is safe to call from another thread, the object is a context manager, and `on_ended` is an optional callback. The chat id is the embed id, not the watch-page slug. This is the fix for [GitHub issue #5](https://github.com/thelabcat/cocorum/issues/5).

::: cocorum.chatapi

S.D.G.
