import os
import json
import logging

import argparse

from LEDDimmerServer.HTTPHandler import HTTPHandler
from LEDDimmerServer.DimmerBackend import DimmerBackend
from LEDDimmerServer.utils import ROOT_DIR
from functools import partial



class LEDDimmer:
    def __init__(self, config):
        self.backend : DimmerBackend = DimmerBackend(config)
        self.http_handler = partial(HTTPHandler)
        self.http_handler.set_backend(self.backend)
        self.backend.set_http_handler(self.http_handler)

def parse_arguments():
    argparser = argparse.ArgumentParser('LED SUNLIGHT TOOL')
    argparser.add_argument("--host", default="led.local")
    argparser.add_argument("--port", default=8080, type=int)
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


