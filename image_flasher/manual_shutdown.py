"""
manually shuts down the system but allows wakups
#TODO: read from config file
#TODO: use argparse to pass in flags for no wakeups etc
"""

import logging
from image_flasher import shutdown, get_pijuice, enable_wakeups

if __name__ == '__main__':
    logging.info('Running shutdown.py')
    piJuice_addr = 0x14
    pj = get_pijuice(piJuice_addr)
    enable_wakeups(pj)
    shutdown(pj)