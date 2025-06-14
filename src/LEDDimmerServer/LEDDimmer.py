import argparse
import json
import logging
import os
from functools import partial
from http.server import HTTPServer

from LEDDimmerServer.DimmerBackend import DimmerBackend
from LEDDimmerServer.HTTPHandler import HTTPHandler
from LEDDimmerServer.utils import ROOT_DIR


class LEDDimmer:
    def __init__(self, config):
        super().__init__()
        self.config = config
        self.backend : DimmerBackend = DimmerBackend(config)
        self.http_handler = partial(HTTPHandler, self.backend)
        self.server = HTTPServer((config['host'], int(config['port'])), RequestHandlerClass=self.http_handler)

    def stop(self):
        self.server.shutdown()

    def run(self):
        logging.info("- start httpd")
        self.server.serve_forever(1)
    
    def shutdown(self):
        logging.info("- shutdown httpd")
        self.server.shutdown()
        self.server.server_close()
        logging.info("- httpd closed")



def parse_arguments(*args):
    argparser = argparse.ArgumentParser('LED SUNLIGHT TOOL')
    argparser.add_argument("--host", default="led.local")
    argparser.add_argument("--port", default=8080, type=int)
    argparser.add_argument("--virtual", default=False, action='store_true',
                           help="Run in virtual mode, no hardware access, only simulation")
    argparse_config = argparser.parse_args(*args)

    with open(os.path.join(ROOT_DIR, "config/config.json"), 'r', encoding="utf-8") as cfg_file:
        json_config = json.load(cfg_file)

    with open(os.path.join(ROOT_DIR, "config/presets.json"), 'r', encoding="utf-8") as cfg_file:
        active_profile = json.load(cfg_file)
        _key = json_config['sunrise_profile']
        #if 'profile' in json_config and json_config['profile'] in active_profile:
        #    _key = json_config['sunrise_profile']
        argparse_config.__dict__['active_profile'] = active_profile[_key]

    # fill in config from json if they are not give by argparse
    for k_j, v_j in json_config.items():
        if k_j not in argparse_config.__dict__:
            argparse_config.__dict__[k_j] = v_j

    return argparse_config.__dict__


