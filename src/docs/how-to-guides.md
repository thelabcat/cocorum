#How-To Guides

## Iterate through all comments under all videos, and mute spam bots based on your custom detection algorithm
```
#!/usr/bin/env python3
"""Rumble comment filter

Demonstration of how to go through Rumble video comments via Cocorum.
Naive. Does not take other comments by the same user into account.
Non-functional filter algorithm dummy.
S.D.G."""

import getpass
from cocorum import servicephp, scraping

USERNAME, PASSWORD = input("Username: "), getpass("Password: ")

def is_spam_comment(comment):
    """Detect if comment is spam. DUMMY STUB.
    
    Args:
         comment (HTMLComment): A single video comment.
    
    Returns:
        Result (bool): Is this a spam comment?
        """

    NotImplemented
    return False

#Log in to Rumble
print("Logging in...")
sphp = servicephp.ServicePHP(USERNAME, PASSWORD)

#Get all videos under user
print("Getting all videos (slow)...")
scraper = scraping.Scraper(sphp)
videos = scraper.get_videos()

#Record of muted users to avoid double-action
mutes = set()

#For each video, get the comments
for video in videos:
    print(f"Getting comments on video #{video.video_id_b10}: '{video.title}'...")
    comments = sphp.comment_list(video.video_id_b36)

    #Bit of formatting at the end to make sure the word comment is singular only when there is exactly one comment, just for niceness
    print(f"Got {len(comments)} comment{'s' * (len(comments) != 1)}.")
    
    #Do the actual filtering
    for comment in comments:
        #Avoid duplicate action
        if comment.username in mutes:
            print(f"Another comment by previous mute '{comment.username}', skipping...")
            continue

        #Comment was found guilty
        if is_spam_comment(comment):
            print(f"Comment by '{comment.username}' detected as spam:\n\t{comment.text}")

            #Have the user confirm, and then take action against the offender
            if "y" in input("Mute user (deletes all their comments)? [y/N]:").lower():
                sphp.mute_user(comment.user, total = True)

print("Done.")
```
