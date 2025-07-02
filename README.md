# LEDDimmerServer
[![codecov](https://codecov.io/gh/terminator-ger/LEDDimmerServer/branch/master/graph/badge.svg?token=9B8U9NB1JJ)](https://codecov.io/gh/terminator-ger/LEDDimmerServer)

Is a Python based REST-server on your Raspi that acts as control-devices
between the LED-Strip and your [Android App](https://github.com/terminator-ger/Sunriser).

## Installation
# Install using pypi
```bash
python -m pip install LEDDimmerServer
```

# Setup 
```bash
sudo cp LEDDimmerServer.service /etc/system.d/system
sudo systemctl daemon-reload
sudo systemctl start LEDDimmerServer
```

Start PI-GPIOD on boot, root is important here
```bash
sudo crontab -e
```
and then add the lines
```bash
@reboot     /usr/local/bin/pigpiod
```
to start the gpio daemon and the LEDDimmer.



