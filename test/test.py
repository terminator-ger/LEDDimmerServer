from functools import partial
import unittest
from LEDDimmerServer.LEDDimmer import HTTPHandler, parse_arguments
from http.server import HTTPServer
import time
import sys
from LEDDimmerServer.__main__ import http_thread
from LEDDimmerServer.DimmerBackend import DimmerBackend
from threading import Thread

class LEDDimmerServerTest(unittest.TestCase):
    def setUp(self):
        from gpiozero import Device
        from gpiozero.pins.mock import MockFactory, MockPWMPin
        Device.pin_factory = MockFactory(pin_class=MockPWMPin)
        return super().setUp()
    
    def test_setup_with_config(self):
        try:
            old_sys_argv = sys.argv
            sys.argv = [old_sys_argv[0]] + ["--host", "127.0.0.1", "--port", "8080"]
            config = parse_arguments()
            server = Thread(target=http_thread, args=config)
            server.daemon = True # Do not make us wait for you to exit
            server.start()
            time.sleep(1)
            server.join()
            assert True
        except Exception:
            assert False

    def test_toggle_rgb(self):
        sys.argv=[]
        config = parse_arguments()
        config["has_rgb"] = True
        config["has_w"] = False
        backend = DimmerBackend(config)
        backend.toggle()
        assert backend.GPIO_RGB_PWM.is_active == True
 
class ColorConversionTest(unittest.TestCase):
    _table = [
        #["#FFFFFF",  	1	 ,   1	 ,   1		    ,None   ,0	    ,1    ],
        #["#808080",  	0.5	 ,   0.5 ,   0.5	   	,None   ,0	    ,0.5  ],
        #["#000000",  	0	 ,   0	 ,   0		    ,None   ,0	    ,0    ],
        ["#FF0000",  	1	 ,   0	 ,   0		    ,0.0    ,1	    ,0.333],
        ["#BFBF00",  	0.75 ,   0.75,	0		    ,60.0   ,1	    ,0.5  ],
        ["#008000",  	0	 ,   0.5 ,   0		    ,120.0 	,1	    ,0.167],
        ["#80FFFF",  	0.5	 ,   1	 ,   1		    ,180.0 	,0.4	,0.833],
        ["#8080FF",  	0.5	 ,   0.5 ,   1		    ,240.0 	,0.25	,0.667],
        ["#BF40BF",  	0.75 ,   0.25,	0.75		,300.0 	,0.571	,0.583],
        ["#A0A424",  	0.628,	0.643,	0.142		,61.5   ,0.699	,0.471],
        ["#411BEA",  	0.255,	0.104,	0.918		,250.0 	,0.756	,0.426],
        ["#1EAC41",  	0.116,	0.675,	0.255		,133.8 	,0.667	,0.349],
        ["#F0C80E",  	0.941,	0.785,	0.053		,50.5   ,0.911	,0.593],
        ["#B430E5",  	0.704,	0.187,	0.897		,284.8 	,0.686	,0.596],
        ["#ED7651",  	0.931,	0.463,	0.316		,13.2   ,0.446	,0.57 ],
        ["#FEF888",  	0.998,	0.974,	0.532		,57.4   ,0.363	,0.835],
        ["#19CB97",  	0.099,	0.795,	0.591		,163.4 	,0.8	,0.495],
        ["#362698",  	0.211,	0.149,	0.597		,247.3 	,0.533	,0.319],
        ["#7E7EB8",  	0.495,	0.493,	0.721		,240. 	,0.135	,0.57 ],
    ]
    def rgb_to_hsi_0(self):
        from LEDDimmerServer.color import rgb_to_hsi
        for name, R, G, B, H, S, I in self._table:
            h,s,i = rgb_to_hsi(R, G, B)
            unittest.TestCase.assertAlmostEqual(h, H)
            unittest.TestCase.assertAlmostEqual(s, S)
            unittest.TestCase.assertAlmostEqual(i, I)
 
       
    def hsi_to_rgb(self):
        from LEDDimmerServer.color import hsi_to_rgb
        for name, R, G, B, H, S, I in self._table:
            r, g, b = hsi_to_rgb(H, S, I)
            unittest.TestCase.assertAlmostEqual(r, R)
            unittest.TestCase.assertAlmostEqual(g, G)
            unittest.TestCase.assertAlmostEqual(b, B)
 
 

if __name__ == '__main__':
    unittest.main()