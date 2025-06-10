import signal
import json
import logging
from http.server import HTTPServer
from threading import Thread
import argparse

from LEDDimmerServer.utc import UTC
from LEDDimmerServer.HTTPHandler import HTTPHandler
import os
from pathlib import Path

ROOT_DIR = Path(os.path.abspath(__file__)).parent.parent.parent.absolute()

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

    with open(os.path.join(ROOT_DIR, "config/config.json"), 'r') as cfg_file:
        json_config = json.load(cfg_file)

    with open(os.path.join(ROOT_DIR, "config/presets.json"), 'r') as cfg_file:
        active_profile = json.load(cfg_file)
        _key = "default"
        if 'profile' in json_config and json_config['profile'] in active_profile:
            _key = json_config['sunrise_profile']
        active_profile[_key]

    # fill in config from json if they are not give by argparse
    for k_j, v_j in json_config.items():
        if k_j not in argparse_config.__dict__:
            argparse_config.__dict__[k_j] = v_j

    argparse_config.__dict__['sunrise_profile'] = active_profile
    return argparse_config.__dict__


def http_thread(config):
    try:
        from functools import partial
        HTTPHandlerConfigWrapper = partial(HTTPHandler, config)
        httpd = HTTPServer(server_address=(config['host'], config['port']), RequestHandlerClass=HTTPHandlerConfigWrapper)
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
