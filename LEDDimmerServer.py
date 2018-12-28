import pigpio
import signal
import SimpleHTTPServer
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



# set up logging to file - see previous section for more details
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
                    datefmt='%d.%m.%y %H:%M:%S',
                    filename='LEDDImmer.log',
                    filemode='w')
# define a Handler which writes INFO messages or higher to the sys.stderr
console = logging.StreamHandler()
console.setLevel(logging.DEBUG)
# add the handler to the root logger
logging.getLogger('').addHandler(console)

# Now, we can log to the root logger, or any other logger. First the root...

ZERO = timedelta(0)
LIGHT_START_BEFORE_ALARM_TIME = 30





# PIN CONFIGURATION
PWM = 14 

GPIO = pigpio.pi()

# PIN INIT
GPIO.set_mode(PWM, pigpio.OUTPUT)

GPIO.write(PWM, 0)
logging.info("hardware initialized")



class UTC(tzinfo):
  def utcoffset(self, dt):
    return ZERO
  def tzname(self, dt):
    return "UTC"
  def dst(self, dt):
    return ZERO

utc = UTC()
epoch = datetime.utcfromtimestamp(0)

#http stuff
PORT = 8080
HOST = '192.168.1.20'
addr = (HOST,PORT)
#ResponseMessage = {
#               "OK": ResponseStatus(code=200, message="OK"),
#               "BAD_REQUEST": ResponseStatus(code=400, message="Bad request"),
#               "NOT_FOUND": ResponseStatus(code=404, message="Not found"),
#               "INTERNAL_SERVER_ERROR": ResponseStatus(code=500, message="Internal server error")}



class HTTPHandler(SimpleHTTPServer.SimpleHTTPRequestHandler):
    
    br = 0
    wakeup_task = None 
    isInWakeupsequence = False
    
    def disable_pwm(self):
	logging.info("disabling ports")
	GPIO.write(PWM, 0)

    def enable_pwm(self):
        logging.info("enabling ports")
	GPIO.write(PWM, 1)

    def pwm_is_enabled(self):
        return (GPIO.read(PWM) == 1)

    def unix_time_ms(dt):
        return (dt-epoch).total_seconds() * 1000.0

    def do_PUT(self):
	logging.debug("-- PUT")
        length = int(self.headers["Content-Length"])
        path = self.translate_path(self.path)
	data_string = self.rfile.read(length)
        print(data_string)
        if "/toggle" in self.path:
		logging.debug( "--- TOGGLE")
		self.send_response(200,"TOGGLE_OK")
	        self.send_header("Content-type","text/html")
                self.end_headers()
                if HTTPHandler.br > 0:
                    HTTPHandler.br = 0
		    self.disable_pwm()
                    # disable wakeup if we are right in one...
                    if self.isInWakeupsequence == True:
                        if HTTPHandler.wakeup_task is not None:
                            HTTPHandler.wakeup_task.cancel()
                            self.isInWakeupsequence = False
                else:
                    HTTPHandler.br = 255
                    self.enable_pwm()
	            logging.debug(HTTPHandler.br)
		GPIO.set_PWM_dutycycle(PWM, HTTPHandler.br)

	if "/on" in self.path:
		logging.debug( "DEPRECATED --- ON")
		self.send_response(200,"ON_OK")
  		self.send_response(200,"OFF_OK")
	        self.send_header("Content-type","text/html")
                self.end_headers()
		HTTPHandler.br = 255
		logging.debug(HTTPHandler.br)
		self.enable_pwm()
		GPIO.set_PWM_dutycycle(PWM, HTTPHandler.br)
	if "/off" in path:
    		logging.debug("DEPRECATED --- OFF")
		self.send_response(200,"OFF_OK")
	        self.send_header("Content-type","text/html")
                self.end_headers()
                self.wfile.write("")
        	HTTPHandler.br = 0
		self.disable_pwm()
		GPIO.set_PWM_dutycycle(PWM, HTTPHandler.br)
                    
	if "/incr" in path:
		logging.debug("--- INCR")
		self.send_response(200,"INCR_OK")
                self.send_header("Content-type","text/html")
                self.end_headers()
                self.wfile.write("")
                HTTPHandler.br = min(HTTPHandler.br + 10, 255)
		GPIO.set_PWM_dutycycle(PWM, int(HTTPHandler.br))
#                if HTTPHandler.br > 5 and not self.pwm_is_enabled:
#			self.enable_pwm()
	if "/decr" in path:
		logging.debug("--- DECR")
                self.send_response(200,"INCR_OK")
                self.send_header("Content-type","text/html")
                self.end_headers()
                self.wfile.write("")

		HTTPHandler.br = max(HTTPHandler.br - 10,0)
		logging.debug(HTTPHandler.br)
		GPIO.set_PWM_dutycycle(PWM, int(HTTPHandler.br))
		if HTTPHandler.br < 0:
			self.disable_pwm()
	if "/wakeuptime" in path:
		logging.debug("--- New wakeup time: ")
		#parse json
		data = simplejson.loads(data_string)
		wakeup_time = data['time']
		wakeup_time = int(wakeup_time)
                #wakeup_time = parser.parse(wakeup_time
                print(datetime.now(utc))
                print(int(wakeup_time))
		now = int(time.time()*1000)
                #dt = datetime.today()  # Get timezone naive now
                #now = int(dt.timestamp())    
                #now = (datetime.now())
                    #-datetime.fromtimestamp(0)).total_seconds()
                #datetime(1970,1,1)).total_seconds()
		print(int(now))
                logging.info("--- sheduling wakeup in ")

                t = int((wakeup_time-now)/1000)
                print(t)
                logging.info(int(wakeup_time))
                logging.debug("killing old wakeups")
                if HTTPHandler.wakeup_task is not None:
                    HTTPHandler.wakeup_task.cancel()
     		HTTPHandler.wakeup_task = Timer(t - (LIGHT_START_BEFORE_ALARM_TIME * 60), self.startIncrLight)
                HTTPHandler.wakeup_task.start()
                self.send_response(200, 'WAKEUP_OK')
                self.send_header("Content-type","text/html")
                self.end_headers()
                returntime = (str(int(wakeup_time)))
                print("returntime: ")
                print(returntime)
                self.wfile.write(returntime)

        if "/sunrise" in path:
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

		now = datetime.now(utc)
                t = wakeup_time - now
                logging.info("Wakeup at")
                logging.info(wakeup_time)
                logging.debug("killing old wakeups")
                if HTTPHandler.wakeup_task is not None:
                    HTTPHandler.wakeup_task.cancel()
     		HTTPHandler.wakeup_task = Timer(t.total_seconds() - (LIGHT_START_BEFORE_ALARM_TIME * 60), self.startIncrLight)
                HTTPHandler.wakeup_task.start()
               
                self.wfile.write("%f"%wakeup_time)



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

def http_thread(addr):
    try:
	httpd = HTTPServer(addr, HTTPHandler)
	logging.info("- start httpd")
        httpd.serve_forever()
    except Exception as e:
        logging.debug(e)

########################################################
# HTTP POST Server for Handling LED Widget commands    #
########################################################
if __name__=='__main__':
    server = Thread(target=http_thread, args=[addr])
    server.daemon = True # Do not make us wait for you to exit
    server.start()
    signal.pause() # Wait for interrupt signal, e.g. KeyboardInterrupt
    server.shutdown()
