

SCRIPTHOME="$( cd "$(dirname "$0")" ; pwd -P )"
CURRENTUSER=$(logname)

#install chromium and driver for webpage renderer
sudo apt install -y chromium-browser
sudo apt install -y chromium-chromedriver


cd render_webpage
#create virtual environment for service, and install requirements
python -m venv ./.render_webpage_venv/

#move dashboard_generator service 
sed -i -e "s%<ExecLocation>%$SCRIPTHOME/render_webpage%" weather_renderer.service
sed -i -e "s%<username>%$CURRENTUSER%" weather_renderer.service
sed -i -e "s%<venvpath>%$SCRIPTHOME/.render_webpage_venv/bin%" weather_renderer.service
mv weather_renderer.service /lib/systemd/system/

systemctl enable weather_renderer.service
systemctl start weather_renderer.service

#need to set I2C as on using raspi-config