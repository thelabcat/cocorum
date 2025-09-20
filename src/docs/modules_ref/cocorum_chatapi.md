# cocorum.chatapi

The primary use from this module is the `ChatAPI` class, a wrapper for Rumble's internal chat API. This class includes links to the chat-related methods of `ServicePHP()` (muting users for example). If you wish to use any two-way chat features, you must first create an instance of `cocorum.servicephp.ServicePHP()`, and then pass it to this class upon initialization. 
All other classes are supporting sub-classes.

::: cocorum.chatapi

S.D.G.
