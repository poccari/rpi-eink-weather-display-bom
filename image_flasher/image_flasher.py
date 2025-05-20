"""
service which will run and get screenshot of weather dash
Flashes screenshot to e-ink display
"""


import requests
from PIL import Image
from inky.auto import auto
import subprocess
from pijuice import PiJuice
import os
import time
import arrow
import json




import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler



class image_flasher:
    def __init__(self,config,pijuice_addr=0x14):
        """
        config is dictionary loaded from json, with keys:
        wakeup_hours: list of int hours to wake up and take screenshot
        timezone:string timezone to use for wakeup hours,
        low_battery_threshold: int percentage to consider low battery
        
        """
        self.setup_logger(level = config.get('logging_level',logging.INFO))
        self.pijuice_addr = pijuice_addr
        self.configure(config)

        
        try:
            self.pj = self.get_pijuice()
        except Exception as e:
            self.flash_display(self.error_image_fp)
        self.set_up_display()
        



    def setup_logger(self,name='image_flasher', log_dir='logs',log_file='image_flasher.log', level=logging.INFO):
        """
        Set up a logger that writes to both the console and a rotating log file.
        Log file rotates when it reaches 1MB, keeping 5 backups.
        """
        if isinstance(level, str):
            level_str = level.upper()
            level = getattr(logging, level_str, None)
            if not isinstance(level, int):
                raise ValueError(f"Invalid log level string: {level_str}")
        elif not isinstance(level, int):
            raise TypeError("Level must be a string or an int (e.g., logging.DEBUG).")

        if os.path.exists(log_dir) == False:
            os.makedirs(log_dir)
        log_file = os.path.join(log_dir, log_file)

        self.logger = logging.getLogger(name)
        self.logger.setLevel(level)

        if not self.logger.hasHandlers():
            # Console handler
            ch = logging.StreamHandler(sys.stdout)
            ch.setLevel(level)
            ch_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
            ch.setFormatter(ch_formatter)

            # File handler with rotation
            log_path = Path(log_file)
            log_path.parent.mkdir(parents=True, exist_ok=True)
            fh = RotatingFileHandler(
                filename=log_path,
                maxBytes=1 * 1024 * 1024,  # 1 MB
                backupCount=5
            )
            fh.setLevel(level)
            fh_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            fh.setFormatter(fh_formatter)

            # Add handlers
            self.logger.addHandler(ch)
            self.logger.addHandler(fh)

    def configure(self, config):
        """
        Configure the image flasher with the config dictionary.
        Will apoly default values if not present in the config.
        """
        self.config = config
        self.internet_check_url = config.get('internet_check_url', 'www.google.com')
        self.WAKEUP_ON_CHARGE_BATTERY_LEVEL = config.get('wakeup_on_charge_battery_level', 0)
        self.screenshot_webpage = "http://localhost:5000/"
        self.screenshot_width = 600
        self.screenshot_height = 448
        self.inky_display = None
        self.image_dir = os.path.join(os.path.dirname(__file__),"weather_images")
        if not os.path.exists(self.image_dir):
            os.makedirs(self.image_dir)
        self.image_fp = os.path.join(self.image_dir,"weather.png")
        self.error_image_fp = os.path.join(os.path.dirname(__file__),"service_images","error.png")
        self.no_internet_image_fp = os.path.join(os.path.dirname(__file__),"service_images","no_internet.png")
        self.low_battery_image_fp = os.path.join(os.path.dirname(__file__),"service_images","low_battery.png")

        self.wakeup_hours = config.get('wakeup_hours', [0, 6, 12, 18])
        self.timezone = config.get('timezone', 'Australia/Adelaide')
        self.low_battery_threshold = config.get('low_battery_threshold', 10)
        forecast_location = config.get('forecast_location', {'latitude': -34.92866000, 'longitude': 138.59863000})
        self.forecast_lat = forecast_location.get('latitude', -34.92866000)
        self.forecast_long = forecast_location.get('longitude', 138.59863000)
        

    def check_clocks(self):
        """
        Check if the system clock is synchronized with NTP and if the RTC is synchronized with the system clock.
        If not, it will sync the RTC with the system clock.
        """
        if not self.is_ntp_synchronized():
            self.logger.debug("NTP is not synchronized. Waiting for NTP sync...")
            if not self.wait_for_ntp_sync():
                self.logger.debug("NTP sync timed out. Setting time from RTC.")
                self.set_time_from_RTC()
            else:
                self.logger.debug("NTP synchronized.")
        else:
            self.logger.debug("NTP is synchronized.")

        if not self.check_RTC_is_synchronized():
            self.logger.debug("RTC is not synchronized with system clock. Syncing RTC...")
            self.set_RTC()
        else:
            self.logger.debug("RTC is synchronized with system clock.")


    def set_time_from_RTC(self):
        resp = self.pj.rtcAlarm.GetTime()

        if resp['error'] == 'NO_ERROR':
            rtc = resp['data']
            rtc_time = arrow.Arrow(
                    rtc['year'], rtc['month'], rtc['day'],
                    rtc['hour'], rtc['minute'], rtc['second'],
                    tzinfo='UTC'
                )

            # Format time for `date` command
            time_str = rtc_time.format("DD MMMM YYYY HH:mm:ss ZZZ")
        
            # Set system time
            subprocess.run(['sudo', 'date', '-s', time_str])
            print("System time updated from PiJuice RTC.")
        else:
            print("Failed to read RTC time from PiJuice:", resp['error'])

    def is_ntp_synchronized(self):
        result = subprocess.run(['timedatectl'], capture_output=True, text=True)
        return "System clock synchronized: yes" in result.stdout

    def wait_for_ntp_sync(self,timeout=60):
        print("Waiting for NTP sync...")
        start = time.time()
        while time.time() - start < timeout:
            if self.is_ntp_synchronized():
                print("✅ NTP synchronized.")
                return True
            time.sleep(2)
        print("❌ Timed out waiting for NTP sync.")
        return False

    def check_RTC_is_synchronized(self,tolerance=60):
        """
        Check if the RTC is synchronized with the system clock.
        If not, it will sync the RTC with the system clock.
        """
        resp = self.pj.rtcAlarm.GetTime()
        if resp['error'] == 'NO_ERROR':
            rtc = resp['data']
            rtc_time = arrow.Arrow(
                    rtc['year'], rtc['month'], rtc['day'],
                    rtc['hour'], rtc['minute'], rtc['second'],
                    tzinfo='UTC'
                )
            return abs(rtc_time-arrow.utcnow()).total_seconds() < tolerance
        else:
            print("Failed to read RTC time from PiJuice:", resp['error'])
            return False
    
    def set_RTC(self):
        now = arrow.utcnow()

        # Prepare the time dictionary for SetTime
        rtc_time = {
            'second': now.second,
            'minute': now.minute,
            'hour': now.hour,
            'weekday': (now.weekday() + 1) % 7 + 1,  # Adjusting to PiJuice format
            'day': now.day,
            'month': now.month,
            'year': now.year,
            'subsecond': now.microsecond // 1000000  # Will always be 0, since microsecond < 1_000_000
        }
        self.pj.rtcAlarm.SetTime(rtc_time)




    def update_screen(self):
        """
        Update the screen with the latest weather data., or update the screen with other error images etc
        """
        self.logger.info('Updating screen ...')
        # Get the latest weather data
        connection_found = self.wait_until_internet_connection()
        battery_percentage = self.get_battery_percentage()
        if battery_percentage < self.low_battery_threshold:
            self.logger.info('Battery level is %f which is below threshold of %d. Flashing low battery image', battery_percentage, self.low_battery_threshold)
            image_to_flash = self.low_battery_image_fp
        else:
            if not connection_found:
                self.logger.info('No internet connection found. Flashing no connection image')
                image_to_flash = self.no_internet_image_fp
            else:
                self.get_screenshot()
                image_to_flash = self.image_fp
        # Flash the display with the new image
        self.flash_display(image_to_flash)

    def get_battery_percentage(self):
        """
        Get the battery percentage from the PiJuice.
        """
        try:
            battery_percentage = self.pj.status.GetChargeLevel()
            return battery_percentage['data']
        except Exception as e:
            self.logger.error('Error getting battery percentage: %s', e)
            return None

    def get_screenshot(self):
        #use following command as subprocess to save screenshot to file
        # subprocess.run(["scrot", image_filepath])
        #TODO: put more error handling in here'
        battery_percentage = self.get_battery_percentage()
        subprocess.run(["wkhtmltoimage", 
                        "--width", str(self.screenshot_width), 
                        "--height", str(self.screenshot_height), 
                        f"{self.screenshot_webpage}?battery-status={battery_percentage}&lat={self.forecast_lat}&long={self.forecast_long}", 
                        self.image_fp])

    def set_up_display(self):
        try:
            self.inky_display = auto(ask_user=True, verbose=True)
        except TypeError:
            raise TypeError("You need to update the Inky library to >= v1.1.0")

        try:
            self.inky_display.set_border(self.inky_display.BLACK)
        except NotImplementedError:
            pass
        return True

    def flash_display(self,image_path):
        """
        
        TODO: put more error handling in here - if no weather data, no image, etc
        """
        if self.inky_display.resolution in ((self.screenshot_width, self.screenshot_height),):
            #not sure if this is necessary as we control the image ,but to be sure?
            img = Image.open(image_path)
            img = img.resize(self.inky_display.resolution)
        # Display the weather dash
        img = Image.open(image_path)
        self.inky_display.set_image(img)
        self.inky_display.show()

    def get_pijuice(self):
        
        pj = PiJuice(1, self.pijuice_addr)
        start = time.time()
        while True:
            if time.time() - start > 30:
                raise Exception('Timeout waiting for PIJuice to be ok')

            stat = pj.status.GetStatus()
            if stat['error'] == 'NO_ERROR':
                return pj
            else:
                time.sleep(0.1)

    def is_pijuice_on_battery(self):
        stat = self.pj.status.GetStatus()
        data = stat['data']
        return data['powerInput'] == "NOT_PRESENT" and data['powerInput5vIo'] == 'NOT_PRESENT'


    def is_ssh_active(self):
        result = self.run_cmd('ss -a | grep ssh | grep ESTAB')
        lines = result.stdout.decode('utf-8').strip().split()
        return len(lines) > 0

    def run_cmd(self,cmd):
        self.logger.info('Running "{}"'.format(cmd))
        result = subprocess.run(cmd, shell=True, capture_output=True)
        self.logger.info('stdout: %s\tstderr: %s', result.stdout, result.stderr)
        return result

    def wait_until_internet_connection(self):
        self.logger.info('Waiting for internet connection ...')

        # Try to check for internet connection
        connection_found = self.loop_until_internet()

        if connection_found:
            return True
        else:
            self.logger.info(
                'Internet connection not yet found, restarting networking...')
            # If not found, restart networking
            self.run_cmd('sudo ifconfig wlan0 down')
            time.sleep(5)
            self.run_cmd('sudo ifconfig wlan0 up')
            time.sleep(5)

        self.logger.info('Checking for internet again...')
        # Check for internet again
        if self.loop_until_internet():
            return True
        return False



    def loop_until_internet(self,times=3):
        for i in range(times):
            try:
                res = requests.get(self.internet_check_url, params={
                    'ping': 'true'}, timeout=8)
                if res.status_code == 200:
                    self.logger.info('Internet connection found!')
                    return True
            except Exception as e:
                self.logger.info('Internet connection not found. Attempt %d/%d', i+1, times)
                self.logger.debug('Address checked: %s, Error: %s', self.internet_check_url,e)
                continue

        return False



    def enable_wakeups(self,local_hours,timezone_str):

        utc_hours = self.local_hours_to_utc(local_hours, timezone_str)
        alarm_config = {
            'second': 0,
            'minute': 0,
            'hour': ';'.join(map(str, utc_hours)),
            'day': 'EVERY_DAY'
        }
        self.logger.debug('pj.rtcAlarm.SetAlarm() with params: {}'.format(alarm_config))
        self.pj.rtcAlarm.SetAlarm(alarm_config)
        self.logger.debug('pj.rtcAlarm.GetAlarm(): {}'.format(pj.rtcAlarm.GetAlarm()))
        # It looked like it's possible that time sync unsets the RTC alarm.
        # https://github.com/PiSupply/PiJuice/issues/362
        self.logger.debug('Enabling RTC wakeup alarm ...')
        self.pj.rtcAlarm.SetWakeupEnabled(True)
        self.logger.debug('Enabling wakeup on charge (%s) ...',str(self.WAKEUP_ON_CHARGE_BATTERY_LEVEL))
        self.pj.power.SetWakeUpOnCharge(self.WAKEUP_ON_CHARGE_BATTERY_LEVEL)

    def disable_wakeups(self):
        self.logger.debug('Disabling RTC wakeup alarm ...')
        self.pj.rtcAlarm.SetWakeupEnabled(False)
        self.logger.debug('Enabling wakeup on charge (%s) ...', str(self.WAKEUP_ON_CHARGE_BATTERY_LEVEL))
        self.pj.power.SetWakeUpOnCharge(self.WAKEUP_ON_CHARGE_BATTERY_LEVEL)

    def local_hours_to_utc(self,local_hours, timezone_str):
        utc_hours = []
        today = arrow.now(timezone_str).floor('day')  # Midnight today in local time zone

        for hour in local_hours:
            # Add the hour to today, keeping it in local time zone
            local_time = today.shift(hours=hour)
            utc_time = local_time.to('UTC')
            utc_hours.append(utc_time.hour)
        utc_hours.sort()
        return utc_hours

    def shutdown(self):
        """
        Sets the apprropiate wakups based on battery level
        and shuts down the system.
        
        """
        battery_percentage = self.get_battery_percentage()
        if battery_percentage < self.low_battery_threshold:
            self.logger.info('Battery level is %f which is below threshold of %d. Disabling wakeups', battery_percentage, self.low_battery_threshold)
            self.disable_wakeups()
        else:
            self.logger.info('Battery level is %f which is above threshold of %d. Enabling wakeups', battery_percentage, self.low_battery_threshold)
            self.enable_wakeups(self.wakeup_hours, self.timezone)

        self.logger.info('Shutting down ...')
        # Make sure power to the Raspberry PI is stopped to not discharge the battery
        self.pj.power.SetSystemPowerSwitch(0)
        self.pj.power.SetPowerOff(15)  # Cut power after n seconds
        os.system("sudo shutdown -h now")

    def ok_to_shutdown(self):
        """
        Check if the system is ok to shutdown.
        if it is on external poer or if there is an active ssh session, don't shutdown
        """
        return not (self.is_pijuice_on_battery() or self.is_ssh_active())
    
    def time_until_next_wakeup(self):
        """
        Get the time until the next wakeup.
        """
        now = arrow.now(self.timezone)
        today = now.floor('day')
        deltas = []
        for hour in self.wakeup_hours:
            candidate = today.shift(hours=hour)
            if candidate <= now:
                candidate = candidate.shift(days=1)
            delta = candidate - now
            deltas.append(delta)
        return min(deltas).total_seconds()
    


if __name__ == "__main__":
    """
    * get screenshot (pass battery % as argument?)
    * get display
    * flash image
    *shut down if required
        *shutdown process involves:
            * getting next wake time from config
            * setting next wake time in pijuice
            * if SSH session is there or on external power, don't send poweroff and just wait for next wakeup
            * else - send poweroff signal to pijuice and also shut down the pi
    """
    
    config_fp = os.path.abspath(os.path.join(os.path.dirname(__file__),"..","config.json"))
    with open(config_fp, 'r') as f:
        config = json.load(f)
    IFHandler = image_flasher(config)
    IFHandler.check_clocks()
    while True:
        IFHandler.update_screen()
        if IFHandler.ok_to_shutdown():
            IFHandler.shutdown()
            break
        else:
            timeUntilNextWakeup = IFHandler.time_until_next_wakeup()
            now = arrow.now(IFHandler.timezone)
            IFHandler.logger.debug('System is still connected to power or SSH session is active. Not shutting down. ssh-state:%s. Pijuice on battery state:%s',IFHandler.is_ssh_active(),IFHandler.is_pijuice_on_battery())
            IFHandler.logger.info("wairing for next wakeup in %f seconds at %s",timeUntilNextWakeup,now.shift(seconds=timeUntilNextWakeup).format("DD-MM-YYYY HH:mm:ss"))
            time.sleep(timeUntilNextWakeup)  # Sleep until next wakeup


                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   