from flask import Flask, render_template, request, send_file
import os
from pyBOM import BOM_Forecast as pyBOM
import arrow
import argparse



app = Flask(__name__)
lat = -34.92866000
long =  138.59863000
testing = True
testPath = os.path.join(os.path.dirname(__file__), 'testFixtures', 'mockWeatherData.json')


@app.route('/')
def index():
    print(f"Testing mode: {testing}")
    batteryPC = request.args.get('battery-status')
    print(f"battery PC: {batteryPC}, type: {type(batteryPC)}")
    if not batteryPC:
        battery_status = 0
    else:
        try:
            battery_status = float(batteryPC)
        except ValueError:
            battery_status = 0
    forcast = pyBOM(lat, long,test=testing, test_json=testPath)
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
                           battery_status=battery_status, 
                           current_data=current_data, 
                           hourly_forecast=hourly_forecast, 
                           daily_forecast=daily_forecast, 
                           weather_warnings=weather_warnings,
                           locations_data=locations_data)



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

