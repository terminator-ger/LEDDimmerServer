from LEDDimmerServer.LEDDimmer import LEDDimmer,  parse_arguments
from threading import Thread
import logging

def _setup_logging():
    '''Setup logger
    '''
    # set up logging to file - see previous section for more details
    logging.basicConfig(level=logging.DEBUG,
                        format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
                        datefmt='%d.%m.%y %H:%M:%S',
                        filename='/home/led/LEDDimmerServer/LEDDimmer.log',
                        filemode='w')
    # define a Handler which writes INFO messages or higher to the sys.stderr
    console = logging.StreamHandler()
    console.setLevel(logging.DEBUG)
    # add the handler to the root logger
    logging.getLogger('').addHandler(console)



########################################################
# HTTP POST Server for Handling LED Widget commands    #
########################################################
if __name__=='__main__':
    _setup_logging()
    args = parse_arguments()
    if args['virtual']:
        logging.warning("Running in virtual mode, no hardware access, only simulation")
        from gpiozero import Device
        from gpiozero.pins.mock import MockFactory, MockPWMPin
        Device.pin_factory = MockFactory(pin_class=MockPWMPin)
    
    srv = LEDDimmer(args)
    srv_thread = Thread(target=srv.run)
    srv_thread.daemon = True  # Do not make us wait for you to exit
    srv_thread.start() 
    srv_thread.join()
