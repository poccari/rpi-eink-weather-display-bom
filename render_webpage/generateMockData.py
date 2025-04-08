import collector
import os
import json

tstfixpath = os.path.join(os.path.dirname(__file__), 'testFixtures')
filename = "mockWeatherData2.json"
outFN = os.path.join(tstfixpath, filename)

lat = -34.92866000   
long =  138.59863000

mycol = collector.Collector(lat,long)
mycol.async_update()

endDict = {}
endDict['observations_data'] = mycol.observations_data['data']
endDict['hourly_forecasts_data'] = mycol.hourly_forecasts_data['data']
endDict['daily_forecasts_data'] = mycol.daily_forecasts_data['data']
endDict['warnings_data'] = mycol.warnings_data['data']
endDict['locations_data'] = mycol.locations_data['data']
# Write the data to a JSON file
with open(outFN, 'w') as outfile:
    outfile.write(json.dumps(endDict, indent=4))
