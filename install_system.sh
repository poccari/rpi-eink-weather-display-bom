#!/bin/bash
set -e

#check that you're running as root, as this only works when you're root
if [ `whoami` != root ]; then
    echo Please run this script as root or using sudo
    exit
fi

SCRIPTHOME="$( cd "$(dirname "$0")" ; pwd -P )"
CURRENTUSER=$(logname)

#check I2C is enabled


# Check if I2C is enabled
I2C_ENABLED=$(sudo raspi-config nonint get_i2c)

if [ "$I2C_ENABLED" -eq 0 ]; then
    echo "I2C is already enabled."
else
    echo "I2C is disabled. Enabling now..."
    sudo raspi-config nonint do_i2c 0
    if [ $? -eq 0 ]; then
        echo "I2C has been successfully enabled."
    else
        echo "Failed to enable I2C."
        exit 1
    fi
fi

#install wkhtmltopdf for lightweight image generation from webpage
apt install -y wkhtmltopdf


cd render_webpage
#create virtual environment for service, and install requirements
python -m venv ./.render_webpage_venv/
source ./.render_webpage_venv/bin/activate
pip install -r requirements.txt

#move dashboard_generator service 
sed -i -e "s%<ExecLocation>%$SCRIPTHOME/render_webpage%" weather_renderer.service
sed -i -e "s%<username>%$CURRENTUSER%" weather_renderer.service
sed -i -e "s%<venvpath>%$SCRIPTHOME/render_webpage/.render_webpage_venv/bin%" weather_renderer.service
mv weather_renderer.service /lib/systemd/system/

systemctl enable weather_renderer.service
systemctl start weather_renderer.service


#install pijuice
apt-get install -y pijuice-base
