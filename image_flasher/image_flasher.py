"""
service which will run and get screenshot of weather dash
Flashes screenshot to e-ink display
"""


import requests
from PIL import Image
from inky.auto import auto


def get_screenshot(image_path,battery_percentage):
    #use following command as subprocess to save screenshot to file
    # subprocess.run(["scrot", image_filepath])
    #subprocess.run([wkhtmltoimage, "--width 600", "--height 448", f"http://localhost:5000/?battery-status={battery_percentage}" image_path])
    pass

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
    if inky_display.resolution in ((600, 448),):
        #not sure if this is necessary as we control the image ,but to be sure?
        img = Image.open(image_path)
        img = img.resize(inky_display.resolution)
    # Display the weather dash
    img = Image.open(image_path)
    inky_display.set_image(img)
    inky_display.show()


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
    pass