# The iCal feed URL for the events that should be synced to the Google Calendar.
# Note that the syncing is one-way only.
ICAL_FEED = '<ICAL FEED URL>'

# the ID of the calendar to use for iCal events, should be of the form
# 'ID@group.calendar.google.com', check the calendar settings page to find it.
# (can also be 'primary' to use the default calendar)
CALENDAR_ID = '<GOOGLE CALENDAR ID>'

# must use the OAuth scope that allows write access
SCOPES = 'https://www.googleapis.com/auth/calendar'

# API secret stored in this file
CLIENT_SECRET_FILE = 'ical_to_gcal_sync_client_secret.json'

# Location to store API credentials
CREDENTIAL_PATH = 'ical_to_gcal_sync.pckl'

# Application name for the Google Calendar API
APPLICATION_NAME = 'ical_to_gcal_sync'

# File to use for logging output
LOGFILE = 'ical_to_gcal_sync_log.txt'

# Time to pause between successive API calls that may trigger rate-limiting protection
API_SLEEP_TIME = 0.05

# Number of days worth of iCal events to sync from the ICAL_FEED defined above.
# Must be a positive integer, e.g. 1 = events up to 24 hours ahead. Set to 0
# or negative value to sync all events (default)
ICAL_DAYS_TO_SYNC = 0
