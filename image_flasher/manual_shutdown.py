"""
manually shuts down the system but allows wakups
#TODO: use argparse to pass in flags for no wakeups etc
"""

from image_flasher import image_flasher
import os
import json


if __name__ == '__main__':
    with open(os.path.abspath(os.path.join(os.path.dirname(__file__),"..","config.json")), 'r') as f:
        config = json.load(f)
    flasher_Obj = image_flasher(config,pijuice_addr=0x14)
    flasher_Obj.shutdown()
   