# eink-weather-display

Battery-powered E-Ink weather display for our home. The device wakes up early in the morning, fetches latest weather forecast information, updates the info to the E-Ink display, and goes back to deep sleep until tomorrow.
Inspiration taken from https://github.com/kimmobrunfeldt/eink-weather-display and uses pi zero with pijuice, but that's about where the similarities end. 


**Goals:**

* Easily glanceable weather forecast at the heart of our home. Ideally eliminates one more reason to pick up the phone (And allows our children to see weather without a device).
* Looks like a "real product". The housing should look professional.
* Fully battery-powered. We didn't want a visible cable, and drilling the cable inside wall wasn't an option, as well as postable.
* Always visible and doesn't light up the hallway during evening / night -> e-Ink display.
* Primarily for our use case, but with reusability in mind. For example custom location and timezone 


Most weather APIs and algorithms aren't so great in Australia, so this uses Australian Weather source (BoM).

**Weather panel render**

Runs a flask app, which pulls data from data source based on config file, and renders to webpage. 
Takes render to PNG to flash to e-ink display



**attributions**

 'weather icon images from Flaticon.com'.