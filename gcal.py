#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from collections import namedtuple
from functools import lru_cache
from typing import Optional

# noinspection PyProtectedMember
from googleapiclient.discovery import Resource, build
from httplib2 import Http
from oauth2client import file, client, tools

AUTH_CACHE_FILE = 'auth_token.json'
AUTH_CREDENTIALS_FILE = 'credentials.json'
SCOPES = 'https://www.googleapis.com/auth/calendar https://www.googleapis.com/auth/calendar.readonly'

SummaryIdTuple = namedtuple('SummaryIdTuple', ('summary', 'id'))
SummaryIdTuple.__str__ = lambda self: '"{}" id: {}'.format(self.summary, self.id)


@lru_cache()
def filter_summary_id_tuple(iterable: (SummaryIdTuple, ...), selector: str = None) -> (SummaryIdTuple, ...):
    return tuple(c for c in iterable if selector in c.summary or c.id == selector) if selector is not None else iterable


@lru_cache()
def get_service() -> Resource:
    store = file.Storage(AUTH_CACHE_FILE)
    credentials = store.get()
    if not credentials or credentials.invalid:
        flow = client.flow_from_clientsecrets(AUTH_CREDENTIALS_FILE, SCOPES)
        credentials = tools.run_flow(flow, store)
    return build(serviceName='calendar', version='v3', http=credentials.authorize(Http()))


@lru_cache()
def list_calendars() -> (SummaryIdTuple, ...):
    return tuple(SummaryIdTuple(cal.get('summary'), cal.get('id')) for cal in
                 get_service().calendarList().list().execute().get('items', ()))


def list_events(calendar_id: str) -> (SummaryIdTuple, ...):
    events = ()
    page_token = ''
    while page_token is not None:
        results = get_service().events().list(calendarId=calendar_id, pageToken=page_token, maxResults=2500).execute()
        events += tuple(SummaryIdTuple(event.get('summary'), event.get('id')) for event in results.get('items', ()))
        page_token = results.get('nextPageToken')
    return events


def print_format_dict(x: dict) -> str:
    return '\n'.join('{}: {}'.format(k, v) for k, v in x.items())


def print_format_summary_id_tuples(x: (SummaryIdTuple, ...)) -> str:
    return '\n'.join('{}. {}: {}'.format(n + 1, c.summary, c.id) for n, c in enumerate(x))


@lru_cache()
def str_list_is_none(arg: str) -> Optional[str]:
    if arg.lower() != 'list':
        return arg


if __name__ == '__main__':
    from sys import argv

    usage = """Usage:
    {0} [Calendar Selector] [Event Selector] [list|delete|copy] [copy ARGS]
    {0}                                               : print usage
    {0} list                                          : print list of calendars
    {0} CalendarSelector [list]                       : print all events in calendar matching CalendarSelector
    {0} CalendarSelector EventSelector [list]         : print matching events
    {0} CalendarSelector EventSelector delete         : delete matching events
    {0} CalendarSelector EventSelector copy PREFIX(s) : create new event with each PREFIX added to the subject
    
    note: provide oauth credentials in file credentials.json
    """.format(argv[0])
    num_args = len(argv)
    calendar_selector = str_list_is_none(argv[1]) if num_args > 1 else None
    event_selector = str_list_is_none(argv[2]) if num_args > 2 else None
    command = argv[3].lower() if num_args > 3 else 'usage' if num_args == 1 else 'list'
    command_args = sorted(argv[4:]) if num_args > 4 else None
    get_service()

    if command == 'copy' and command_args is None:
        command = 'usage'

    if command == 'usage':
        print(usage)
        exit(0)

    if calendar_selector is None:
        print('\n'.join('Calendar: {}'.format(c) for c in list_calendars()))
        exit(0)

    for selected_calendar in filter_summary_id_tuple(list_calendars(), calendar_selector):
        print('Calendar: {}'.format(selected_calendar))
        for selected_event in filter_summary_id_tuple(list_events(selected_calendar[1]), event_selector):
            if command == 'list':
                print('Event: {}'.format(selected_event))
            elif command == 'delete':
                print('deleting event "{}" from "{}"'.format(selected_event[0], selected_calendar[0]))
                get_service().events().delete(calendarId=selected_calendar[1], eventId=selected_event[1]).execute()
            elif command == 'copy':
                print('copying event "{}" to {}'.format(selected_event[0], ', '.join(command_args)))
                info = get_service().events().get(calendarId=selected_calendar[1], eventId=selected_event[1]).execute()
                summary = info['summary']
                for attrib in ('created', 'creator', 'etag', 'htmlLink', 'iCalUID', 'id', 'sequence', 'updated'):
                    info.pop(attrib)
                for i, prefix in enumerate(command_args):
                    info['summary'] = '{:02d} {}: {}'.format(i + 1, prefix, summary)
                    info['colorId'] = (i % 10) + 1
                    new_event = get_service().events().insert(calendarId=selected_calendar[1], body=info).execute()
                    print('New Event: {}'.format(SummaryIdTuple(new_event['summary'], new_event['id'])))
