import argparse
import json
import logging
import os
from functools import partial
from http.server import HTTPServer

from LEDDimmerServer.DimmerBackend import DimmerBackend
from LEDDimmerServer.HTTPHandler import HTTPHandler
from LEDDimmerServer.utils import  get_ssl_context
import subprocess
from pathlib import Path
from importlib.resources import files


class LEDDimmer:
    def __init__(self, config):
        super().__init__()
        self.config = config
        self.backend : DimmerBackend = DimmerBackend(config)
        self.http_handler = partial(HTTPHandler, self.backend)
        self.httpd = HTTPServer((config['host'], int(config['port'])), RequestHandlerClass=self.http_handler)
        if config['use_ssl']:
            logging.info("- SSL enabled")
            self._ssl_init()
    
   
    def _ssl_init(self):
        """Initialize SSL for the HTTP server."""   
        logging.info("- init ssl")
        os.makedirs(os.path.join(Path.home(), ".ssh"), exist_ok=True)
        ssl_key_file = os.environ.get('LED_SSL_PRIVATE_KEY')
        if not ssl_key_file:
            logging.warning("SSL private key file not set in environment variable LED_SSL_PRIVATE_KEY ")
            ssl_key_file = os.path.join(Path.home(), ".ssh/led_key.pem")
        ssl_cert_file = ssl_key_file.replace("led_key.pem", "led_cert.pem") 
        
        if not os.path.exists(ssl_key_file):
            logging.error("SSL private key file %s does not exist - generating a new one.", ssl_key_file)
            subprocess.run(
                ["openssl",
                 "req",
                 "-x509",
                 "-newkey",
                 "rsa:4096",
                 "-sha256",
                 "-days",
                 "36500",
                 "-nodes",
                 "-keyout",
                 ssl_key_file,
                 "-out", 
                 ssl_cert_file,
                 "-subj",
                 "/CN=led.local",
                "-addext",
                "subjectAltName=DNS:led.local,DNS:*.led.local"
            ])
        context = get_ssl_context(ssl_cert_file, ssl_key_file)
        self.httpd.socket = context.wrap_socket(self.httpd.socket, server_side=True)
    
    def stop(self):
        self.httpd.shutdown()

    def run(self):
        logging.info("- start httpd")
        logging.info("- host: %s", self.config['host'])
        logging.info("- port: %d", self.config['port'])
        self.httpd.serve_forever(1)
    
    def shutdown(self):
        logging.info("- shutdown httpd")
        self.httpd.shutdown()
        self.httpd.server_close()
        logging.info("- httpd closed")



def parse_arguments(*args):
    argparser = argparse.ArgumentParser('LED SUNLIGHT TOOL')
    argparser.add_argument("--host", default="led.local")
    argparser.add_argument("--port", default=8080, type=int)
    argparser.add_argument("--virtual", default=False, action='store_true',
                           help="Run in virtual mode, no hardware access, only simulation")
    argparse_config = argparser.parse_args(*args)

    json_config = files("config").joinpath("config.json")
    with json_config.open() as cfg_file:
        json_config = json.load(cfg_file)

    presets_config = files("config").joinpath("presets.json")
    with presets_config.open() as cfg_file:
        active_profile = json.load(cfg_file)
        _key = json_config['sunrise_profile']
        argparse_config.__dict__['active_profile'] = active_profile[_key]

    # fill in config from json if they are not give by argparse
    for k_j, v_j in json_config.items():
        if k_j not in argparse_config.__dict__:
            argparse_config.__dict__[k_j] = v_j

    return argparse_config.__dict__


