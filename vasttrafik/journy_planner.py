# -*- coding: utf-8 -*-
"""
Västtrafik API
"""

import base64
import json
import requests
import urllib.parse
from datetime import datetime
from datetime import timedelta

TOKEN_URL = 'https://ext-api.vasttrafik.se/token'
API_BASE_URL = 'https://ext-api.vasttrafik.se/pr/v4'


class Error(Exception):
    pass


def _get_node(response, *ancestors):
    """ Traverse tree to node """
    document = response
    for ancestor in ancestors:
        if ancestor not in document:
            return {}
        else:
            document = document[ancestor]
    return document


def _format_datetime(date: datetime):
    if date.tzinfo is None:
        default_tz = datetime.now().astimezone().tzinfo
        date = date.replace(tzinfo=default_tz)
    return urllib.parse.quote(date.isoformat())


class JournyPlanner:
    """ Journy planner class"""

    def __init__(self, key, secret, expiery=59):
        self._key = key
        self._secret = secret
        self._expiery = expiery
        self.update_token()

    def update_token(self):
        """ Get token from key and secret """
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Authorization': 'Basic ' + base64.b64encode(
                (self._key + ':' + self._secret).encode()).decode()
        }
        data = {'grant_type': 'client_credentials'}

        response = requests.post(TOKEN_URL, data=data, headers=headers)
        obj = json.loads(response.content.decode('UTF-8'))
        self._token = obj['access_token']
        self._token_expire_date = (
                datetime.now() +
                timedelta(minutes=self._expiery))

    # LOCATION

    def location_nearbystops(self, origin_coord_lat, origin_coord_long):
        """ location.nearbystops """
        response = self._request(
            'locations/by-coordinates',
            latitude=origin_coord_lat,
            longitude=origin_coord_long)
        return _get_node(response, 'results')

    def location_name(self, name):
        """ location.name """
        response = self._request(
            'locations/by-text',
            q=name,
            types='stoparea')
        return _get_node(response, 'results')

    # ARRIVAL BOARD
    def arrivalboard(self, stop_id, date=None, direction=None):
        """ arrivalBoard """
        date = date if date else datetime.now()
        request_parameters = {
            'startDateTime': _format_datetime(date)
        }
        if direction:
            request_parameters['directionGid'] = direction
        response = self._request(
            f'stop-areas/{stop_id}/arrivals',
            **request_parameters)
        return _get_node(response, 'results')

    # DEPARTURE BOARD
    def departureboard(self, stop_id, date=None, direction=None):
        """ departureBoard """
        date = date if date else datetime.now()
        request_parameters = {
            'startDateTime': _format_datetime(date)
        }
        if direction:
            request_parameters['directionGid'] = direction
        response = self._request(
            f'stop-areas/{stop_id}/departures',
            **request_parameters)
        return _get_node(response, 'results')

    # TRIP

    def trip(self, origin_id, dest_id, date=None):
        """ trip """
        date = date if date else datetime.now()
        response = self._request(
            'journeys',
            originGid=origin_id,
            destinationGid=dest_id,
            dateTime=_format_datetime(date))
        return _get_node(response, 'results')

    def _request(self, service, **parameters):
        """ request builder """
        urlformat = "{baseurl}/{service}?{parameters}"
        url = urlformat.format(
            baseurl=API_BASE_URL,
            service=service,
            parameters="&".join([
                "{}={}".format(key, value) for key, value in parameters.items()
            ]))
        if datetime.now() > self._token_expire_date:
            self.update_token()
        headers = {'Authorization': 'Bearer ' + self._token}
        res = requests.get(url, headers=headers)
        if res.status_code == 200:
            return json.loads(res.content.decode('UTF-8'))
        else:
            raise Error('Error: ' + str(res.status_code) +
                        str(res.content))
