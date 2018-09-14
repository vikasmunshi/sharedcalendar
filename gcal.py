#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from googleapiclient.discovery import build
from httplib2 import Http
from oauth2client import file, client, tools

AUTH_CACHE_FILE = 'auth_token.json'
AUTH_CREDENTIALS_FILE = 'credentials.json'
SCOPES = 'https://www.googleapis.com/auth/calendar https://www.googleapis.com/auth/calendar.readonly'


def get_service():
    store = file.Storage(AUTH_CACHE_FILE)
    credentials = store.get()
    if not credentials or credentials.invalid:
        flow = client.flow_from_clientsecrets(AUTH_CREDENTIALS_FILE, SCOPES)
        credentials = tools.run_flow(flow, store)
    return build(serviceName='calendar', version='v3', http=credentials.authorize(Http()))


def list_calendars() -> ((str, str), ...):
    return tuple((c['summary'], c['id']) for c in get_service().calendarList().list().execute().get('items', ()))


def list_events(calendar_id: str, single_events: bool = False) -> ((str, str), ...):
    return tuple((e['summary'], e['id']) for e in get_service().events().list(
        calendarId=calendar_id, singleEvents=single_events).execute().get('items', ()))


def print_dict(x: dict) -> str:
    return '\n'.join('{}: {}'.format(k, v) for k, v in x.items())


def print_tuple(x: ((str, str), ...)) -> str:
    return '\n'.join('{}. {}: {}'.format(n + 1, *c) for n, c in enumerate(x))


if __name__ == '__main__':
    from sys import argv

    usage = """Usage:
    {0} [Calendar Name or Calendar ID] [Event ID] [ACTION] [ACTION ARGS]
    {0}                               : print list of calendars
    {0} CalendarName                  : print events in calendar with name starting with CalendarName or calendar list
    {0} CalendarID                    : print events in calendar with id CalendarID
    {0} Calendar EventName            : print event with name starting with EventName or list of events
    {0} Calendar EventID              : print event with id EventID
    {0} Calendar Event DELETE         : delete event
    {0} Calendar Event COPY PREFIX(s) : create new event with each PREFIX added to the subject
    """.format(argv[0])
    all_calendars = list_calendars()
    if len(argv) == 1:
        print(usage)
        print('Available calendars:')
        print(print_tuple(all_calendars))
        exit(0)
    filtered_calendars = tuple(c for c in all_calendars if str(c[0]).startswith(argv[1]) or c[1] == argv[1])
    selected_calendar = filtered_calendars[0] if len(filtered_calendars) == 1 else None
    if selected_calendar is None:
        print('Matching calendars:')
        print(print_tuple(filtered_calendars))
        exit(0)
    else:
        print('Selected calendar {}, id {}'.format(*selected_calendar))
    all_events = list_events(selected_calendar[1], single_events=False)
    if len(argv) == 2:
        print('Events in {}:'.format(selected_calendar[0]))
        print(print_tuple(all_events))
        exit(0)
    filtered_events = tuple(e for e in all_events if str(e[0]).startswith(argv[2]) or e[1] == argv[2])
    selected_event = filtered_events[0] if len(filtered_events) == 1 else None
    if selected_event is None:
        print('Matching events:')
        print(print_tuple(filtered_events))
        exit(0)
    else:
        print('Selected event {}, id {}'.format(*selected_event))
    event_info = get_service().events().get(calendarId=selected_calendar[1], eventId=selected_event[1]).execute()
    if len(argv) == 3:
        print(print_dict(event_info))
        exit(0)
    if argv[3].lower() in 'delete':
        choice = input('Confirm deleting event "{}" from calendar "{}" [Yes{}]: '.format(
            selected_event[0], selected_calendar[0], chr(0x000021B5)))
        if choice.lower() in 'yes':
            get_service().events().delete(calendarId=selected_calendar[1], eventId=selected_event[1]).execute()
        exit(0)
    if argv[3].lower() in 'copy' and len(argv) > 4:
        for attrib in ('created', 'creator', 'etag', 'htmlLink', 'iCalUID', 'id', 'kind', 'organizer', 'sequence',
                       'updated',):
            event_info.pop(attrib)
        event_summary = event_info['summary']
        for i, prefix in enumerate(argv[4:]):
            event_info['summary'] = '{:02d}.{}: {}'.format(i + 1, prefix, event_summary)
            event_info['colorId'] = (i % 10) + 1
            new_event = get_service().events().insert(calendarId=selected_calendar[1], body=event_info).execute()
            print(new_event['summary'], new_event['id'])
    else:
        print(usage)
