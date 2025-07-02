import logging
import sys
import time
from datetime import datetime, timedelta, timezone
from threading import Lock, Timer
from typing import Dict, Tuple

from astral import Observer, sun
import pytz
from gpiozero import PWMLED, RGBLED

from LEDDimmerServer.color import  modify_json, SunriseProgress
from LEDDimmerServer.utc import UTC
from LEDDimmerServer.utils import add_float_tuple


class DimmerBackend:
    def __init__(self, config):
        self.wakeup_task = None
        self.check_config(config)
        self.config = config
        

        # PIN CONFIGURATION
        # @see http://abyz.me.uk/rpi/pigpio/index.html#Type_3
        self.GPIO_RGB = None
        self.GPIO_W = None
        self.on_off_w_pwm = None
        self.on_off_rgb_pwm = None
        self.wakeup_type = None
        
        if self.config['has_w']:
            self.GPIO_W = PWMLED(pin=self.config["GPIO_W"], frequency=self.config['PWM_frequency_hz'])
            self.on_off_w_pwm = 1.0
            

        if self.config["has_rgb"]:
            self.GPIO_RGB = RGBLED(red=self.config["GPIO_R"],
                                   green=self.config["GPIO_G"],
                                   blue=self.config["GPIO_B"],
                                   pwm=True)
            self.on_off_rgb_pwm = (1.0, 1.0, 1.0)

        logging.info("hardware initialized")
        self.utc = UTC()
        self.epoch = datetime.now(tz=timezone.utc).timestamp()
        self.progress = SunriseProgress(config, self.GPIO_RGB, self.GPIO_W)
    
    def get_status(self) -> Dict:
        ''' Returns the status of the LED Dimmer Server
            :return: A dictionary containing the status of the LED Dimmer Server
        '''
        status = {
            'has_w': self.config['has_w'],
            'has_rgb': self.config['has_rgb'],
            'w_pwm': self.on_off_w_pwm,
            'rgb_pwm': self.on_off_rgb_pwm,
            'is_in_wakeup_sequence': self.progress.is_in_wakeup_sequence.locked(),
            'wakeup_task_alive': self.wakeup_task.is_alive() if self.wakeup_task else False,
            "wakeup_time": self.wakeuptime(0)[1] if self.wakeup_task else 0,
            "wakeup_type": self.wakeup_type,
        }
        print("--- STATUS ---")
        logging.info("status: %s", status)
        return status
    
    def get_config(self) -> Dict:
        ''' Returns the configuration of the LED Dimmer Server
            :return: A dictionary containing the configuration of the LED Dimmer Server
        '''
        config = {
            "active_profile": self.config['active_profile'],
            "latitude": self.config['latitude'],    
            "longitude": self.config['longitude'],
            "time_zone": self.config['time_zone'],  
            "colors": self.config['colors'],
            "gradient": self.config['gradient'],    
            "presets": self.config['presets'],
            "GPIO_W": self.config['GPIO_W'],
            "gpio_r": self.config['GPIO_R'],
            "gpio_g": self.config['GPIO_G'],
            "gpio_b": self.config['GPIO_B'],
        }
        return config

    def check_config(self, config: Dict) -> bool:
        ''' Check if the config is valid
            :param config: The configuration dictionary 
        '''
        # one condition has to be set
        assert config['has_w'] or config['has_rgb']



    def toggle(self) -> bool:
        ''' Toggles the light on or off'''
        logging.debug("--- TOGGLE")

        if (self.config['has_w'] and self.GPIO_W.is_active) \
            or (self.config['has_rgb'] and self.GPIO_RGB.is_active):

            self.off()
            return False
        
        else:
            self.on()
            return True

    def on(self) -> bool:
        ''' Turns the light on
            If the light is already on, it does nothing.    
        '''

        if self.config["has_w"]:
            #self.on_off_w_pwm = 1.0
            logging.debug("set w: %s", self.on_off_w_pwm)
            self.GPIO_W.on()
            self.GPIO_W.value = self.on_off_w_pwm

        if self.config["has_rgb"]:
            self.GPIO_RGB.on()
            self.GPIO_RGB.value = self.on_off_rgb_pwm
            
        return True

    def off(self) -> bool:
        ''' Turns the light off
            If the light is already off, it does nothing.
        '''
        # disable wakeup if there is one active...
        if (self.progress.wakeup_sequence_is_locked() and
            self.wakeup_task is not None):
                self.wakeup_task.cancel()
                self.progress.wakeup_sequence_release_lock()
                
        if self.config["has_w"]:
            logging.debug("set w: %s", self.on_off_w_pwm)
            self.GPIO_W.off()

        if self.config["has_rgb"]:
            logging.debug("set rgb: %s", self.on_off_rgb_pwm)
            self.GPIO_RGB.off()

        return True

    def incr(self) -> bool:
        ''' Increases the light intensity by 10%
            If the light is already at maximum intensity, it does nothing.  
        '''

        logging.debug("--- INCR")
        if self.config['has_w']:
            if not self.GPIO_W.is_active:
                logging.debug("W_PWM is not active, cannot incr")
                return False
            self.on_off_w_pwm = min(self.on_off_w_pwm + 0.1, 1.0)
            self.GPIO_W.value = self.on_off_w_pwm
            if self.GPIO_W.value > 0:
                self.GPIO_W.on()

        if self.config['has_rgb']:
            if not self.GPIO_RGB.is_active:
                logging.debug("W_PWM is not active, cannot incr")
                return False
            self.on_off_rgb_pwm = add_float_tuple(self.on_off_rgb_pwm, -0.1)
            self.GPIO_RGB.value = self.on_off_rgb_pwm
            if any([x > 0 for x in self.GPIO_RGB.value]):
                self.GPIO_RGB.on()
           
        return True
    
      

    def decr(self) -> bool:
        ''' Decreases the light intensity by 10%
            If the light is already at minimum intensity, it does nothing.
        '''
        logging.debug("--- DECR")
        if self.config['has_w']:
            if not self.GPIO_W.is_active:
                logging.debug("W_PWM is not active, cannot decr")
                return False
            self.on_off_w_pwm = max(self.on_off_w_pwm - 0.1, 0.0)
            self.GPIO_W.value = self.on_off_w_pwm
            if self.GPIO_W.value == 0:
                self.GPIO_W.off()


        if self.config['has_rgb']:
            if not self.GPIO_RGB.is_active:
                logging.debug("RGB_PWM is not active, cannot decr")
                return False
            self.on_off_rgb_pwm = add_float_tuple(self.on_off_rgb_pwm, - 0.10)
            self.GPIO_RGB.value = self.on_off_rgb_pwm
            if any([x == 0 for x in self.GPIO_RGB.value]):
                self.GPIO_RGB.off()

        return True

    def interrupt_wakeup(self) -> None:
        ''' Interrupts the wakeup sequence
            If there is no wakeup sequence running, it does nothing.
        '''
        logging.debug("--- INTERRUPT WAKEUP")
        if self.wakeup_task is not None and self.wakeup_task.is_alive():
            logging.debug("Cancelling wakeup task")
            self.wakeup_task.cancel()
            if self.progress.wakeup_sequence_is_locked():
                self.progress.wakeup_sequence_release_lock()
            self.wakeup_task.join()
            self.off()

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
        
        if self.progress.wakeup_sequence_is_locked():
            # disable wakeup if there is one active...
            self.interrupt_wakeup()
        
        if wakeup_time == 0:
            logging.info("Wakeup sequence disabled")
            return (True, 0)
        
        time_delta = t - (self.config['active_profile']['wakeup_sequence_len'] * 60)
        self.wakeup_task = Timer(time_delta, self.progress.run)
        self.wakeup_type = "alarm"
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
       
        if self.progress.wakeup_sequence_is_locked():
            # disable wakeup if there is one active...
            self.progress.wakeup_sequence_release_lock()
            self.off() 

        logging.info("Wakeup at")
        logging.info("%s", wakeup_time)
        time_delta = t.total_seconds() - (self.config['active_profile']['wakeup_sequence_len'] * 60)
        self.wakeup_task = Timer(time_delta, self.progress.run)
        self.wakeup_type = "sunrise"
        self.wakeup_task.start()
        return (True, int(wakeup_time.timestamp()))

    def color(self, dict: Dict) -> bool:
        '''
            name [[rgb], [rgb], ...]
        '''
        for key, values in dict.items():
            modify_json(key, values, "colors.json")
        return True

    def gradient(self, data: Dict) -> bool:
        '''
            name [[rgb], [rgb], ...]
        '''
        #key, values = data_string.split(" ")
        #values = [float(x) for x in values]
        for key, values in data.items():
            modify_json(key, values, "gradient.json")
        self.progress.reload(self.config)
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
        modify_json('profile', profile, 'config.json')
        return True

    def update(self) -> None:
        ''' Updates the LED Dimmer Server
            This will download the latest version from the repository and restart the server.
        '''
        sys.exit(42)  # quit with code for update

  