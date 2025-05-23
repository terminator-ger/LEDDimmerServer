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

class HTTPHandler(SimpleHTTPServer.SimpleHTTPRequestHandler):
    def __init__(self):
        self.br = 0
        self.wakeup_task = None 
        self.isInWakeupsequence = False
        GPIO.set_mode(PWM, pigpio.OUTPUT)
        GPIO.write(PWM, 0)
        logging.info("hardware initialized")
        self.utc = UTC()
        self.epoch = datetime.utcfromtimestamp(0)


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
        GPIO.write(PWM, 0)

    def enable_pwm(self):
        logging.info("enabling ports")
        GPIO.write(PWM, 1)

    def pwm_is_enabled(self):
        return (GPIO.read(PWM) == 1)

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
            if self.isInWakeupsequence == True:
                if self.wakeup_task is not None:
                    self.wakeup_task.cancel()
                    self.isInWakeupsequence = False
        else:
            self.br = 255
            self.enable_pwm()
            logging.debug(self.br)
        GPIO.set_PWM_dutycycle(PWM, self.br)
        
    def _put_on(self):
        logging.debug( "DEPRECATED --- ON")
        self.send_response(200,"ON_OK")
        self.send_response(200,"OFF_OK")
        self.send_header("Content-type","text/html")
        self.end_headers()
        self.br = 255
        logging.debug(self.br)
        self.enable_pwm()
        GPIO.set_PWM_dutycycle(PWM, self.br)

    def _put_off(self):
        logging.debug("DEPRECATED --- OFF")
        self.send_response(200,"OFF_OK")
        self.send_header("Content-type","text/html")
        self.end_headers()
        self.wfile.write("")
        self.br = 0
        self.disable_pwm()
        GPIO.set_PWM_dutycycle(PWM, self.br)
    
    def _put_incr(self):
        logging.debug("--- INCR")
        self.send_response(200,"INCR_OK")
        self.send_header("Content-type","text/html")
        self.end_headers()
        self.wfile.write("")
        self.br = min(self.br + 10, 255)
        GPIO.set_PWM_dutycycle(PWM, int(self.br))
        
    def _put_decr(self):
        logging.debug("--- DECR")
        self.send_response(200,"INCR_OK")
        self.send_header("Content-type","text/html")
        self.end_headers()
        self.wfile.write("")

        self.br = max(self.br - 10,0)
        logging.debug(self.br)
        GPIO.set_PWM_dutycycle(PWM, int(self.br))
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
           pass 



    def startIncrLight(self):
        logging.debug("starting up with the lightshow")
        self.enable_pwm()
        self.isInWakeupsequence = True
        val = 0         
        for t in range(0,59):
            val = int(255.0/59.0)*t
            logging.info(("setting light to " + str(val)))
            GPIO.set_PWM_dutycycle(PWM, val)
            time.sleep(30)