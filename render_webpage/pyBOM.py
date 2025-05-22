"""BOM data 'collector' that downloads the observation data."""
import logging
import requests
import datetime
import json
import os
import arrow

# Some functionality in this file is adapted from https://github.com/bremor/bureau_of_meteorology
# I have adapted this code to work better with my use case
# Copyright (c) Bremor https://github.com/bremor
# Licensed under the MIT License. See the full license text below.

"""
MIT License

Copyright (c) 2019 Custom cards for Home Assistant

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

"""Constants for PyBoM."""

MAP_MDI_ICON = {
    "clear": "night",
    "cloudy": "cloudy",
    "cyclone": "hurricane",
    "dust": "hazy",
    "dusty": "hazy",
    "fog": "fog",
    "frost": "snowflake-melt",
    "haze": "hazy",
    "hazy": "hazy",
    "heavy_shower": "pouring",
    "heavy_showers": "pouring",
    "light_rain": "partly-rainy",
    "light_shower": "light-showers",
    "light_showers": "light-showers",
    "mostly_sunny": "sunny",
    "partly_cloudy": "partly-cloudy",
    "rain": "pouring",
    "shower": "rainy",
    "showers": "rainy",
    "snow": "snowy",
    "storm": "lightning-rainy",
    "storms": "lightning-rainy",
    "sunny": "sunny",
    "tropical_cyclone": "hurricane",
    "wind": "windy",
    "windy": "windy",
    "windy_rain": "windy_rain",
    None: None,
}
MAP_UV = {
    "extreme": "Extreme",
    "veryhigh": "Very High",
    "high": "High",
    "moderate": "Moderate",
    "low": "Low",
    None: None,
}

URL_BASE = "https://api.weather.bom.gov.au/v1/locations/"
URL_DAILY = "/forecasts/daily"
URL_HOURLY = "/forecasts/hourly"
URL_OBSERVATIONS = "/observations"
URL_WARNINGS = "/warnings"


def flatten_dict(keys, dict):
    for key in keys:
        if dict[key] is not None:
            flatten = dict.pop(key)
            for inner_key, value in flatten.items():
                dict[key + "_" + inner_key] = value
    return dict

def geohash_encode(latitude, longitude, precision=6):
    base32 = '0123456789bcdefghjkmnpqrstuvwxyz'
    lat_interval = (-90.0, 90.0)
    lon_interval = (-180.0, 180.0)
    geohash = []
    bits = [16, 8, 4, 2, 1]
    bit = 0
    ch = 0
    even = True
    while len(geohash) < precision:
        if even:
            mid = (lon_interval[0] + lon_interval[1]) / 2
            if longitude > mid:
                ch |= bits[bit]
                lon_interval = (mid, lon_interval[1])
            else:
                lon_interval = (lon_interval[0], mid)
        else:
            mid = (lat_interval[0] + lat_interval[1]) / 2
            if latitude > mid:
                ch |= bits[bit]
                lat_interval = (mid, lat_interval[1])
            else:
                lat_interval = (lat_interval[0], mid)
        even = not even
        if bit < 4:
            bit += 1
        else:
            geohash += base32[ch]
            bit = 0
            ch = 0
    return ''.join(geohash)

_LOGGER = logging.getLogger(__name__)

class BOM_Forecast:
    """PyBoM class to pull forecast data from BOM API."""

    def __init__(self, latitude, longitude,test=False,test_json=None):
        """Init collector."""
        self.locations_data = None
        self.observations_data = None
        self.daily_forecasts_data = None
        self.hourly_forecasts_data = None
        self.warnings_data = None
        self.geohash7 = geohash_encode(latitude, longitude)
        self.geohash6 = self.geohash7[:6]
        self.test = test
        self.test_json = test_json
        self.timezone = 'UTC'

    def get_locations_data(self):
        headers={"User-Agent": "MakeThisAPIOpenSource/1.0.0"}
        """Get JSON location name from BOM API endpoint."""

        response = requests.get(URL_BASE + self.geohash7)

        if response is not None and response.status == 200:
            self.locations_data = response.json()
            print(f"Locations data: {self.locations_data}")
            self.timezone = self.locations_data["data"].get(["timezone"],'UTC')

    def format_daily_forecast_data(self):
        """Format forecast data."""
        days = len(self.daily_forecasts_data["data"])
        for day in range(0, days):

            d = self.daily_forecasts_data["data"][day]

            d["mdi_icon"] = MAP_MDI_ICON[d["icon_descriptor"]]
            if d["icon_descriptor"] in ["wind",'windy'] and d['rain']['chance'] > 20:
                d["mdi_icon"] = MAP_MDI_ICON["windy_rain"]
            arrowTS = arrow.get(d["date"])
            tzawareTS = arrowTS.to(self.timezone)
            d["day"] =tzawareTS.format("dddd")#format to day of week, e.g. Monday
            #get sunrise and sunset times in string
            sunrise = arrow.get(d["astronomical"]["sunrise_time"])
            tzawareSunrise = sunrise.to(self.timezone)
            d["astronomical"]["sunrise_formatted"] = tzawareSunrise.format("h:mma")#format to hr and am/pm, e.g. 1pm
            sunset = arrow.get(d["astronomical"]["sunset_time"])
            tzawareSunset = sunset.to(self.timezone)
            d["astronomical"]["sunset_formatted"] = tzawareSunset.format("h:mma")#format to hr and am/pm, e.g. 1pm
            # print(f"TS String: {d["date"]} tzawareTS: {tzawareTS}, d_day: {d["day"]} maxtemp: {d['temp_max']} TZ: {self.timezone}")
            flatten_dict(["amount"], d["rain"])
            flatten_dict(["rain", "uv", "astronomical"], d)

            if day == 0:
                flatten_dict(["now"], d)

            # If rain amount max is None, set as rain amount min
            if d["rain_amount_max"] is None:
                d["rain_amount_max"] = d["rain_amount_min"]
                d["rain_amount_range"] = d["rain_amount_min"]
            else:
                d["rain_amount_range"] = f"{d['rain_amount_min']}–{d['rain_amount_max']}"

    def format_hourly_forecast_data(self):
        """Format forecast data."""
        hours = len(self.hourly_forecasts_data["data"])
        for hour in range(0, hours):

            d = self.hourly_forecasts_data["data"][hour]
            arrowTS = arrow.get(self.hourly_forecasts_data["data"][hour]["time"])
            tzawareTS = arrowTS.to(self.timezone)
            d["hour_str"] = tzawareTS.format("ha")#format to hr and am/pm, e.g. 1pm
            d["mdi_icon"] = MAP_MDI_ICON[d["icon_descriptor"]]
            if d["icon_descriptor"] in ["wind",'windy'] and d['rain']['chance'] > 20:
                d["mdi_icon"] = MAP_MDI_ICON["windy_rain"]

            flatten_dict(["amount"], d["rain"])
            flatten_dict(["rain", "wind"], d)

            # If rain amount max is None, set as rain amount min
            if d["rain_amount_max"] is None:
                d["rain_amount_max"] = d["rain_amount_min"]
                d["rain_amount_range"] = d["rain_amount_min"]
            else:
                d["rain_amount_range"] = f"{d['rain_amount_min']} to {d['rain_amount_max']}"


    def get_forecast(self):
        """get forecast data from API endpoint.
        if the object is initialised with test=True, it will populate from the test_json file"""
        if self.test:
            self.populate_test_data()
            return
        headers={"User-Agent": "MakeThisAPIOpenSource/1.0.0"}
        response = requests.get(URL_BASE + self.geohash7, headers=headers)
        if response is not None and response.status_code == 200:
            self.locations_data = response.json()
            self.timezone = self.locations_data["data"].get("timezone",'UTC')
        else:
            _LOGGER.error("Unable to get locations data from BOM API")

        response = requests.get(URL_BASE + self.geohash6 + URL_OBSERVATIONS, headers=headers)
        if response is not None and response.status_code == 200:
            self.observations_data = response.json()
            if self.observations_data["data"].get("wind",None) is not None:
                flatten_dict(["wind"], self.observations_data["data"])
            else:
                self.observations_data["data"]["wind_direction"] = "unavailable"
                self.observations_data["data"]["wind_speed_kilometre"] = "unavailable"
                self.observations_data["data"]["wind_speed_knot"] = "unavailable"
            if self.observations_data["data"]["gust"] is not None:
                flatten_dict(["gust"], self.observations_data["data"])
            else:
                self.observations_data["data"]["gust_speed_kilometre"] = "unavailable"
                self.observations_data["data"]["gust_speed_knot"] = "unavailable"

        resp = requests.get(URL_BASE + self.geohash6 + URL_DAILY, headers=headers)
        if resp is not None and resp.status_code == 200:
            self.daily_forecasts_data = resp.json()
            self.format_daily_forecast_data()

        resp = requests.get(URL_BASE + self.geohash6 + URL_HOURLY, headers=headers)
        if resp is not None and resp.status_code == 200:
            self.hourly_forecasts_data = resp.json()
            self.format_hourly_forecast_data()

        resp = requests.get(URL_BASE + self.geohash6 + URL_WARNINGS, headers=headers)
        if resp is not None and resp.status_code == 200:
            self.warnings_data = resp.json()

    def populate_test_data(self):
        """Populate test data."""
        print("Populating test data from JSON file")
        if self.test_json is not None:
            with open(self.test_json, 'r') as json_file:
                data = json.load(json_file)
                self.observations_data = {'data':data['observations_data']}
                self.hourly_forecasts_data = {'data':data['hourly_forecasts_data']}
                self.daily_forecasts_data = {'data':data['daily_forecasts_data']}
                self.warnings_data ={'data': data['warnings_data']}
                self.locations_data = {'data':data['locations_data']}
