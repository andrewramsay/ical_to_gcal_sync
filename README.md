This script can be used to periodically pull events from an iCal feed and insert them into a selected Google Calendar using the API for that service. 

Why do this instead of importing the iCal URL straight into GCal? The rate at which GCal refreshes iCal feeds is glacially slow, typically somewhere between 1-2 days. This has been the case for the best part of a decade now and Google show absolutely no interest in providing a sensible way to even trigger a manual refresh (e.g. https://productforums.google.com/forum/#!msg/calendar/iXp8fZfgU2E/wK9Qf6nfI48J). This script is a simple way to work around that limitation - it's not much use to me if I add an event to my todo list and then check my calendar the next day and forget about it because it hasn't been synced from the associated iCal feed yet. 

I've been running this script on an RPi as a cronjob and it's working well for me. I'm putting the code here in case it's useful to anyone similarly frustrated with Google Calendar and its handling of iCal feeds. Note that it's not particularly polished or well-packaged, and importantly doesn't try to handle all possible types of iCal events. It only does the minimum I needed for my own workflow. 

## Using the script

> NOTE: requires Python 3.7+ (2.7 can be made to work to some extent, but hasn't been well-tested recently and you may encounter bugs)

Some brief instructions:
1. Copy `config.py.example` to a new file `config.py` or a custom file (see *Multiple Configurations* below)
2. Set `ICAL_FEED` to the URL of the iCal feed you want to sync events from. If the feed is passowrd protected set also the variables `ICAL_FEED_USER` and `ICAL_FEED_PASS`.
3. Set `CALENDAR_ID` to the ID of the Google Calendar instance you want to insert events into. You can set it to `primary` to use the default main calendar, or create a new secondary calendar (in which case you can find the ID on the settings page, of the form `longID@group.calendar.google.com`).
4. `pip install -r requirements.txt`
5. Go through the process of registering an app in the Google Calendar API dashboard in order to obtain the necessary API credentials. This process is described at https://developers.google.com/google-apps/calendar/quickstart/python - rename the downloaded file to ical_to_gcal_sync_client_secret.json and place it in the same location as the script. 
6. Run the script. This should trigger the OAuth2 authentication process and prompt you to allow the app you created in step 4 to access your calendars. If successful it should store the credentials in ical_to_gcal_sync.json.
7. Subsequent runs of the script should not require any further interaction unless the credentials are invalidated/changed.

## Multiple Configurations / Alternate Config Location

If you want to specify an alternate location for the config.py file, use the environment variable CONFIG_PATH:

```
CONFIG_PATH='/path/to/my-custom-config.py' python ical_to_gcal_sync.py
```

## Rewriting Events / Skipping Events

If you specify a function in the config file called EVENT_PREPROESSOR, you can use that
function to rewrite or even skip events from being synced to the Google Calendar.

Some example rewrite rules:

``` python
import icalevents
def EVENT_PREPROCESSOR(ev: icalevents.icalparser.Event) -> bool:
    from datetime import timedelta

    # Skip Bob's out of office messages
    if ev.summary == "Bob OOO":
        return False

    # Skip gaming events when we're playing Monopoly
    if ev.summary == "Gaming" and "Monopoly" in ev.description:
        return False

    # convert fire drill events to all-day events
    if ev.summary == "Fire Drill":
        ev.all_day = True
        ev.start = ev.start.replace(hour=0, minute=0, second=0)
        ev.end = ev.start + timedelta(days=1)

    # include all other entries
    return True
```
