import simplejson
import time
import sys
import requests
import json
import logging
import time
from datetime import datetime, timedelta, timezone
from threading import Lock, Timer
from http.server import SimpleHTTPRequestHandler
from gpiozero import PWMLED, RGBLED
import pytz
import requests
import simplejson
import astral
from typing import Dict

from LEDDimmerServer.color import get_sunrise_color, get_sunrise_intensity, modify_json
from LEDDimmerServer.utc import UTC


class DimmerBackend:
    def __init__(self, config):
        self.on_off_w_pwm = 0.0
        self.wakeup_task = None 
        self.is_in_wakeup_sequence : Lock = Lock()
        self.check_config(config)
        self.config = config

        # PIN CONFIGURATION
        # @see http://abyz.me.uk/rpi/pigpio/index.html#Type_3
        if self.config['has_w']:
            self.GPIO_W_PWM = PWMLED(pin=self.config["GPIO_W_PWM"])
            self.on_off_w_pwm = 1.0
        
        if self.config["has_rgb"]:
            self.GPIO_RGB = RGBLED(red=self.config["GPIO_R"],
                                    green=self.config["GPIO_G"],
                                    blue=self.config["GPIO_B"],
                                    pwm=False)
            self.GPIO_RGB_PWM = PWMLED(pin=self.config['GPIO_RGB_PWM'])
            self.on_off_rgb = (0,0,0)
            self.on_off_rgb_pwm = 1.0
        
            
        logging.info("hardware initialized")
        self.utc = UTC()
        self.epoch = datetime.now(tz=timezone.utc).timestamp()
        self.http_handler = None
        
    def set_http_handler(self, handler):
        from LEDDimmerServer.HTTPHandler import HTTPHandler
        self.http_handler : HTTPHandler = handler

    def check_config(self, config: Dict) -> bool:
        # one condition has to be set
        assert config['has_w'] or config['has_rgb']

    def disable_pwm(self):
        logging.info("disabling ports")
        if self.config['has_w'] and self.GPIO_RGB_PWM.is_active:
            self.GPIO_RGB_PWM.off()
        if self.config['has_rgb'] and self.GPIO_W_PWM.is_active:
            self.GPIO_W_PWM.off()

    def enable_pwm(self):
        logging.info("enabling ports")
        if self.config['has_rgb'] and not self.GPIO_RGB_PWM.is_active:
            self.GPIO_RGB_PWM.on()
        if self.config['has_w'] and not self.GPIO_W_PWM.is_active:
            self.GPIO_W_PWM.on()


    def unix_time_ms(self, dt):
        return (dt-self.epoch).total_seconds() * 1000.0
   
    def toggle(self):
        logging.debug( "--- TOGGLE")
        if self.http_handler is not None:
            self.http_handler.send_response(200,"TOGGLE_OK")
            self.http_handler.send_header("Content-type","text/html")
            self.http_handler.end_headers()
            
        if self.config['has_w'] and self.GPIO_W_PWM.is_active or self.config['has_rgb'] and self.GPIO_RGB_PWM.is_active:
            self.disable_pwm()
            # disable wakeup if there is one active...
            if self.is_in_wakeup_sequence.locked():
                if self.wakeup_task is not None:
                    self.wakeup_task.cancel()
                    self.is_in_wakeup_sequence.release_lock()
        else:
            # light on
            self.enable_pwm()
            if self.config["has_w"]:
                logging.debug("set w: %s", self.on_off_w_pwm)
                self.GPIO_W_PWM.value = self.on_off_w_pwm

            if self.config["has_rgb"]:
                logging.debug("set r: %s", self.on_off_rgb)
                logging.debug("set r: %s", self.on_off_rgb_pwm)
                self.GPIO_RGB.value = self.on_off_rgb
                self.GPIO_RGB_PWM.value = self.on_off_rgb_pwm


    def on(self):
        if self.http_handler is not None:
            self.http_handler.send_response(200,"ON_OK")
            self.http_handler.send_response(200,"OFF_OK")
            self.http_handler.send_header("Content-type","text/html")
            self.http_handler.end_headers()

        self.enable_pwm()

        if self.config["has_w"]:
            logging.debug("set w: %s", self.on_off_w_pwm)
            self.GPIO_W_PWM.value = self.on_off_w_pwm

        if self.config["has_rgb"]:
            logging.debug("set rgb: %s", self.on_off_rgb)
            self.GPIO_RGB.value = self.on_off_rgb


    def off(self):
        if self.http_handler is not None:
            self.http_handler.send_response(200,"OFF_OK")
            self.http_handler.send_header("Content-type","text/html")
            self.http_handler.end_headers()
            self.http_handler.wfile.write("")
 
        if self.config["has_w"]:
            logging.debug("set w: %s", self.on_off_w_pwm)
            self.on_off_w_pwm = 0
            self.GPIO_W_PWM = self.on_off_w_pwm

        if self.config["has_rgb"]:
            logging.debug("set rgb: %s", self.on_off_rgb)
            self.on_off_rgb_pwm = 0
            self.GPIO_RGB.value = self.on_off_rgb
        
        self.disable_pwm()
   
    
    def incr(self):
        logging.debug("--- INCR")
        if self.http_handler is not None:
            self.http_handler.send_response(200,"INCR_OK")
            self.http_handler.send_header("Content-type","text/html")
            self.http_handler.end_headers()
            self.http_handler.wfile.write("")
            
        if self.config['has_w']:
            if self.on_off_w_pwm == 0:
                self.enable_pwm()
            self.on_off_w_pwm = min(self.on_off_w_pwm + 10, 255)
            self.GPIO_W_PWM.value = self.on_off_w_pwm

        if self.config['has_rgb']:
            if self.on_off_rgb_pwm == 0:
                self.enable_pwm()
            self.on_off_rgb_pwm = min(self.on_off_rgb_pwm + 10, 255)
            self.GPIO_RGB_PWM.value = self.on_off_w_pwm
                                                                                            
        
    def decr(self):
        logging.debug("--- DECR")
        if self.http_handler is not None:
            self.http_handler.send_response(200,"INCR_OK")
            self.http_handler.send_header("Content-type","text/html")
            self.http_handler.end_headers()
            self.http_handler.wfile.write("")

        self.on_off_w_pwm = max(self.on_off_w_pwm - 10,0)
        if self.config['has_w']:
            self.GPIO_W_PWM.value = self.on_off_w_pwm
            if self.on_off_w_pwm < 0:
                self.disable_pwm() 
    
        if self.config['has_rgb']:
            self.on_off_rgb_pwm = max(self.on_off_rgb - 10, 0)
            if self.on_off_rgb_pwm < 0:
                self.disable_pwm()
 
    def wakeuptime(self, data_string):
        logging.debug("--- New wakeup time: ")
        #parse json
        data = simplejson.loads(data_string)
        wakeup_time = data['time']
        wakeup_time = int(wakeup_time)
        now = int(time.time()*1000)
        t = int((wakeup_time-now)/1000)
        returntime = (str(int(wakeup_time)))

        logging.info("--- sheduling wakeup in ")
        logging.info("%d", int(wakeup_time))
        logging.debug("killing old wakeups")
        logging.debug("returntime: ")
        logging.debug("%s", returntime)
        
        if self.wakeup_task is not None:
            self.wakeup_task.cancel()
        self.wakeup_task = Timer(t - (self.config['active_profile']['wakeup_sequence_len'] * 60), self.startIncrLight)
        self.wakeup_task.start()
       
        if self.http_handler is not None:
            self.http_handler.send_response(200, 'WAKEUP_OK')
            self.http_handler.send_header("Content-type","text/html")
            self.http_handler.end_headers()
            self.http_handler.wfile.write(returntime) 
    
    def sunrise(self):
        logging.debug("--- Wakeup set to Sunrise ---")

        send_url = 'http://freegeoip.net/json'
        r = requests.get(send_url)
        j = json.loads(r.text)
        lat = float(j['latitude'])
        lon = float(j['longitude'])
        location = astral.Observer(lat, lon)
        tomorrow = datetime.today() + timedelta(days=1)
        local_tz = pytz.timezone(j['time_zone'])
 
        wakeup_time = astral.sun.dawn(location, date=tomorrow, tzinfo=local_tz)
        now = datetime.now(self.utc)

        t = wakeup_time - now
        logging.info("Wakeup at")
        logging.info("%s", wakeup_time)
        logging.debug("killing old wakeups")
        if self.wakeup_task is not None:
            self.wakeup_task.cancel()
        self.wakeup_task = Timer(t.total_seconds() - (self.config['active_profile']['wakeup_sequence_len']* 60), self.startIncrLight)
        self.wakeup_task.start()
               
        if self.http_handler is not None:
            self.http_handler.send_response(200, 'SUNRISE_OK')
            self.http_handler.send_header("Content-type","text/html")
            self.http_handler.end_headers()
            self.http_handler.wfile.write("%f"%wakeup_time) 


    def color(self, data_string):
        '''
            name [[rgb], [rgb], ...]
        '''
        key, values = data_string.split(" ")
        values = [f"#{x}" for x in values]
        modify_json(key, values, "colors.json") 
        

    def gradient(self, data_string):
        '''
            name [[rgb], [rgb], ...]
        '''
        key, values = data_string.split(" ")
        values = [float(x) for x in values]
        modify_json(key, values, "gradient.json") 
        

    def preset(self, data_string):
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
   
    
    def default(self, data_string):
        _, profile = data_string.split(" ")
        modify_json('profile', profile, 'config.json')
    
    def update(self):
        sys.exit(42) #quit with code for update


    def startIncrLight(self):
        logging.debug("starting up with the lightshow")
        self.enable_pwm()
        self.is_in_wakeup_sequence.acquire()
        pause = (self.config['active_profile']['wakeup_sequence_len'] * 60) / self.config['pwm_steps']

        for progress in range(0, self.config['pwm_steps']):
            p = progress / self.config['pwm_steps']
            lum = get_sunrise_intensity(p, self.config['active_profile']['grad_interpolation'], self.config['active_profile']['gradient'])
            logging.info("setting light to %s", str(lum))
            if self.config['has_w']:
                self.GPIO_W_PWM.value = lum
            if self.config['has_rgb']:
                self.GPIO_RGB_PWM.value = lum
                #r, g, b = get_sunrise_color(p, self.config.color_interpolation, self.config.color)
                #self.GPIO.set_PWM_dutycycle(self.config["GPIO_R"], r)
                #self.GPIO.set_PWM_dutycycle(self.config["GPIO_G"], g)
                #self.GPIO.set_PWM_dutycycle(self.config["GPIO_B"], b)

            time.sleep(pause)

