# Tutorials

## Reading chat using the Rumble Live Stream API wrapper
Class `cocorum.RumbleAPI` is the wrapper for [the Rumble Live Stream API](https://rumblefaq.groovehq.com/help/how-to-use-rumble-s-live-stream-api); the API Rumble has published for the public to use, furthermore referenced as the RLS API. To get started with it, you will first need an API "key" from Rumble (really it's a static URL with a key as a parameter, but you don't need to worry about that). You can get that URL with key [here](https://rumble.com/account/livestream-api).

The recommended way to handle most API keys is an environment variable, but since there's a good chance you could be handling multiple API keys on the same machine, I don't recommend this. Whatever you do, DO NOT HARDCODE IT! You can use [dotenv](https://pypi.org/project/dotenv/) to load it, or whatever method you prefer, but make sure that you do not accidentally distribute it. If you are using Git, you can add the filename to your repository's .gitignore file. All the code here will assume you have loaded your URL with key, and assigned it to `API_URL`.

With that taken care of, we can initialize the API wrapper. I recommend you do this in an interactive Python shell, such as IDLE, rather than a script. 

```python
from cocorum import RumbleAPI

## API_URL is Rumble Live Stream API URL with key
api = RumbleAPI(API_URL, refresh_rate=10)
```

The wrapper will load data from the API, then be ready to use. I'll explain the `refresh_rate` parameter in a moment.

Now we can query the wrapper for some data.

```python
print(api.username)
## Should display your Rumble username

print("Latest follower:", api.latest_follower)
## Should display your latest follower, or None if you have none.
```

If you are familiar with the RLS API's JSON structure, this naming scheme should be familiar. Most of the JSON keys are translated directly into Python attribute names, with the general exception of `id` being augmented to `thing_id`, since `id` means something in Python.

Now, let's try to get the `latest_subscriber/amount_dollars` endpoint:

```python
if api.latest_subscriber:
    print(api.latest_subscriber, f"subscribed for ${api.latest_subscriber.amount_dollars}")
## Should display your latest subscriber if you have one.
```

Note: If there is no latest subscriber, this endpoint will be None, and NoneType has no attribute amount_dollars. I added the `if` statement in that code to avoid an AttributeError.

You may have noticed by now that sometimes, querying data takes quite a bit longer than other times. This is `refresh_rate` in action. The way the Rumble Live Stream API currently works is by passing a big JSON data block of everything it knows, all at once. It would be very wasteful to ask it for this JSON block anew every time we wanted to read one value from it. But, after awhile we do want to check again and make sure it's up-to-date. The wrapper handles this by remembering the entire JSON block, and checking how old it is every time you make a query (with some exceptions). If the remembered JSON is older than `refresh_rate` (a value in seconds), the wrapper discards the JSON block and queries it again. Otherwise, it reuses the old data (it's not THAT old).

Now, about those exceptions, some properties will not be likely to change while you are using the API (the username it is under, for example). These are listed in `cocorum.static.StaticAPIEndpoints`. Because of this, querying those properties specifically will not trigger a refresh. They do still reference the newest remembered JSON, however, so if you really needed to get the latest version of them, you could run `api.check_refresh()` to make sure the remembered JSON is not older than `refresh_rate`. You can also run `api.refresh()` to try and refresh immediately, but be warned that Rumble sets their own rate limits!

The next part of the tutorial requires that you have a livestream up. You don't actually have to go live, you can just initialize it and then not actually stream, but the chat needs to be open. We are going to watch the chat in Python. Once you have the livestream up, query it from the API wrapper.

```python
livestream = api.latest_livestream # None if there is no stream running
```

We won't have to get this again, because Livestream objects returned by RumbleAPI are deep: When queried for data, they will make sure their sub-block of the JSON is still up-do-date, via an internal link to their parent RumbleAPI object.

Let's get some data on this livestream:

```python
print(livestream.title)
print("Stream visibility is", livestream.visibility)

# We will use this later
STREAM_ID = livestream.stream_id

print("Stream ID is", STREAM_ID)
```

We will use that `STREAM_ID` in a later test, so don't close this interpreter!

Now that we've verified the `Livestream` object is working, we can start monitoring chat. To help with this kind of application, I added a `new_messages` virtual endpoint to the `LivestreamChat` API sub-wrapper class. When you query this, it will only return chat messages that are newer than the last time you queried it (or the time you first created the Livestream object instance). Effectively, it's like checking the chat mailbox. Let's check it frequently, for one minute. Be sure to send some chat messages in this time, so you can see this at work.

```python
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

This is a good simple way to get slow chats' messages. But, what if the chat is moving too fast for this to be effective? RLS API queries have a max number of chat messages they will show into the past, and we could miss some if more than that many new chat messages arrive before we can refresh the JSON block. That was the problem GlobalGamer2015 encountered when developing [RUM Bot Live Alerts](https://www.rumbot.org/rum-bot-live-alerts/), and so he found and used a different API: The Rumble internal SSE chat stream.

## Reading chat using the ChatAPI wrapper
This is where Cocorum goes into the backroads of Rumble. So far, we have only seen wrappers for the API that Rumble expresssly designed for the public to use. Beyond this point, we get into wrappers for APIs used by the internals of the web interface. If Rumble officially forbids / denies public access to them (which they have every right to do), these wrappers will break. Thankfully, they have made no indication that they intend to do so as far as I know, so please, don't give them a reason to. We're fudging our boundaries here, make sure you respect the spirit of the law rather than just the letter. I do not, in any regards whatsoever, endorse any sort of cyber-arson, including but not limited to; disrupting the Rumble platform, via misuse of the public RLS API or any other means.

With that being understood, let's connect to the SSE chat stream. I expect this to be in the same interpreter, so `time` will still be imported, api is still a RumbleAPI object, and `STREAM_ID` is still assigned, from earlier.

A warning here, if you used some other method to get your stream ID (such as copying it from a chat popup window's URL), be sure that it is not both base 10 and a string. Said chat URLs have it in base 10, so when copying it from there, you MUST make it an integer type before passing it here (can be converted with Python's `int()` function). This is because whatever format you pass must be converted to base 10 internally. [The converter](../modules_ref/cocorum_utils/#cocorum.utils.ensure_b10) has no way to tell the difference between a base 10 string, and a base 36 string that happens to only have base 10 numerals. So, where Cocorum uses such converters, I set them to assume any string is base 36. I could have done this the other way around maybe, but we'd hit the same sort of limitation in reverse.

```python
from cocorum import chatapi

chat = chatapi.ChatAPI(stream_id = STREAM_ID) # Stream ID can be an integer or a base 36 string
chat.clear_mailbox() # Erase messages that were still visible before we connected
```

If you don't run `chat.clear_mailbox()`, then the following code will print messages that were already in chat before it gets to waiting for new ones. Anyways, let's monitor chat for one minute. 

```python
# Get messages for one minute
start_time = time.time()

# Continue watching chat for one minute, or until the return of chat.get_message() is None (indicates a chat close)
while time.time() - start_time < 60 and (msg := chat.get_message()):
    print(msg.user.username, "said", msg)
```

A note about this. `ChatAPI().get_message()` will always wait for an additional message, even after the time runs out. I've also had trouble getting the chat to close properly once the stream ends, or staying open if it is inactive for several minutes. See [GitHub issue # 5](https://github.com/thelabcat/cocorum/issues/5) for more info on this.

That's all fine and dandy, but what about _sending_ messages? Well...

## Logging in to Rumble
Logging into Rumble is handled by a separate submodule called `servicephp`, wrapping a number of Rumble endpoints, all contained within one file on the Rumble servers named (you guessed it) `service.php`. The `servicephp` library used to be called by default inside `ChatAPI.__init__()` if you passed credentials to that method, but when Rumble added 2FA, this became inviable. Now, you pass an already logged-in `ServicePHP` to `__init__()` instead. Since our current instance of `ChatAPI` in this example was initialized without this, we cannot use it any more.

I'm sorry, instance.

```python
chat.close()
```

Jokes aside, it's good practice to call `ChatAPI().close()` when you are done with it, to clean up the network connection and mark it as unusable. Now, with that dealt with, let's log in. Again, never hard code your credentials. In this example, `UNAME` is your Rumble account username (do NOT use your email). For interactive terminals, you can get passwords with Python's native `getpass` module, so we'll do that here to keep it from being recorded in the interpreter's history log.

```python
from getpass import getpass
from cocorum import servicephp
sphp = servicephp.ServicePHP(UNAME)

# First step of login
twofactor = sphp.login_basic(getpass("Enter password: "))
```

If you do not have 2FA enabled on your account, `sphp` is now logged in, and `twofactor` is `None`. Otherwise, `twofactor` is an instance of `servicephp.TwoFacAuth`. So, that's something we can and should check with an if statement, before trying to do 2FA.

```python
# Set the order of preference for authentication options, from best to worst
# This is so the script can choose the best one automatically
TWOFA_PREF_ORDER = "authenticator", "email", "phone"

if twofactor:
    # 2FA is enabled
    # Get the available option that comes earliest in the preference order
    best_option = sorted(twofactor.options, key=TWOFA_PREF_ORDER.index)[0]

    # Get a code
    # NOTE: If the option is "authenticator", this technically doesn't do anything important
    # Authenticator apps don't communicate with the server
    twofactor.request_2fa_code(best_option)
    print("Code sent to", best_option)

    # Finally, complete the login
    # Note that we need the TwoFacAuth object here for some behind-the-scenes data transfer
    twofa_code = input("Enter 2FA code: ")
    sphp.login_second_factor(twofactor, twofa_code)
```

If that last line gives you an error with some JSON mentioning an "invalid or expired user key", it means you waited too long in between the first and second factor of authentication. Just rerun `twofactor = sphp.login_basic(PWORD)`, and then rerun the `if twofactor:` clause.

Now, `sphp` is logged in, and we can pass it to a new `ChatAPI` instance.

```python
chat = chatapi.ChatAPI(STREAM_ID, sphp)
outmsg_id, outmsg_user = chat.send_message("Hello, Rumble!")

# Just some data like the sent message ID
print(f"Sent message {outmsg_id} as {outmsg_user.username}.")
```

Getting messages functions the same as before. In fact, you will even receive the message you sent here. You can use the returned outmsg_id to recognize it.

```python
# Get messages for one minute
start_time = time.time()

# Continue watching chat for one minute, or until the return of chat.get_message() is None (indicates a chat close)
while time.time() - start_time < 60 and (msg := chat.get_message()):
    print(msg.user.username, "said", msg)
    if msg.message_id == outmsg_id:
        print("(Hey, that was our message!)")
```

When we are done with any `ServicePHP` instance, just to make less of an attack surface and possible confusion on the number of signed-in devices, we should do something about the still-valid session token cookie. We can do this with the `logout()` method, immediately invalidating the token:

```python
sphp.logout()
```

Or instead, we can make note of the token for later use:

```python
cookie: dict = sphp.session_cookie
token: str = cookie[cocorum.static.Misc.session_token_key]
```

Pass either of these as the `session` parameter of `__init__()` method of a new `ServicePHP` instance to immediately log it in. This is equivalent to "Remember me" when signing in via your browser. This won't work with a token that has been logged out, though!

## Conclusion

I haven't used everything these classes offer, just the basics. For example, you can save the `ServicePHP().session_cookie` attribute, and pass it to a `ServicePHP().__init__()` call next time, to avoid having to log in again. I.E., you can remember your sign-in. I recommend that you check the Reference section of this documentation.

I hope the module is easier to understand now. Goodbye! :-)

## S.D.G.
