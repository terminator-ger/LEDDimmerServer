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


class HTTPHandler(SimpleHTTPRequestHandler):
    def __init__(self, config, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.on_off_w_pwm = 0
        self.wakeup_task = None 
        self.isInWakeupsequence = Lock()
        self.check_config(config)
        self.config = config

        # PIN CONFIGURATION
        # @see http://abyz.me.uk/rpi/pigpio/index.html#Type_3
        if self.config['has_w']:
            self.GPIO_W_PWM = PWMLED(pin=self.config["GPIO_W_PWM"])
            self.on_off_w_pwm = 255
        
        if self.config["has_rgb"]:
            self.GPIO_RGB = RGBLED(red=self.config["GPIO_R"],
                                    green=self.config["GPIO_G"],
                                    blue=self.config["GPIO_B"],
                                    pwm=False)
            self.GPIO_RGB_PWM = PWMLED(pin=self.config['GPIO_RGB_PWM'])
            self.on_off_rgb = (0,0,0)
            self.on_off_rgb_pwm = 255
        
            
        logging.info("hardware initialized")
        self.utc = UTC()
        self.epoch = datetime.now(tz=timezone.utc).timestamp()

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
    def check_config(self, config: Dict) -> bool:
        # one condition has to be set
        assert config['has_w'] or config['has_rgb']

    def disable_pwm(self):
        logging.info("disabling ports")
        if self.config['has_w'] and self.GPIO_RGB_PWM.is_active():
            self.GPIO_RGB_PWM.off()
        if self.config['has_rgb'] and self.GPIO_W_PWM.is_active():
            self.GPIO_W_PWM.off()

    def enable_pwm(self):
        logging.info("enabling ports")
        if self.config['has_rgb'] and not self.GPIO_RGB_PWM.is_active():
            self.GPIO_RGB_PWM.on()
        if self.config['has_w'] and not self.GPIO_W_PWM.is_active():
            self.GPIO_W_PWM.on()


    def unix_time_ms(self, dt):
        return (dt-self.epoch).total_seconds() * 1000.0
   
    def _put_toggle(self):
        logging.debug( "--- TOGGLE")
        self.send_response(200,"TOGGLE_OK")
        self.send_header("Content-type","text/html")
        self.end_headers()
        if self.GPIO_W_PWM.is_active() or self.GPIO_RGB_PWM.is_active():
            # light off 
            self.disable_pwm()
            # disable wakeup if there is one active...
            if self.isInWakeupsequence.locked():
                if self.wakeup_task is not None:
                    self.wakeup_task.cancel()
                    self.isInWakeupsequence.release_lock()
        else:
            # light on
            self.enable_pwm()
            if self.config["has_w"]:
                logging.debug(f"set w: {self.on_off_w_pwm}")
                self.GPIO_W_PWM = self.on_off_w_pwm

            if self.config["has_rgb"]:
                logging.debug(f"set r: {self.on_off_rgb}")
                logging.debug(f"set r: {self.on_off_rgb_pwm}")
                self.GPIO_RGB.value = self.on_off_rgb
                self.GPIO_RGB_PWM.value = self.on_off_rgb_pwm


    def _put_on(self):
        self.send_response(200,"ON_OK")
        self.send_response(200,"OFF_OK")
        self.send_header("Content-type","text/html")
        self.end_headers()

        self.enable_pwm()

        if self.config["has_w"]:
            logging.debug(f"set w: {self.on_off_w_pwm}")
            self.GPIO_W_PWM = self.on_off_w_pwm

        if self.config["has_rgb"]:
            logging.debug(f"set rgb: {self.on_off_rgb}")
            self.GPIO_RGB.value = self.on_off_rgb


    def _put_off(self):
        self.send_response(200,"OFF_OK")
        self.send_header("Content-type","text/html")
        self.end_headers()
        self.wfile.write("")
 
        if self.config["has_w"]:
            logging.debug(f"set w: {self.on_off_w_pwm}")
            self.on_off_w_pwm = 0
            self.GPIO_W_PWM = self.on_off_w_pwm

        if self.config["has_rgb"]:
            logging.debug(f"set rgb: {self.on_off_rgb}")
            self.on_off_rgb_pwm = 0
            self.GPIO_RGB.value = self.on_off_rgb
        
        self.disable_pwm()
   
    
    def _put_incr(self):
        logging.debug("--- INCR")
        self.send_response(200,"INCR_OK")
        self.send_header("Content-type","text/html")
        self.end_headers()
        self.wfile.write("")
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
                                                                                            
        
    def _put_decr(self):
        logging.debug("--- DECR")
        self.send_response(200,"INCR_OK")
        self.send_header("Content-type","text/html")
        self.end_headers()
        self.wfile.write("")

        self.on_off_w_pwm = max(self.on_off_w_pwm - 10,0)
        if self.config['has_w']:
            self.GPIO_W_PWM = self.on_off_w_pwm
            if self.on_off_w_pwm < 0:
                self.disable_pwm() 
    
        if self.config['has_rgb']:
            self.on_off_rgb_pwm = max(self.on_off_rgb - 10, 0)
            if self.on_off_rgb_pwm < 0:
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
        self.wakeup_task = Timer(t - (self.config['active_profile']['wakeup_sequence_len'] * 60), self.startIncrLight)
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
        lat = float(j['latitude'])
        lon = float(j['longitude'])
        location = astral.Observer(lat, lon)
        tomorrow = datetime.today() + timedelta(days=1)
        local_tz = pytz.timezone(j['time_zone'])
 
        wakeup_time = astral.sun.dawn(location, date=tomorrow, tzinfo=local_tz)
        now = datetime.now(self.utc)

        t = wakeup_time - now
        logging.info("Wakeup at")
        logging.info(wakeup_time)
        logging.debug("killing old wakeups")
        if self.wakeup_task is not None:
            self.wakeup_task.cancel()
        self.wakeup_task = Timer(t.total_seconds() - (self.config['active_profile']['wakeup_sequence_len']* 60), self.startIncrLight)
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
        sys.exit(42) #quit with code for update
        

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
        pause = (self.config['active_profile']['wakeup_sequence_len'] * 60) / self.config['pwm_steps']

        for progress in range(0, self.config['pwd_steps']):
            p = progress / self.pwm_steps
            lum = get_sunrise_intensity(p, self.config['active_profile']['grad_interpolation'], self.config['active_profile']['gradient'])
            logging.info(("setting light to " + str(lum)))
            if self.config['has_w']:
                self.GPIO_W_PWM.value = lum
            if self.config['has_rgb']:
                self.GPIO_RGB_PWM.value = lum
                #r, g, b = get_sunrise_color(p, self.config.color_interpolation, self.config.color)
                #self.GPIO.set_PWM_dutycycle(self.config["GPIO_R"], r)
                #self.GPIO.set_PWM_dutycycle(self.config["GPIO_G"], g)
                #self.GPIO.set_PWM_dutycycle(self.config["GPIO_B"], b)

            time.sleep(pause)

