from flask import Flask, render_template, request, redirect, url_for
import os
from pyBOM import BOM_Forecast as pyBOM
import arrow
import argparse
import json
import io
import base64


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
    config_data = load_config()#think about getting lat long from config file rather than passed in via args
    nHours_to_show = config_data.get('hourly_forecast_n_hours', 12)
    hourly_graph = config_data.get('hourly_forecast_as_graph', True)
    
    forcast = pyBOM(lat_read, long_read,test=testing, test_json=testPath)
    forcast.get_forecast()
    current_data = forcast.observations_data['data']
    if hourly_graph:
        # Generate SVG for hourly forecast
        png_bytes = generate_weather_png(forcast.hourly_forecasts_data['data'], hours_to_show=nHours_to_show)
        hourly_png = base64.b64encode(png_bytes).decode('utf-8')
    else:
        # If not generating SVG, set hourly_svg to None
        # This is to avoid rendering an empty SVG in the template
        # when hourly graph is not enabled.
        hourly_png = None
    daily_forecast = forcast.daily_forecasts_data['data'][0:6]
    weather_warnings = forcast.warnings_data['data']
    locations_data = forcast.locations_data['data']
    hourly_forecast = forcast.hourly_forecasts_data['data']
    time = arrow.now()
    timeStrings = {'date':time.format("dddd, D MMMM"),
                   'time':time.format("h:mm A")}
    return render_template('index.html', 
                           timeStrings=timeStrings, 
                           battery_status=batteryPC, 
                           current_data=current_data, 
                           hourly_png=hourly_png, 
                           hourly_forecast=hourly_forecast,
                           daily_forecast=daily_forecast, 
                           weather_warnings=weather_warnings,
                           locations_data=locations_data)

def generate_weather_png(hourly_forecast, hours_to_show=None):
    import matplotlib
    matplotlib.use('svg')  # Use 
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    import datetime
    import pytz
    from scipy.interpolate import make_interp_spline
    import numpy as np
    config_data = load_config()
    config_timezone = config_data.get('timezone', 'Australia/Adelaide')
    # print(f"Config timezone: {config_timezone}")
    #get the limited number of hours to show
    limited_forecast = hourly_forecast[:hours_to_show] 
    #build the hours and temp and rain chance lists
    times = [arrow.get(h["time"]).to(config_timezone).datetime for h in limited_forecast]
    temps = [h["temp"] for h in limited_forecast]
    rain_chance = [h["rain_chance"] for h in limited_forecast]
    rain_min = [h["rain_amount_min"] for h in limited_forecast]
    rain_max = [h["rain_amount_max"] for h in limited_forecast]
    rain_range = [max_val - min_val for min_val, max_val in zip(rain_min, rain_max)]
    rain_mean = [(lo + hi) / 2 for lo, hi in zip(rain_min, rain_max)]
    rain_error = [(hi - lo) / 2 for lo, hi in zip(rain_min, rain_max)]
    # Create figure
    locator = mdates.AutoDateLocator(minticks=4, maxticks=10)
    formatter = mdates.DateFormatter('%-I%p',tz=pytz.timezone(config_timezone))
    fig, ax1 = plt.subplots(figsize=(10, 5), dpi=120)

    tick_fontsize = 20
    # Temperature lines
    # Plot temperature with ±5°C range
    #smooth the temperature line
    x = mdates.date2num(times)  # Convert datetime objects to matplotlib's date format
    x_array = np.array(x)
    x_smooth = np.linspace(x_array.min(), x_array.max(), 300)
    spl = make_interp_spline(x, temps, k=3)  # k=3: cubic spline
    y_smooth_temps = spl(x_smooth)
    ax1.plot(x_smooth, y_smooth_temps, label="Temp (°C)", color="tab:red",linewidth =5)
    ax1.set_ylabel("Temperature (°C)", color="tab:red",fontsize=tick_fontsize)
    ax1.tick_params(axis='y', labelcolor='tab:red')
    ax1.tick_params(axis='both', labelsize=tick_fontsize) 
    ax1.xaxis.set_major_locator(locator)
    ax1.xaxis.set_major_formatter(formatter)

    # 2nd Y-axis: Rain Chance (%)
    ax2 = ax1.twinx()
    ax2.bar(times, rain_chance, width=datetime.timedelta(hours=1), color="blue", alpha=0.6, label="Rain Chance")
    ax2.set_ylim(0, 100)
    ax2.set_ylabel("Rain Chance (%)", color="blue",fontsize=tick_fontsize)
    ax2.tick_params(axis='y', labelcolor='blue')

    # 3rd Y-axis: Rain Min/Max range (as error bars)
    ax3 = ax1.twinx()
    ax3.spines["right"].set_position(("axes", 1.12))  # Shift right side spine outward
    ax3.fill_between(times, rain_min, rain_max, color='green', alpha=0.2, label='Rain Amount Range (mm)')
    ax3.set_ylabel("Rain Amount (mm)", color="tab:green",fontsize=tick_fontsize)
    ax3.tick_params(axis='y', labelcolor='tab:green')
    ax3.set_ylim(0, max(rain_max) * 1.1)  # Set y-limit to accommodate rain range
    ax3.spines["right"].set_position(("outward", 80))
    ax3.tick_params(axis='y', pad=4)  # default is ~4–5
 
    ax2.tick_params(axis='y', labelsize=tick_fontsize) 
    ax3.tick_params(axis='y', labelsize=tick_fontsize) 

    # Collect all legend handles and labels from all axes
    handles1, labels1 = ax1.get_legend_handles_labels()
    handles2, labels2 = ax2.get_legend_handles_labels()
    handles3, labels3 = ax3.get_legend_handles_labels()

    # Combine and place the legend on the figure
    # ax1.legend(
    #     handles1 + handles2 + handles3,
    #     labels1 + labels2 + labels3,
    #     ncol=3,
    #     loc='upper center',
    #     frameon=False
    # )

    fig.autofmt_xdate(rotation=30)
    fig.tight_layout()

    # Write to SVG in-memory
    
    png_io = io.BytesIO()
    fig.savefig(png_io, format='png', bbox_inches='tight')  # 'bbox_inches=tight' helps reduce whitespace
    plt.close(fig)

    png_io.seek(0)

    return png_io.getvalue()


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
    app.run(debug=True,host="0.0.0.0", port=5006)

if __name__ == '__main__':
    main()

