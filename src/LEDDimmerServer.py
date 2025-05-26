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
import sys
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
import argparse

from .config import GPIO, PWM
from .utc import UTC
from .HTTPHandler import HTTPHandler
##################
# Set up logging
##################

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

def parse_arguments():
    argparser = argparse.ArgumentParser('LED SUNLIGHT TOOL')
    argparser.add_argument("host", default=argparse.SUPPRESS)
    argparser.add_argument("port", default=argparse.SUPPRESS)
    argparse_config = argparser.parse_args()

    with open("config/config.json", 'r') as cfg_file:
        json_config = json.load(cfg_file)

    # fill in config from json if they are not give by argparse
    for k_j, v_j in json_config:
        if k_j not in argparse_config.__dict__:
            argparse_config.__dict__[k_j] = v_j
    return argparse_config


def http_thread(config):
    try:
        httpd = HTTPServer(config, HTTPHandler)
        logging.info("- start httpd")
        httpd.serve_forever()
    except Exception as e:
        logging.debug(e)

########################################################
# HTTP POST Server for Handling LED Widget commands    #
########################################################
if __name__=='__main__':
    config = parse_arguments()
        
    server = Thread(target=http_thread, args=config)
    server.daemon = True # Do not make us wait for you to exit
    server.start()
    signal.pause() # Wait for interrupt signal, e.g. KeyboardInterrupt
    server.shutdown()
