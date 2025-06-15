import json
import logging
import sys
import time
from datetime import datetime, timedelta, timezone
from threading import Lock, Timer
from typing import Dict, Tuple

import astral
from astral import Observer, sun
import pytz
import requests
import simplejson
from gpiozero import PWMLED, RGBLED

from LEDDimmerServer.color import get_sunrise_intensity, modify_json
from LEDDimmerServer.utc import UTC


class DimmerBackend:
    def __init__(self, config):
        self.on_off_w_pwm = 0.0
        self.wakeup_task = None
        self.is_in_wakeup_sequence: Lock = Lock()
        self.check_config(config)
        self.config = config

        # PIN CONFIGURATION
        # @see http://abyz.me.uk/rpi/pigpio/index.html#Type_3
        if self.config['has_w']:
            self.GPIO_W_PWM = PWMLED(pin=self.config["GPIO_W_PWM"])
            self.on_off_w_pwm = 0.0

        if self.config["has_rgb"]:
            self.GPIO_RGB = RGBLED(red=self.config["GPIO_R"],
                                   green=self.config["GPIO_G"],
                                   blue=self.config["GPIO_B"],
                                   pwm=False)
            self.GPIO_RGB_PWM = PWMLED(pin=self.config['GPIO_RGB_PWM'])
            self.on_off_rgb = (0, 0, 0)
            self.on_off_rgb_pwm = 0.0

        logging.info("hardware initialized")
        self.utc = UTC()
        self.epoch = datetime.now(tz=timezone.utc).timestamp()

    def check_config(self, config: Dict) -> bool:
        ''' Check if the config is valid
            :param config: The configuration dictionary 
        '''
        # one condition has to be set
        assert config['has_w'] or config['has_rgb']



    def toggle(self) -> bool:
        ''' Toggles the light on or off'''
        logging.debug("--- TOGGLE")

        if (self.config['has_w'] and self.GPIO_W_PWM.is_active) \
            or (self.config['has_rgb'] and self.GPIO_RGB_PWM.is_active):

            self.off()
        else:
            self.on()

        return True

    def on(self) -> bool:
        ''' Turns the light on
            If the light is already on, it does nothing.    
        '''

        if self.config["has_w"]:
            self.on_off_w_pwm = 1.0
            logging.debug("set w: %s", self.on_off_w_pwm)
            self.GPIO_W_PWM.value = self.on_off_w_pwm

        if self.config["has_rgb"]:
            self.on_off_rgb_pwm = 1.0
            logging.debug("set rgb: %s", self.on_off_rgb)
            self.GPIO_RGB_PWM.value = self.on_off_rgb_pwm
            
        return True

    def off(self) -> bool:
        ''' Turns the light off
            If the light is already off, it does nothing.
        '''
        # disable wakeup if there is one active...
        if (self.is_in_wakeup_sequence.locked() and
            self.wakeup_task is not None):
                self.wakeup_task.cancel()
                self.is_in_wakeup_sequence.release_lock()
                
        if self.config["has_w"]:
            logging.debug("set w: %s", self.on_off_w_pwm)
            self.on_off_w_pwm = 0
            self.GPIO_W_PWM.value = self.on_off_w_pwm

        if self.config["has_rgb"]:
            logging.debug("set rgb: %s", self.on_off_rgb)
            self.on_off_rgb_pwm = 0
            self.GPIO_RGB_PWM.value = self.on_off_rgb_pwm

        return True

    def incr(self) -> bool:
        ''' Increases the light intensity by 10%
            If the light is already at maximum intensity, it does nothing.  
        '''

        logging.debug("--- INCR")
        if self.config['has_w']:

            self.on_off_w_pwm = min(self.on_off_w_pwm + 0.10, 1)
            self.GPIO_W_PWM.value = self.on_off_w_pwm

        if self.config['has_rgb']:

            self.on_off_rgb_pwm = min(self.on_off_rgb_pwm + 0.10, 1)
            self.GPIO_RGB_PWM.value = self.on_off_rgb_pwm
            
        return True

    def decr(self) -> bool:
        ''' Decreases the light intensity by 10%
            If the light is already at minimum intensity, it does nothing.
        '''
        logging.debug("--- DECR")
        if self.config['has_w']:
            self.on_off_w_pwm = max(self.on_off_w_pwm - 0.10, 0)
            self.GPIO_W_PWM.value = self.on_off_w_pwm

        if self.config['has_rgb']:
            self.on_off_rgb_pwm = max(self.on_off_rgb_pwm - 0.10, 0)
            self.GPIO_RGB_PWM.value = self.on_off_rgb_pwm

        return True

    def wakeuptime(self, wakeup_time: int) -> Tuple[bool, int]:
        ''' Sets the wakeup time
            :param data_string: The data string containing the wakeup time in milliseconds since epoch  
            when the wakeup_time is 0 it will disable the wakeup sequence
            :return: A tuple containing a boolean indicating success and the wakeup time in seconds since epoch
        '''
        logging.debug("--- New wakeup time: ")
        
        if not isinstance(wakeup_time, int):
            raise TypeError("wakeup_time must be an integer")

        now = int(time.time())
        t = int((wakeup_time-now))

        logging.info("--- sheduling wakeup in ")
        logging.info("%d", t)
        logging.debug("killing old wakeups")
        logging.debug("returntime: ")
        logging.debug("%s", str(int(wakeup_time)))

        if self.wakeup_task is not None:
            self.wakeup_task.cancel()
        
        if self.is_in_wakeup_sequence.locked():
            # disable wakeup if there is one active...
            self.is_in_wakeup_sequence.release_lock()
            self.off()
        
        if wakeup_time == 0:
            logging.info("Wakeup sequence disabled")
            return (True, 0)
            
        self.wakeup_task = Timer(
            t - (self.config['active_profile']['wakeup_sequence_len'] * 60), self.start_incr_light)
        self.wakeup_task.start()
        return (True, wakeup_time)

    def sunrise(self) -> tuple[bool, int]:
        ''' Sets the wakeup time to the next sunrise
        '''
        logging.debug("--- Wakeup set to Sunrise ---")

        lat = float(self.config['latitude'])
        lon = float(self.config['longitude'])
        location = Observer(lat, lon)
        tomorrow = datetime.today() + timedelta(days=1)
        local_tz = pytz.timezone(self.config['time_zone'])

        wakeup_time = sun.dawn(location, date=tomorrow, tzinfo=local_tz)
        now = datetime.now(self.utc)

        t = wakeup_time - now

        
        if self.wakeup_task is not None and self.wakeup_task.is_alive():
            logging.debug("Wakeuptask was set - cancel it")
            self.wakeup_task.cancel()
            self.wakeup_task.join()
            return (True, 0)
       
        if self.is_in_wakeup_sequence.locked():
            # disable wakeup if there is one active...
            self.is_in_wakeup_sequence.release_lock()
            self.off() 

        logging.info("Wakeup at")
        logging.info("%s", wakeup_time)
        self.wakeup_task = Timer(t.total_seconds(
        ) - (self.config['active_profile']['wakeup_sequence_len'] * 60), self.start_incr_light)
        self.wakeup_task.start()
        return (True, int(wakeup_time.timestamp()))

    def color(self, dict: Dict) -> bool:
        '''
            name [[rgb], [rgb], ...]
        '''
        for key, values in dict.items():
            modify_json(key, values, "config/colors.json")
        return True

    def gradient(self, data: Dict) -> bool:
        '''
            name [[rgb], [rgb], ...]
        '''
        #key, values = data_string.split(" ")
        #values = [float(x) for x in values]
        for key, values in data.items():
            modify_json(key, values, "config/gradient.json")
        return True

    def preset(self, data_string) -> bool:
        '''
            preset color color_interpolation gradient gradient_interpolation wakeup_sequence_len pwm_steps
        '''
        key, values = data_string.split(" ")
        _dict = {"color": values[0],
                 "color_interpolation": values[1],
                 "gradient": values[2],
                 "gradient_interpolation": values[3],
                 "wakeup_sequence_len": values[4],
                 "pwm_steps": values[5]
                 }
        modify_json(key, _dict, 'presets.json')
        return True

    def default(self, data_string) -> bool:
        ''' Sets the default profile
            :param data_string: The data string containing the profile name
        '''
        _, profile = data_string.split(" ")
        modify_json('profile', profile, 'config/config.json')
        return True

    def update(self) -> None:
        ''' Updates the LED Dimmer Server
            This will download the latest version from the repository and restart the server.
        '''
        sys.exit(42)  # quit with code for update

    def start_incr_light(self) -> None:
        ''' Starts the wakeup sequence
            This will increase the light intensity over a period of time.
        '''
        logging.debug("starting up with the lightshow")
        self.is_in_wakeup_sequence.acquire()
        pause = (self.config['active_profile']
                 ['wakeup_sequence_len'] * 60) / self.config['active_profile']['pwm_steps']

        for progress in range(0, self.config['active_profile']['pwm_steps']):
            p = progress / self.config['active_profile']['pwm_steps']
            lum = get_sunrise_intensity(
                p, self.config['active_profile']['gradient_interpolation'], self.config['active_profile']['gradient'])
            logging.info("setting light to %s", str(lum))
            if self.config['has_w']:
                self.GPIO_W_PWM.value = lum
            if self.config['has_rgb']:
                self.GPIO_RGB_PWM.value = lum
                
            time.sleep(pause)
            if not self.is_in_wakeup_sequence.locked():
                # if the wakeup sequence is cancelled, stop the lightshow
                logging.info("wakeup sequence cancelled")
                self.off()
                return
