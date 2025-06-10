import pigpio
import signal
import SocketServer
import simplejson
import time
import os
import ephem
import sys
import requests
import json
import ephem
import subprocess
import pytz
import logging
import math
from datetime import datetime
from astral import Astral,Location
from BaseHTTPServer import HTTPServer, BaseHTTPRequestHandler
from threading import Thread
from threading import Timer
from datetime import datetime
from dateutil import parser
from datetime import tzinfo, timedelta, datetime
from collections import namedtuple 

from src.config import GPIO, PWM, LIGHT_START_BEFORE_ALARM_TIME
from src.utc import UTC
from warnings import deprecated
import pigpio
from threading import Lock
from src.color import get_sunrise_color, get_sunrise_intensity, modify_json

class HTTPHandler(SimpleHTTPServer.SimpleHTTPRequestHandler):
    def __init__(self, config):
        self.w_intensity = 0
        self.wakeup_task = None 
        self.isInWakeupsequence = Lock()
        self.config = config
        #self.PWM = config.GPIO_PWM
        #self.

        # PIN CONFIGURATION
        # @see http://abyz.me.uk/rpi/pigpio/index.html#Type_3
        self.GPIO = pigpio.pi()
        if self.config.is_w or self.config.is_rgbw:
            self.GPIO.set_mode(self.config.GPIO_PWM, pigpio.OUTPUT)
            self.GPIO.write(self.config.GPIO_PWM, 0)
        
        if self.config.is_rgbw or self.config.is_rgb:
            self.GPIO.set_mode(self.config.GPIO_R, pigpio.OUTPUT)
            self.GPIO.set_mode(self.config.GPIO_G, pigpio.OUTPUT)
            self.GPIO.set_mode(self.config.GPIO_B, pigpio.OUTPUT)
            self.GPIO.write(self.config.GPIO_R, 0)
            self.GPIO.write(self.config.GPIO_G, 0)
            self.GPIO.write(self.config.GPIO_B, 0)
            
        logging.info("hardware initialized")
        self.utc = UTC()
        self.epoch = datetime.fromtimestamp(datetime.timezone.utc)

        #self.grad_curve = config.gradient
        #self.grad_interpolation = config.gradient_interpolation
        #self.color = config.color
        #self.color_interpolation = config.color_interpolation
        #self.wakeup_sequence_len = config.wakeup_sequence_len
        #self.pwm_steps = config.pwm_steps

    '''
    self contains the servers logic. As it subclasses
    SimpleHTTPServer all incoming REST-Messages are passed to the
    corresponding functions. We just need PUT.
    Message definition:
    PUT /incr
    PUT /decr
    PUT /toggle
    PUT /sunrise
    PUT /wakeuptime [utc-time-in-ms]
    PUT /color [name] [rgb, rgb, ...]
    PUT /gradient [name] [float, float, ...]
    '''
   
    def disable_pwm(self):
        logging.info("disabling ports")
        self.GPIO.write(PWM, 0)

    def enable_pwm(self):
        logging.info("enabling ports")
        self.GPIO.write(PWM, 1)

    def pwm_is_enabled(self):
        return (self.GPIO.read(PWM) == 1)

    def unix_time_ms(self, dt):
        return (dt-self.epoch).total_seconds() * 1000.0
   
    def _put_toggle(self):
        logging.debug( "--- TOGGLE")
        self.send_response(200,"TOGGLE_OK")
        self.send_header("Content-type","text/html")
        self.end_headers()
        if self.w_intensity > 0 or any([self.r_intensity > 0, self.g_intensity > 0, self.b_intensity > 0]):
            # light off
            if self.config.is_w or self.config.is_rgbw:
                modify_json("on_off_w", self.on_off_w, "config/config.json")
            if self.config.is_rgbw or self.config.rgb:
                modify_json("on_off_r", self.on_off_r, "config/config.json")
                modify_json("on_off_g", self.on_off_g, "config/config.json")
                modify_json("on_off_b", self.on_off_b, "config/config.json")

            self.disable_pwm()
            # disable wakeup if there is one active...
            if self.isInWakeupsequence.locked():
                if self.wakeup_task is not None:
                    self.wakeup_task.cancel()
                    self.isInWakeupsequence.release_lock()
        else:
            # light on - load from flash
            self.enable_pwm()
            if self.config.is_w or self.config.is_rgbw:
                self.w_intensity = self.config.on_off_w
                logging.debug(f"set w: {self.w_intensity}")
                self.GPIO.set_PWM_dutycycle(PWM, self.w_intensity)
            if self.config.is_rgbw or self.config.rgb:
                self.r_intensity = self.config.on_off_r
                self.g_intensity = self.config.on_off_g
                self.b_intensity = self.config.on_off_b
                logging.debug(f"set r: {self.r_intensity}")
                logging.debug(f"set g: {self.g_intensity}")
                logging.debug(f"set b: {self.b_intensity}")
                self.GPIO.set_PWM_dutycycle(PWM, self.r_intensity)
                self.GPIO.set_PWM_dutycycle(PWM, self.g_intensity)
                self.GPIO.set_PWM_dutycycle(PWM, self.b_intensity)


    @deprecated()
    def _put_on(self):
        logging.debug( "DEPRECATED --- ON")
        self.send_response(200,"ON_OK")
        self.send_response(200,"OFF_OK")
        self.send_header("Content-type","text/html")
        self.end_headers()

        self.enable_pwm()
        self.GPIO.set_PWM_dutycycle(PWM, self.w_intensity)

        if self.config.is_w or self.config.is_rgbw:
            self.w_intensity = self.config.on_off_w
            logging.debug(f"set w: {self.w_intensity}")
            self.GPIO.set_PWM_dutycycle(PWM, self.w_intensity)
        if self.config.is_rgbw or self.config.rgb:
            self.r_intensity = self.config.on_off_r
            self.g_intensity = self.config.on_off_g
            self.b_intensity = self.config.on_off_b
            logging.debug(f"set r: {self.r_intensity}")
            logging.debug(f"set g: {self.g_intensity}")
            logging.debug(f"set b: {self.b_intensity}")
            self.GPIO.set_PWM_dutycycle(PWM, self.r_intensity)
            self.GPIO.set_PWM_dutycycle(PWM, self.g_intensity)
            self.GPIO.set_PWM_dutycycle(PWM, self.b_intensity)

    @deprecated()
    def _put_off(self):
        logging.debug("DEPRECATED --- OFF")
        self.send_response(200,"OFF_OK")
        self.send_header("Content-type","text/html")
        self.end_headers()
        self.wfile.write("")
        self.w_intensity = 0
        self.disable_pwm()
        self.GPIO.set_PWM_dutycycle(PWM, self.w_intensity)
    
    def _put_incr(self):
        logging.debug("--- INCR")
        self.send_response(200,"INCR_OK")
        self.send_header("Content-type","text/html")
        self.end_headers()
        self.wfile.write("")
        self.w_intensity = min(self.w_intensity + 10, 255)
        self.GPIO.set_PWM_dutycycle(PWM, int(self.w_intensity))
        
    def _put_decr(self):
        logging.debug("--- DECR")
        self.send_response(200,"INCR_OK")
        self.send_header("Content-type","text/html")
        self.end_headers()
        self.wfile.write("")

        self.w_intensity = max(self.w_intensity - 10,0)
        logging.debug(self.w_intensity)
        self.GPIO.set_PWM_dutycycle(PWM, int(self.w_intensity))
        if self.w_intensity < 0:
            self.disable_pwm() 
    
    def _put_wakeuptime(self, data_string):
        logging.debug("--- New wakeup time: ")
        #parse json
        data = simplejson.loads(data_string)
        wakeup_time = data['time']
        wakeup_time = int(wakeup_time)
        print(datetime.now(self.utc))
        print(int(wakeup_time))
        now = int(time.time()*1000)

        print(int(now))
        logging.info("--- sheduling wakeup in ")

        t = int((wakeup_time-now)/1000)
        print(t)
        logging.info(int(wakeup_time))
        logging.debug("killing old wakeups")
        if self.wakeup_task is not None:
            self.wakeup_task.cancel()
        self.wakeup_task = Timer(t - (LIGHT_START_BEFORE_ALARM_TIME * 60), self.startIncrLight)
        self.wakeup_task.start()
        self.send_response(200, 'WAKEUP_OK')
        self.send_header("Content-type","text/html")
        self.end_headers()
        returntime = (str(int(wakeup_time)))
        print("returntime: ")
        print(returntime)
        self.wfile.write(returntime) 
    
    def _put_sunrise(self):
        logging.debug("--- Wakeup set to Sunrise ---")
        self.send_response(200, 'SUNRISE_OK')
        self.send_header("Content-type","text/html")
        self.end_headers()
 
        send_url = 'http://freegeoip.net/json'
        r = requests.get(send_url)
        j = json.loads(r.text)
        lat = j['latitude']
        lon = j['longitude']

        a = Astral()
        a.solar_depression = 'civil'

        l = Location()
        l.name = 'name'
        l.region = 'region'
        l.latitude = lat
        l.longitude = lon
        l.timezone = j['time_zone']
        #TODO:
        l.elevation = 200
        l.sun()
                
        tomorrow = datetime.today() + timedelta(days=1)
        sun = l.sun(date=tomorrow, local=True)
        local_tz = pytz.timezone(j['time_zone'])
                
        wakeup_time = sun['sunrise']

        now = datetime.now(self.utc)
        t = wakeup_time - now
        logging.info("Wakeup at")
        logging.info(wakeup_time)
        logging.debug("killing old wakeups")
        if self.wakeup_task is not None:
            self.wakeup_task.cancel()
        self.wakeup_task = Timer(t.total_seconds() - (self.config.active_profile.wakeup_sequence_len * 60), self.startIncrLight)
        self.wakeup_task.start()
               
        self.wfile.write("%f"%wakeup_time) 


    def _put_color(self, data_string):
        '''
            name [[rgb], [rgb], ...]
        '''
        key, values = data_string.split(" ")
        values = [f"#{x}" for x in values]
        modify_json(key, values, "colors.json") 
        

    def _put_gradient(self, data_string):
        '''
            name [[rgb], [rgb], ...]
        '''
        key, values = data_string.split(" ")
        values = [float(x) for x in values]
        modify_json(key, values, "gradient.json") 
        

    def _put_preset(self, data_string):
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
   
    
    def _put_default(self, data_string):
        _, profile = data_string.split(" ")
        modify_json('profile', profile, 'config.json')
    
    def _update(self):
        os.spawnl(os.P_DETACH, f'/bin/bash {}/sunrisr_update.sh')
        sys.exit(0)
        

    def do_PUT(self):
        logging.debug("-- PUT")
        length = int(self.headers["Content-Length"])
        path = self.translate_path(self.path)
        data_string = self.rfile.read(length)
        print(data_string)

        if "/toggle" in self.path:
            self._put_toggle()

        if "/on" in self.path:
            self._put_on()
  
        if "/off" in path:
            self._put_off()
                        
        if "/incr" in path:
            self._put_incr()

        if "/decr" in path:
            self._put_decr
   
        if "/wakeuptime" in path:
            self._put_wakeuptime(data_string)

        if "/sunrise" in path:
            self._put_sunrise()
            
        if '/color' in path:
            self._put_color(data_string)

        if '/gradient' in path:
            self._put_gradient(data_string)

        if '/preset' in path:
            self._put_preset(data_string)

        if '/default' in path:
            self._put_default(data_string)
            
        if '/update' in path:
            self._update()


    def startIncrLight(self):
        logging.debug("starting up with the lightshow")
        self.enable_pwm()
        self.isInWakeupsequence.acquire_lock()
        pause = (self.config.wakeup_sequence_len * 60) / self.config.pwm_steps

        for progress in range(0, self.config.pwd_steps):
            p = progress / self.pwm_steps
            lum = get_sunrise_intensity(p, self.config.grad_interpolation, self.config.gradient)
            logging.info(("setting light to " + str(lum)))
            self.GPIO.set_PWM_dutycycle(self.config.GPIO_PWM, lum)

            if self.color:
                r, g, b = get_sunrise_color(p, self.config.color_interpolation, self.config.color)
                self.GPIO.set_PWM_dutycycle(self.config.GPIO_R, r)
                self.GPIO.set_PWM_dutycycle(self.config.GPIO_G, g)
                self.GPIO.set_PWM_dutycycle(self.config.GPIO_B, b)

            time.sleep(pause)