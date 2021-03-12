from __future__ import print_function

import logging
import time
import string
import re
import sys
#import pickle

import googleapiclient
import arrow
from icalevents.icalevents import events
from dateutil.tz import gettz

from datetime import datetime, timezone, timedelta

from auth import auth_with_calendar_api
from config import ICAL_FEED, FILES, CALENDAR_ID, API_SLEEP_TIME, ICAL_DAYS_TO_SYNC, LOGFILE

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = logging.FileHandler(filename=LOGFILE, mode='a')
handler.setFormatter(logging.Formatter('%(asctime)s|[%(levelname)s] %(message)s'))
logger.addHandler(handler)

DEFAULT_TIMEDELTA = timedelta(days=365)


def get_current_events_from_files():
    
    """Retrieves data from iCal files.  Assumes that the files are all
    *.ics files located in a single directory.

    Returns the parsed Calendar object of None if no events are found.

    """

    from glob import glob
    from os.path import join

    event_ics = glob(join(ICAL_FEED, '*.ics'))

    if len(event_ics) > 0:
        ics = event_ics[0]
        cal = get_current_events(ics)
        for ics in event_ics[1:]:
            evt = get_current_events(ics)
            if len(evt) > 0:
                cal.extend(evt)
        return cal
    else:
        return None

def get_current_events(feed):
    """Retrieves data from iCal iCal feed and returns an ics.Calendar object 
    containing the parsed data.

    Returns the parsed Calendar object or None if an error occurs.
    """

    events_end = datetime.now()
    if ICAL_DAYS_TO_SYNC == 0:
        # default to 1 year ahead
        events_end += DEFAULT_TIMEDELTA
    else:
        # add on a number of days
        events_end += timedelta(days=ICAL_DAYS_TO_SYNC)

    try:
        if FILES:
            cal = events(file=feed, end=events_end)
        else:
            cal = events(feed, end=events_end)
    except Exception as e:
        logger.error('> Error retrieving iCal data ({})'.format(e))
        return None

    return cal

def get_gcal_events(service, from_time):
    """Retrieves the current set of Google Calendar events from the selected
    user calendar. Only includes upcoming events (those taking place from start
    of the current day. 

    Returns a dict containing the event(s) existing in the calendar.
    """

    # The list() method returns a dict containing various metadata along with the actual calendar entries (if any). 
    # It is not guaranteed to return all available events in a single call, and so may need called multiple times
    # until it indicates no more events are available, signalled by the absence of "nextPageToken" in the result dict

    logger.debug('Retrieving Google Calendar events')

    # make an initial call, if this returns all events we don't need to do anything else,,,
    eventsResult = service.events().list(calendarId=CALENDAR_ID, 
                                         timeMin=from_time, 
                                         singleEvents=True, 
                                         orderBy='startTime', 
                                         showDeleted=True).execute()

    events = eventsResult.get('items', [])
    # if nextPageToken is NOT in the dict, this should be everything
    if 'nextPageToken' not in eventsResult:
        logger.info('> Found {:d} upcoming events in Google Calendar (single page)'.format(len(events)))
        return events

    # otherwise keep calling the method, passing back the nextPageToken each time
    while 'nextPageToken' in eventsResult:
        token = eventsResult['nextPageToken']
        eventsResult = service.events().list(calendarId=CALENDAR_ID, 
                                             timeMin=from_time, 
                                             pageToken=token, 
                                             singleEvents=True, 
                                             orderBy='startTime', 
                                             showDeleted=True).execute()
        newevents = eventsResult.get('items', [])
        events.extend(newevents)
        logger.debug('> Found {:d} events on new page, {:d} total'.format(len(newevents), len(events)))
    
    logger.info('> Found {:d} upcoming events in Google Calendar (multi page)'.format(len(events)))
    return events

def delete_all_events(service):
    for gc in get_gcal_events(service):
        try:
            service.events().delete(calendarId=CALENDAR_ID, eventId=gc['id']).execute()
            time.sleep(API_SLEEP_TIME)
        except googleapiclient.errors.HttpError:
            pass # event already marked as deleted

def get_gcal_datetime(py_datetime, gcal_timezone):
    py_datetime = py_datetime.astimezone(gettz(gcal_timezone))
    return {u'dateTime': py_datetime.strftime('%Y-%m-%dT%H:%M:%S%z'), 'timeZone': gcal_timezone}

def get_gcal_date(py_datetime):
    return {u'date': py_datetime.strftime('%Y-%m-%d')}

def create_id(uid, begintime, endtime):
    """ Converts ical UUID, begin and endtime to a valid Gcal ID

    Characters allowed in the ID are those used in base32hex encoding, i.e. lowercase letters a-v and digits 0-9, see section 3.1.2 in RFC2938
    Te length of the ID must be between 5 and 1024 characters
    https://developers.google.com/resources/api-libraries/documentation/calendar/v3/python/latest/calendar_v3.events.html

    Returns:
        ID
    """
    allowed_chars = string.ascii_lowercase[:22] + string.digits
    return re.sub('[^{}]'.format(allowed_chars), '', uid.lower()) + str(arrow.get(begintime).timestamp) + str(arrow.get(endtime).timestamp)

if __name__ == '__main__':
    # setting up Google Calendar API for use
    logger.debug('> Loading credentials')
    service = auth_with_calendar_api()

    # dateime instance representing the start of the current day (UTC)
    today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)

    # retrieve events from Google Calendar, starting from beginning of current day
    logger.info('> Retrieving events from Google Calendar')
    gcal_events = get_gcal_events(service, today.isoformat())

    # retrieve events from the iCal feed
    logger.info('> Retrieving events from iCal feed')
    if FILES:
        ical_cal = get_current_events_from_files()
    else:
        ical_cal = get_current_events(ICAL_FEED)

    if ical_cal is None:
        sys.exit(-1)

    # convert iCal event list into a dict indexed by (converted) iCal UID
    ical_events = {}

    for ev in ical_cal:
        # explicitly set any events with no timezone to use UTC (icalevents
        # doesn't seem to do this automatically like ics.py)
        if ev.start.tzinfo is None:
            ev.start = ev.start.replace(tzinfo=timezone.utc)
        if ev.end is not None and ev.end.tzinfo is None:
            ev.end = ev.end.replace(tzinfo=timezone.utc)

        ical_events[create_id(ev.uid, ev.start, ev.end)] = ev

    logger.debug('> Collected {:d} iCal events'.format(len(ical_events)))

    # retrieve the Google Calendar object itself
    gcal_cal = service.calendars().get(calendarId=CALENDAR_ID).execute()

    logger.info('> Processing Google Calendar events...')
    gcal_event_ids = [ev['id'] for ev in gcal_events]

    # first check the set of Google Calendar events against the list of iCal
    # events. Any events in Google Calendar that are no longer in iCal feed
    # get deleted. Any events still present but with changed start/end times
    # get updated.
    for gcal_event in gcal_events:
        eid = gcal_event['id']

        if eid not in ical_events:
            # if a gcal event has been deleted from iCal, also delete it from gcal.
            # Apparently calling delete() only marks an event as "deleted" but doesn't
            # remove it from the calendar, so it will continue to stick around. 
            # If you keep seeing messages about events being deleted here, you can
            # try going to the Google Calendar site, opening the options menu for 
            # your calendar, selecting "View bin" and then clicking "Empty bin 
            # now" to completely delete these events.
            try:
                logger.info(u'> Deleting event "{}" from Google Calendar...'.format(gcal_event.get('summary', '<unnamed event>')))
                service.events().delete(calendarId=CALENDAR_ID, eventId=eid).execute()
                time.sleep(API_SLEEP_TIME)
            except googleapiclient.errors.HttpError:
                pass # event already marked as deleted
        else:
            ical_event = ical_events[eid]
            gcal_begin = arrow.get(gcal_event['start'].get('dateTime', gcal_event['start'].get('date')))
            gcal_end = arrow.get(gcal_event['end'].get('dateTime', gcal_event['end'].get('date')))

            gcal_has_location = 'location' in gcal_event
            ical_has_location = ical_event.location is not None

            gcal_has_description = 'description' in gcal_event
            ical_has_description = ical_event.description is not None

            # event name can be left unset, in which case there's no summary field
            gcal_name = gcal_event.get('summary', None)
            log_name = '<unnamed event>' if gcal_name is None else gcal_name

            # check if the iCal event has a different: start/end time, name, location,
            # or description, and if so sync the changes to the GCal event
            if gcal_begin != ical_event.start\
                or gcal_end != ical_event.end\
                or gcal_name != ical_event.summary\
                or gcal_has_location != ical_has_location \
                or (gcal_has_location and gcal_event['location'] != ical_event.location) \
                or gcal_has_description != ical_has_description \
                or (gcal_has_description and gcal_event['description'] != ical_event.description):

                logger.info(u'> Updating event "{}" due to date/time change...'.format(log_name))
                delta = ical_event.end - ical_event.start
                # all-day events handled slightly differently
                # TODO multi-day events?
                if delta.days >= 1:
                    gcal_event['start'] = get_gcal_date(ical_event.start)
                    gcal_event['end'] = get_gcal_date(ical_event.end)
                else:
                    gcal_event['start'] = get_gcal_datetime(ical_event.start, gcal_cal['timeZone'])
                    if ical_event.end is not None:
                        gcal_event['end']   = get_gcal_datetime(ical_event.end, gcal_cal['timeZone'])

                gcal_event['summary'] = ical_event.summary
                gcal_event['description'] = ical_event.description
                if FILES:
                    url_feed = 'https://www.google.com'
                else:
                    url_feed = ICAL_FEED
                gcal_event['source'] = {'title': 'imported from ical_to_gcal_sync.py', 'url': url_feed}
                gcal_event['location'] = ical_event.location

                service.events().update(calendarId=CALENDAR_ID, eventId=eid, body=gcal_event).execute()
                time.sleep(API_SLEEP_TIME)

    # now add any iCal events not already in the Google Calendar 
    logger.info('> Processing iCal events...')
    for ical_id, ical_event in ical_events.items():
        if ical_id not in gcal_event_ids:
            gcal_event = {}
            gcal_event['summary'] = ical_event.summary
            gcal_event['id'] = ical_id
            gcal_event['description'] = '%s (Imported from mycal.py)' % ical_event.description
            gcal_event['location'] = ical_event.location

            # check if no time specified in iCal, treat as all day event if so
            delta = ical_event.end - ical_event.start
            # TODO multi-day events?
            if delta.days >= 1:
                gcal_event['start'] = get_gcal_date(ical_event.start)
                logger.info(u'iCal all-day event {} to be added at {}'.format(ical_event.summary, ical_event.start))
                if ical_event.end is not None:
                    gcal_event['end'] = get_gcal_date(ical_event.end)
            else:
                gcal_event['start'] = get_gcal_datetime(ical_event.start, gcal_cal['timeZone'])
                logger.info(u'iCal event {} to be added at {}'.format(ical_event.summary, ical_event.start))
                if ical_event.end is not None:
                    gcal_event['end'] = get_gcal_datetime(ical_event.end, gcal_cal['timeZone'])

            try:
                time.sleep(API_SLEEP_TIME)
                service.events().insert(calendarId=CALENDAR_ID, body=gcal_event).execute()
            except:
                time.sleep(API_SLEEP_TIME)
                service.events().update(calendarId=CALENDAR_ID, eventId=gcal_event['id'], body=gcal_event).execute()
