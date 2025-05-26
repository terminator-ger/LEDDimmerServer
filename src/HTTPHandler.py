import pigpio
import signal
import SocketServer
import simplejson
import time
import ephem
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
from src.color import get_sunrise_color, get_sunrise_intensity

class HTTPHandler(SimpleHTTPServer.SimpleHTTPRequestHandler):
    def __init__(self, config):
        self.br = 0
        self.wakeup_task = None 
        self.isInWakeupsequence = Lock()
        self.config = config
        #self.PWM = config.GPIO_PWM
        #self.

        # PIN CONFIGURATION
        # @see http://abyz.me.uk/rpi/pigpio/index.html#Type_3
        self.GPIO = pigpio.pi()
        self.GPIO.set_mode(self.config.GPIO_PWM, pigpio.OUTPUT)
        self.GPIO.write(self.config.GPIO_PWM, 0)
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
        if self.br > 0:
            self.br = 0
            self.disable_pwm()
            # disable wakeup if we are right in one...
            if self.isInWakeupsequence.locked():
                if self.wakeup_task is not None:
                    self.wakeup_task.cancel()
                    self.isInWakeupsequence.release_lock()
        else:
            self.br = 255
            self.enable_pwm()
            logging.debug(self.br)
        self.GPIO.set_PWM_dutycycle(PWM, self.br)

    @deprecated()
    def _put_on(self):
        logging.debug( "DEPRECATED --- ON")
        self.send_response(200,"ON_OK")
        self.send_response(200,"OFF_OK")
        self.send_header("Content-type","text/html")
        self.end_headers()
        self.br = 255
        logging.debug(self.br)
        self.enable_pwm()
        self.GPIO.set_PWM_dutycycle(PWM, self.br)

    @deprecated()
    def _put_off(self):
        logging.debug("DEPRECATED --- OFF")
        self.send_response(200,"OFF_OK")
        self.send_header("Content-type","text/html")
        self.end_headers()
        self.wfile.write("")
        self.br = 0
        self.disable_pwm()
        self.GPIO.set_PWM_dutycycle(PWM, self.br)
    
    def _put_incr(self):
        logging.debug("--- INCR")
        self.send_response(200,"INCR_OK")
        self.send_header("Content-type","text/html")
        self.end_headers()
        self.wfile.write("")
        self.br = min(self.br + 10, 255)
        self.GPIO.set_PWM_dutycycle(PWM, int(self.br))
        
    def _put_decr(self):
        logging.debug("--- DECR")
        self.send_response(200,"INCR_OK")
        self.send_header("Content-type","text/html")
        self.end_headers()
        self.wfile.write("")

        self.br = max(self.br - 10,0)
        logging.debug(self.br)
        self.GPIO.set_PWM_dutycycle(PWM, int(self.br))
        if self.br < 0:
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
        self.wakeup_task = Timer(t.total_seconds() - (LIGHT_START_BEFORE_ALARM_TIME * 60), self.startIncrLight)
        self.wakeup_task.start()
               
        self.wfile.write("%f"%wakeup_time) 
    
    def _put_color(self, data_string):
        '''
            name [[rgb], [rgb], ...]
        '''
        

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