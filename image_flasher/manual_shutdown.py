"""
manually shuts down the system but allows wakups
#TODO: read from config file
#TODO: use argparse to pass in flags for no wakeups etc
"""

import logging
from image_flasher import shutdown, get_pijuice, enable_wakeups
import os
import json


mylogger = logging.getLogger(__name__)

if __name__ == '__main__':
    logging.info('Running shutdown.py')
    piJuice_addr = 0x14
    pj = get_pijuice(piJuice_addr)
    config_fp = os.path.abspath(os.path.join(os.path.dirname(__file__),"..","config.json"))
    with open(config_fp, 'r') as f:
        config = json.load(f)
    enable_wakeups(pj,config['wakeup_hours'], config['timezone'])
    shutdown(pj,passedLogger=mylogger)