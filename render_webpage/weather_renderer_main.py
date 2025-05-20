from flask import Flask, render_template, request, redirect, url_for
import os
from pyBOM import BOM_Forecast as pyBOM
import arrow
import argparse
import json


app = Flask(__name__)

testing = True
configPath = os.path.abspath(os.path.join(os.path.dirname(__file__),"..", 'config.json'))
testPath = os.path.join(os.path.dirname(__file__), 'testFixtures', 'mockWeatherData.json')


# Default coordinates for Adelaide, Australia
lat = -34.92866000
long =  138.59863000

def load_config():
    with open(configPath) as f:
        return json.load(f)

def save_config(data):
    current = load_config()
    current['forecast_location'] = data['forecast_location']
    current['wakeup_hours'] = data['wakeup_hours']
    current['timezone'] = data['timezone']
    current['low_battery_threshold'] = data['low_battery_threshold']
    with open(configPath, 'w') as f:
        json.dump(current, f, indent=4)


def cast_to_float(value, default=0.0):
    try:
        return float(value)
    except (ValueError, TypeError) as e:
        return default

@app.route('/')
def index():
    print(f"Testing mode: {testing}")
    batteryPC = cast_to_float(request.args.get('battery-status'),0.0)
    lat_read = cast_to_float(request.args.get('lat'), lat)
    long_read = cast_to_float(request.args.get('long'), long)
    
    forcast = pyBOM(lat_read, long_read,test=testing, test_json=testPath)
    forcast.get_forecast()
    current_data = forcast.observations_data['data']
    hourly_forecast = forcast.hourly_forecasts_data['data'][0:10]
    daily_forecast = forcast.daily_forecasts_data['data'][0:6]
    weather_warnings = forcast.warnings_data['data']
    locations_data = forcast.locations_data['data']
    time = arrow.now()
    timeStrings = {'date':time.format("dddd, D MMMM"),
                   'time':time.format("h:mm A")}
    return render_template('index.html', 
                           timeStrings=timeStrings, 
                           battery_status=batteryPC, 
                           current_data=current_data, 
                           hourly_forecast=hourly_forecast, 
                           daily_forecast=daily_forecast, 
                           weather_warnings=weather_warnings,
                           locations_data=locations_data)

@app.route('/config', methods=['GET', 'POST'])
def config():
    config_data = load_config()
    if request.method == 'POST':
        new_data = {
            "forecast_location": {
                "latitude": float(request.form['latitude']),
                "longitude": float(request.form['longitude'])
            },
            "wakeup_hours": [int(h) for h in request.form.getlist('wakeup_hours')],
            "timezone": request.form['timezone'],
            "low_battery_threshold": int(request.form['low_battery_threshold'])
        }
        save_config(new_data)
        return redirect(url_for('config'))
    return render_template('config.html', config=config_data)

def parse_arguments():
    parser = argparse.ArgumentParser(description="Runs a flask application which grabs and renders weather data from BOM API")
    parser.add_argument("--testing", action="store_true", help="Enable test mode doesn't pull from BOM and uses stored data in json.")
    return parser.parse_args()

def main():
    global testing
    args = parse_arguments()
    testing = args.testing
    print(f"Testing mode: {testing}")
    app.run(debug=True,host="0.0.0.0", port=5005)

if __name__ == '__main__':
    main()

