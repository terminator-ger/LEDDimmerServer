import json
import unittest
from LEDDimmerServer.LEDDimmer import LEDDimmer, parse_arguments
import time
import sys
from LEDDimmerServer.DimmerBackend import DimmerBackend
from threading import Thread

class WTest(unittest.TestCase):
    def setUp(self):
        from gpiozero import Device
        from gpiozero.pins.mock import MockFactory, MockPWMPin
        Device.pin_factory = MockFactory(pin_class=MockPWMPin)
        return super().setUp()
    
    
    def test_setup_with_config(self):
        config = parse_arguments(["--host", "127.0.0.1", "--port", "8080"])
        srv = LEDDimmer(config)
        srv_thread = Thread(target=srv.run)
        srv_thread.daemon = True  # Do not make us wait for you to exit
        srv_thread.start()
        time.sleep(1)
        srv.stop()
        srv_thread.join()
        self.assertTrue(True)

    def test_toggle(self):
        sys.argv=[]
        config = parse_arguments()
        config["has_rgb"] = False
        config["has_w"] = True
        backend = DimmerBackend(config)
        backend.toggle()
        self.assertTrue(backend.GPIO_W_PWM.is_active)
 
    def test_on(self):
        sys.argv=[]
        config = parse_arguments()
        config["has_rgb"] = False
        config["has_w"] = True
        backend = DimmerBackend(config)
        backend.on()
        self.assertTrue(backend.GPIO_W_PWM.is_active)
        
    def test_off(self):
        sys.argv=[]
        config = parse_arguments()
        config["has_rgb"] = False
        config["has_w"] = True
        backend = DimmerBackend(config)
        backend.on()
        backend.off()
        self.assertFalse(backend.GPIO_W_PWM.is_active)
 
    def test_incr(self):
        sys.argv=[]
        config = parse_arguments()
        config["has_rgb"] = False
        config["has_w"] = True
        backend = DimmerBackend(config)
        backend.incr()
        self.assertTrue(backend.GPIO_W_PWM.is_active)
 
    def test_decr(self):
        sys.argv=[]
        config = parse_arguments()
        config["has_rgb"] = False
        config["has_w"] = True
        backend = DimmerBackend(config)
        backend.decr()
        self.assertFalse(backend.GPIO_W_PWM.is_active)
        
    def test_on_incr(self):
        sys.argv=[]
        config = parse_arguments()
        config["has_rgb"] = False
        config["has_w"] = True
        backend = DimmerBackend(config)
        backend.on()
        backend.incr()
        self.assertTrue(backend.GPIO_W_PWM.is_active)
        self.assertEqual(backend.GPIO_W_PWM.value, 1.0)
         
    def test_off_incr(self):
        sys.argv=[]
        config = parse_arguments()
        config["has_rgb"] = False
        config["has_w"] = True
        backend = DimmerBackend(config)
        backend.off()
        backend.incr()
        self.assertTrue(backend.GPIO_W_PWM.is_active)
        self.assertEqual(backend.GPIO_W_PWM.value, 0.1)  # Assuming incr sets a default value of 0.1
        
    def test_toggle_incr(self):
        '''
        Test toggling RGB and then incrementing brightness
        default is off, toggle to on, then incr
        '''
        sys.argv=[]
        config = parse_arguments()
        config["has_rgb"] = False
        config["has_w"] = True
        backend = DimmerBackend(config)
        backend.toggle()
        backend.incr()
        self.assertTrue(backend.GPIO_W_PWM.is_active)
        self.assertEqual(backend.GPIO_W_PWM.value, 1.0)  # Assuming incr sets a default value of 0.1

    def test_on_decr(self):
        sys.argv=[]
        config = parse_arguments()
        config["has_rgb"] = False
        config["has_w"] = True
        backend = DimmerBackend(config)
        backend.on()
        backend.decr()
        self.assertTrue(backend.GPIO_W_PWM.is_active)
        self.assertEqual(backend.GPIO_W_PWM.value, 0.9)  # Assuming decr reduces brightness by 0.1
         
    def test_off_decr(self):
        sys.argv=[]
        config = parse_arguments()
        config["has_rgb"] = False
        config["has_w"] = True
        backend = DimmerBackend(config)
        backend.off()
        backend.decr()
        self.assertFalse(backend.GPIO_W_PWM.is_active)
        self.assertEqual(backend.GPIO_W_PWM.value, 0.0)  # Assuming incr sets a default value of 0.1
        
    def test_toggle_decr(self):
        '''
        Test toggling RGB and then incrementing brightness
        default is off, toggle to on, then incr
        '''
        sys.argv=[]
        config = parse_arguments()
        config["has_rgb"] = False
        config["has_w"] = True
        backend = DimmerBackend(config)
        backend.toggle()
        backend.decr()
        self.assertTrue(backend.GPIO_W_PWM.is_active)
        self.assertEqual(backend.GPIO_W_PWM.value, 0.9)  # Assuming incr sets a default value of 0.1
                
    def test_wakeuptime_more_than_wakeup_period_toggle(self):
        sys.argv=[]
        config = parse_arguments()
        config["has_rgb"] = False
        config["has_w"] = True
        timedelta = config['active_profile']['wakeup_sequence_len'] * 60
        current_epoch = int(time.time())
        wakeup_time = current_epoch + timedelta + 5  # More than wakeup period
        backend = DimmerBackend(config)
        backend.wakeuptime(wakeup_time)
        backend.incr()
        self.assertTrue(backend.GPIO_W_PWM.is_active)
        self.assertEqual(backend.GPIO_W_PWM.value, 0.1)  # Assuming incr sets a default value of 0.1
        self.assertFalse(backend.wakeup_task.finished.is_set())
        backend.wakeup_task.cancel()
         
    def test_wakeuptime_less_than_wakeup_period_toggle(self):
        sys.argv=[]
        config = parse_arguments()
        config["has_rgb"] = False
        config["has_w"] = True
        timedelta = config['active_profile']['wakeup_sequence_len'] * 60
        current_epoch = int(time.time())
        wakeup_time = current_epoch + timedelta + 5  # More than wakeup period
        backend = DimmerBackend(config)
        backend.wakeuptime(wakeup_time)
 
        backend.incr()
        self.assertTrue(backend.GPIO_W_PWM.is_active)
        self.assertEqual(backend.GPIO_W_PWM.value, 0.1)  # Assuming incr sets a default value of 0.1
        self.assertFalse(backend.wakeup_task.finished.is_set()) # Ensure the wakeup task has finished
        backend.wakeup_task.cancel()
        
    def test_wakeuptime_wakeuptime_toggle(self):
        sys.argv=[]
        config = parse_arguments()
        config["has_rgb"] = False
        config["has_w"] = True
        timedelta = config['active_profile']['wakeup_sequence_len'] * 60
        current_epoch = int(time.time())
        wakeup_time_old = current_epoch + timedelta + 6  # More than wakeup period
        wakeup_time_new = current_epoch + timedelta + 5  # More than wakeup period
        backend = DimmerBackend(config)
        backend.wakeuptime(wakeup_time_old)
        backend.wakeuptime(wakeup_time_new)
 
        self.assertFalse(backend.GPIO_W_PWM.is_active)
        self.assertEqual(backend.wakeup_task.interval, 5)  # Ensure the wakeup task has finished
        backend.wakeup_task.cancel()
 
    def test_wakeuptime_wakeuptime_interupt(self):
        sys.argv=[]
        config = parse_arguments()
        config["has_rgb"] = False
        config["has_w"] = True
        timedelta = config['active_profile']['wakeup_sequence_len'] * 60
        current_epoch = int(time.time())
        wakeup_time_old = current_epoch + timedelta + 2  # More than wakeup period
        wakeup_time_new = current_epoch + timedelta + 10  # More than wakeup period
        backend = DimmerBackend(config)
        backend.wakeuptime(wakeup_time_old)
        time.sleep(4)
        backend.wakeuptime(wakeup_time_new)
 
        self.assertFalse(backend.GPIO_W_PWM.is_active)
        self.assertEqual(backend.wakeup_task.interval, 6)  # Ensure the wakeup task has finished
        backend.wakeup_task.cancel()
        
    def test_sunrise_interupt(self):
        sys.argv=[]
        config = parse_arguments()
        config["has_rgb"] = False
        config["has_w"] = True
        backend = DimmerBackend(config)
        backend.sunrise()
 
        self.assertFalse(backend.GPIO_W_PWM.is_active)
        backend.wakeup_task.cancel()        
 
    def test_sunrise_sunrise_interupt(self):
        sys.argv=[]
        config = parse_arguments()
        config["has_rgb"] = False
        config["has_w"] = True
        backend = DimmerBackend(config)
        backend.sunrise()
        backend.sunrise()
 
        self.assertFalse(backend.GPIO_W_PWM.is_active)
        backend.wakeup_task.cancel()        
         
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
def test_rgb_to_hsi(self):
    from LEDDimmerServer.color import rgb_to_hsi
    for name, R, G, B, H, S, I in self._table:
        h, s, i = rgb_to_hsi(R, G, B)
        self.assertAlmostEqual(h, H, places=2)
        self.assertAlmostEqual(s, S, places=2)
        self.assertAlmostEqual(i, I, places=2)

def test_hsi_to_rgb(self):
    from LEDDimmerServer.color import hsi_to_rgb
    for name, R, G, B, H, S, I in self._table:
        r, g, b = hsi_to_rgb(H, S, I)
        self.assertAlmostEqual(r, R, places=2)
        self.assertAlmostEqual(g, G, places=2)
        self.assertAlmostEqual(b, B, places=2)
 
 

if __name__ == '__main__':
    unittest.main()