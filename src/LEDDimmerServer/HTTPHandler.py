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
from LEDDimmerServer.DimmerBackend import DimmerBackend

class HTTPHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.backend = None
    
    def set_backend(self, backend):
        from LEDDimmerServer.DimmerBackend import DimmerBackend
        self.backend : DimmerBackend = backend

    def do_PUT(self):
        logging.debug("-- PUT")
        length = int(self.headers["Content-Length"])
        path = self.translate_path(self.path)
        data_string = self.rfile.read(length)
        print(data_string)
        
        if self.backend is None:
            raise Exception("Backend not initialized!")

        if "/toggle" in self.path:
            self.backend.toggle()

        if "/on" in self.path:
            self.backend.on()
  
        if "/off" in path:
            self.backend.off()
                        
        if "/incr" in path:
            self.backend.incr()

        if "/decr" in path:
            self.backend.decr()
   
        if "/wakeuptime" in path:
            self.backend.wakeuptime(data_string)

        if "/sunrise" in path:
            self.backend.sunrise()
            
        if '/color' in path:
            self.backend.color(data_string)

        if '/gradient' in path:
            self.backend.gradient(data_string)

        if '/preset' in path:
            self.backend.preset(data_string)

        if '/default' in path:
            self.backend.default(data_string)
            
        if '/update' in path:
            self.backend.update()


