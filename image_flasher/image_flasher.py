"""
service which will run and get screenshot of weather dash
Flashes screenshot to e-ink display
"""


import requests

response = requests.get("http://127.0.0.1/screenshot")
with open("weather_screenshot.png", "wb") as f:
    f.write(response.content)
