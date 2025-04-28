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


WAKEUP_ON_CHARGE_BATTERY_LEVEL = 0
config = {}
config['RENDER_URL'] = 'www.google.com'  # TODO: replace with actual render URL
#config - wakeup hours and timezone

import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler

import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler

def setup_logger(name='my_logger', log_dir='logs',log_file='app.log', level=logging.INFO):
    """
    Set up a logger that writes to both the console and a rotating log file.
    Log file rotates when it reaches 1MB, keeping 5 backups.
    """
    if os.path.exists(log_dir) == False:
        os.makedirs(log_dir)
    log_file = os.path.join(log_dir, log_file)

    logger = logging.getLogger(name)
    logger.setLevel(level)

    if not logger.hasHandlers():
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
        logger.addHandler(ch)
        logger.addHandler(fh)

    return logger



logger = setup_logger('image_flasher', "logs", 'image_flasher.log')


def set_time_from_RTC(pj):
    resp = pj.rtcAlarm.GetTime()

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

def is_ntp_synchronized():
    result = subprocess.run(['timedatectl'], capture_output=True, text=True)
    return "System clock synchronized: yes" in result.stdout

def wait_for_ntp_sync(timeout=60):
    print("Waiting for NTP sync...")
    start = time.time()
    while time.time() - start < timeout:
        if is_ntp_synchronized():
            print("✅ NTP synchronized.")
            return True
        time.sleep(2)
    print("❌ Timed out waiting for NTP sync.")
    return False

def check_RTC_is_synchronized(pj):
    """
    Check if the RTC is synchronized with the system clock.
    If not, it will sync the RTC with the system clock.
    """
    resp = pj.rtcAlarm.GetTime()
    if resp['error'] == 'NO_ERROR':
        rtc = resp['data']
        rtc_time = arrow.Arrow(
                rtc['year'], rtc['month'], rtc['day'],
                rtc['hour'], rtc['minute'], rtc['second'],
                tzinfo='UTC'
            )
        return rtc_time == arrow.utcnow()
    else:
        print("Failed to read RTC time from PiJuice:", resp['error'])
        return False
    
def set_RTC(pj):
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
    pj.rtcAlarm.SetTime(rtc_time)

def get_screenshot(image_path,battery_percentage):
    #use following command as subprocess to save screenshot to file
    # subprocess.run(["scrot", image_filepath])
    #TODO: put more error handling in here
    subprocess.run(["wkhtmltoimage", "--width", "600", "--height", "448", f"http://localhost:5000/?battery-status={battery_percentage}", image_path])

def set_up_display():
    try:
        inky_display = auto(ask_user=True, verbose=True)
    except TypeError:
        raise TypeError("You need to update the Inky library to >= v1.1.0")

    try:
        inky_display.set_border(inky_display.BLACK)
    except NotImplementedError:
        pass
    return inky_display

def flash_display(image_path,inky_display):
    """
    
    TODO: put more error handling in here - if no weather data, no image, etc
    """
    if inky_display.resolution in ((600, 448),):
        #not sure if this is necessary as we control the image ,but to be sure?
        img = Image.open(image_path)
        img = img.resize(inky_display.resolution)
    # Display the weather dash
    img = Image.open(image_path)
    inky_display.set_image(img)
    inky_display.show()

def get_pijuice(address):
    
    pj = PiJuice(1, address)
    start = time.time()
    while True:
        if time.time() - start > 30:
            raise Exception('Timeout waiting for PIJuice to be ok')

        stat = pj.status.GetStatus()
        if stat['error'] == 'NO_ERROR':
            return pj
        else:
            time.sleep(0.1)

def is_pijuice_on_battery(pj):
    stat = pj.status.GetStatus()
    data = stat['data']
    return data['powerInput'] == "NOT_PRESENT" and data['powerInput5vIo'] == 'NOT_PRESENT'


def is_ssh_active():
    result = run_cmd('ss -a | grep ssh | grep ESTAB')
    lines = result.stdout.decode('utf-8').strip().split()
    return len(lines) > 0

def run_cmd(cmd):
    logger.info('Running "{}"'.format(cmd))
    result = subprocess.run(cmd, shell=True, capture_output=True)
    logger.info('stdout:')
    logger.info(result.stdout)
    logger.info('stderr:')
    logger.info(result.stderr)
    logger.info('End of process output.')
    return result

def wait_until_internet_connection():
    logger.info('Waiting for internet connection ...')

    # Try to check for internet connection
    connection_found = loop_until_internet()

    if connection_found:
        return
    else:
        logger.info(
            'Internet connection not yet found, restarting networking...')
        # If not found, restart networking
        run_cmd('sudo ifconfig wlan0 down')
        time.sleep(5)
        run_cmd('sudo ifconfig wlan0 up')
        time.sleep(5)

    logger.info('Checking for internet again...')
    # Check for internet again
    if loop_until_internet():
        return

    raise Exception('Timeout waiting for internet connection')


def loop_until_internet(times=3):
    for i in range(times):
        try:
            res = requests.get(config['RENDER_URL'], params={
                'ping': 'true'}, timeout=8)
            if res.status_code == 200:
                logger.info('Internet connection found!')
                return True
        except:
            continue

    return False



def enable_wakeups(pj,local_hours,timezone_str):

    utc_hours = local_hours_to_utc(local_hours, timezone_str)
    alarm_config = {
        'second': 0,
        'minute': 0,
        'hour': ';'.join(map(str, utc_hours)),
        'day': 'EVERY_DAY'
    }
    logger.debug('pj.rtcAlarm.SetAlarm() with params: {}'.format(alarm_config))
    pj.rtcAlarm.SetAlarm(alarm_config)
    logger.debug('pj.rtcAlarm.GetAlarm(): {}'.format(pj.rtcAlarm.GetAlarm()))
    # It looked like it's possible that time sync unsets the RTC alarm.
    # https://github.com/PiSupply/PiJuice/issues/362
    logger.debug('Enabling RTC wakeup alarm ...')
    pj.rtcAlarm.SetWakeupEnabled(True)
    logger.debug('Enabling wakeup on charge ({}) ...'.format(
        WAKEUP_ON_CHARGE_BATTERY_LEVEL))
    pj.power.SetWakeUpOnCharge(WAKEUP_ON_CHARGE_BATTERY_LEVEL)

def local_hours_to_utc(local_hours, timezone_str):
    utc_hours = []
    today = arrow.now(timezone_str).floor('day')  # Midnight today in local time zone

    for hour in local_hours:
        # Add the hour to today, keeping it in local time zone
        local_time = today.shift(hours=hour)
        utc_time = local_time.to('UTC')
        utc_hours.append(utc_time.hour)
    utc_hours.sort()
    return utc_hours

def shutdown(pj,passedLogger = None):
    if passedLogger:
        logger = passedLogger

    logger.info('Shutting down ...')
    # Make sure power to the Raspberry PI is stopped to not discharge the battery
    pj.power.SetSystemPowerSwitch(0)
    pj.power.SetPowerOff(15)  # Cut power after n seconds
    os.system("sudo shutdown -h now")




if __name__ == "__main__":
    """
    * get screenshot (pass battery % as argument?)
    * get display
    * flash image
    *shut down if required
        *shutdown process involves:
            * getting next wake time from config?
            * setting next wake time in pijuice
            * if SSH session is there, don't send poweroff assume user is connected and leave it up to user
            * else - send poweroff signal to pijuice and also shut down the pi
    """
    piJuice_addr = 0x14
    config_fp = os.path.abspath(os.path.join(os.path.dirname(__file__),"..","config.json"))
    with open(config_fp, 'r') as f:
        config = json.load(f)

    logger.info("Config received: %s", config)

    imageDir = os.path.join(os.path.dirname(__file__),"weather_images")
    if not os.path.exists(imageDir):
        os.makedirs(imageDir)
    image_fp = os.path.join(imageDir,"weather.png")
    pj = get_pijuice(piJuice_addr)
    #enable wakeups early
    local_hours = [6, 10, 15, 18, 21]
    timezone_str = 'Australia/Adelaide'
    enable_wakeups(pj,config['wakeup_hours'], config['timezone'])
    # get battery percentage
    battery_percentage = pj.status.GetChargeLevel()

    #wait for NTP sync so correct time is set
    if not is_ntp_synchronized():
        timedout = wait_for_ntp_sync()
        if timedout:
            #no NTP, set time from RTC
            set_time_from_RTC(pj)

    if battery_percentage['data']< config['low_battery_threshold']:
        logger.info('Battery level is %f which is below threshold of %d. Flashing low battery image',battery_percentage['data'],config['low_battery_threshold'])
        image_fp = os.path.join(os.path.dirname(__file__),"service_images","low_battery.png")
    else:
        get_screenshot(image_fp,battery_percentage['data'])
    inky_display = set_up_display()
    flash_display(image_fp,inky_display)


    # Shut down the PiJuice - set alarms etc etc

    if is_pijuice_on_battery(pj) and not is_ssh_active():
    # if is_pijuice_on_battery(pj):
        logger.info('Shutting down the system ...')
        shutdown(pj,passedLogger=logger)
    else:
        logger.info(f'System is still connected to power or SSH session is active. Not shutting down. ssh-state:{is_ssh_active()}. Pijuice on battery state: {is_pijuice_on_battery(pj)}')