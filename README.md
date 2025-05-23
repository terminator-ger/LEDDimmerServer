# LEDDimmerServer
Is a Python based REST-server on your Raspi that acts as control-devices
between the LED-Strip and your [Android App](https://github.com/terminator-ger/LedDimmerWidget).

## Installation
It is build upon a standard Raspian installation. 

```bash
 sudo apt-get install python        #python 2.7
 sudo apt-get install python-pip 
 sudo apt-get install rpi.gpio
 ```
Use pip to install all dependencies 
```python
pip install -r python_dependencies.txt
```

Start PI-GPIOD on boot, root is important here
```bash
sudo crontab -e
```
and then add the lines
```bash
@reboot     /usr/local/bin/pigpiod
@reboot     nohup python LEDDimmerServer.py &
```
to start the gpio daemon and the LEDDimmer.

