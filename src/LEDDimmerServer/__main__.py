import signal
from LEDDimmerServer.LEDDimmer import LEDDimmer, parse_arguments
from http.server import HTTPServer
from threading import Thread
import logging
from typing import Dict

def _setup_logging():
    '''Setup logger
    '''
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



def http_thread(config: Dict):
    led_server = LEDDimmer(config)
    #backend = DimmerBackend(config)
    #HTTPHandlerConfigWrapper = partial(HTTPHandler, backend)
    httpd = HTTPServer(server_address=(config['host'], config['port']), RequestHandlerClass=led_server.http_handler)
    logging.info("- start httpd")
    httpd.serve_forever()

########################################################
# HTTP POST Server for Handling LED Widget commands    #
########################################################
if __name__=='__main__':
    _setup_logging()
    server = Thread(target=http_thread, args=(parse_arguments(),))
    server.daemon = True # Do not make us wait for you to exit
    server.start()
    signal.wait(server)  # Wait for the server thread to finish
    #signal.pause() # Wait for interrupt signal, e.g. KeyboardInterrupt
