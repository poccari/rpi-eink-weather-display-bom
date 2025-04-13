from flask import Flask, render_template, request
import requests
import os
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By 
from collector import Collector
import arrow
import argparse

from PIL import Image

app = Flask(__name__)
lat = -34.92866000
long =  138.59863000
testing = True
testPath = os.path.join(os.path.dirname(__file__), 'testFixtures', 'mockWeatherData.json')






@app.route('/')
def index():
    print(f"Testing mode: {testing}")
    mycol = Collector(lat, long,test=testing, test_json=testPath)
    mycol.async_update()
    battery_status = 89
    current_data = mycol.observations_data['data']
    hourly_forecast = mycol.hourly_forecasts_data['data'][0:10]
    daily_forecast = mycol.daily_forecasts_data['data'][0:6]
    weather_warnings = mycol.warnings_data['data']
    locations_data = mycol.locations_data['data']
    time = arrow.now()
    timeStrings = {'date':time.format("dddd, D MMMM"),
                   'time':time.format("h:mm A")}
    return render_template('index.html', 
                           timeStrings=timeStrings, 
                           battery_status=battery_status, 
                           current_data=current_data, 
                           hourly_forecast=hourly_forecast, 
                           daily_forecast=daily_forecast, 
                           weather_warnings=weather_warnings,
                           locations_data=locations_data)

@app.route('/screenshot')
def screenshot():
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--force-device-scale-factor=1")
    options.add_argument("--disable-infobars")
    options.add_argument("--hide-scrollbars")
    options.add_argument("--disable-extensions")
    options.add_argument("--window-size=600,448")
    options.binary_location = "/usr/bin/chromium-browser"  # Update if needed

    service = Service("/usr/bin/chromedriver")  # Update if needed

    driver = webdriver.Chrome(service=service, options=options)
    driver.set_window_size(600, 448+100)  #

    # Optional: confirm
    print("Adjusted to:", driver.execute_script("return [window.innerWidth, window.innerHeight]"))

  

    driver.execute_script("window.resizeTo(600, 448);")
    driver.get("http://127.0.0.1:5000/")
    # driver.save_screenshot('weather.png')
    element = driver.find_element(By.ID, "weather-container")
    driver.execute_script("arguments[0].scrollIntoView(true);", element)
    print("Element size:", element.size)
    element.screenshot("weather.png")
    img = Image.open('weather.png')
    print(f"Image size: {img.width}x{img.height}")
    print(driver.title)
    driver.quit()
    return "Screenshot saved as weather.png"


def parse_arguments():
    parser = argparse.ArgumentParser(description="Runs a flask application which grabs and renders weather data from BOM API")
    parser.add_argument("--testing", action="store_true", help="Enable test mode doesn't pull from BOM and uses stored data in json.")
    return parser.parse_args()

def main():
    global testing
    args = parse_arguments()
    testing = args.testing
    print(f"Testing mode: {testing}")
    app.run(debug=True,host="0.0.0.0", port=5000)

if __name__ == '__main__':
    main()

