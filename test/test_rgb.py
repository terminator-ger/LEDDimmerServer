import json
import unittest
from LEDDimmerServer.LEDDimmer import LEDDimmer, parse_arguments
import time
import sys
from LEDDimmerServer.DimmerBackend import DimmerBackend
from threading import Thread
from LEDDimmerServer.utils import GlobalExceptionWatcher

class RGBTest(unittest.TestCase):
    def setUp(self):
        from gpiozero import Device
        from gpiozero.pins.mock import MockFactory, MockPWMPin
        Device.pin_factory = MockFactory(pin_class=MockPWMPin)
        return super().setUp()
    
    def test_setup_with_config(self):
        with GlobalExceptionWatcher():
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
        with GlobalExceptionWatcher():
            sys.argv=[]
            config = parse_arguments()
            config["has_rgb"] = True
            config["has_w"] = False
            backend = DimmerBackend(config)
            backend.toggle()
            self.assertTrue(backend.GPIO_RGB.is_active)
 
    def test_on(self):
        with GlobalExceptionWatcher():
            sys.argv=[]
            config = parse_arguments()
            config["has_rgb"] = True
            config["has_w"] = False
            backend = DimmerBackend(config)
            backend.on()
            self.assertTrue(backend.GPIO_RGB.is_active)
        
    def test_off(self):
        with GlobalExceptionWatcher():
            sys.argv=[]
            config = parse_arguments()
            config["has_rgb"] = True
            config["has_w"] = False
            backend = DimmerBackend(config)
            backend.on()
            backend.off()
            self.assertFalse(backend.GPIO_RGB.is_active)
 
    def test_incr(self):
        with GlobalExceptionWatcher():
            sys.argv=[]
            config = parse_arguments()
            config["has_rgb"] = True
            config["has_w"] = False
            backend = DimmerBackend(config)
            backend.incr()
            self.assertFalse(backend.GPIO_RGB.is_active)
        
    def test_on_incr(self):
        with GlobalExceptionWatcher():
            sys.argv=[]
            config = parse_arguments()
            config["has_rgb"] = True
            config["has_w"] = False
            backend = DimmerBackend(config)
            backend.on()
            backend.incr()
            self.assertTrue(backend.GPIO_RGB.is_active)
            self.assertEqual(backend.GPIO_RGB.value, (1.0, 1.0, 1.0))
         
    def test_off_incr(self):
        with GlobalExceptionWatcher():
            sys.argv=[]
            config = parse_arguments()
            config["has_rgb"] = True
            config["has_w"] = False
            backend = DimmerBackend(config)
            backend.off()
            backend.incr()
            self.assertFalse(backend.GPIO_RGB.is_active)
            self.assertEqual(backend.GPIO_RGB.value, (0.0, 0.0, 0.0))  # Assuming incr sets a default value of 0.1
        
    def test_toggle_incr(self):
        '''
        Test toggling RGB and then incrementing brightness
        default is off, toggle to on, then incr
        '''
        with GlobalExceptionWatcher():
            sys.argv=[]
            config = parse_arguments()
            config["has_rgb"] = True
            config["has_w"] = False
            backend = DimmerBackend(config)
            backend.toggle()
            backend.incr()
            self.assertTrue(backend.GPIO_RGB.is_active)
            self.assertEqual(backend.GPIO_RGB.value, (1.0, 1.0, 1.0))  # Assuming incr sets a default value of 0.1
 
 
    def test_decr(self):
        with GlobalExceptionWatcher():
            sys.argv=[]
            config = parse_arguments()
            config["has_rgb"] = True
            config["has_w"] = False
            backend = DimmerBackend(config)
            backend.decr()
            self.assertFalse(backend.GPIO_RGB.is_active)
        
    def test_on_decr(self):
        with GlobalExceptionWatcher():
            sys.argv=[]
            config = parse_arguments()
            config["has_rgb"] = True
            config["has_w"] = False
            backend = DimmerBackend(config)
            backend.on()
            backend.decr()
            self.assertTrue(backend.GPIO_RGB.is_active)
            self.assertEqual(backend.GPIO_RGB.value, (0.9, 0.9, 0.9))
         
    def test_off_decr(self):
        with GlobalExceptionWatcher():
            sys.argv=[]
            config = parse_arguments()
            config["has_rgb"] = True
            config["has_w"] = False
            backend = DimmerBackend(config)
            backend.off()
            backend.decr()
            self.assertFalse(backend.GPIO_RGB.is_active)
            self.assertEqual(backend.GPIO_RGB.value, (0.0, 0.0, 0.0))  # Assuming incr sets a default value of 0.1
        
    def test_toggle_decr(self):
        '''
        Test toggling RGB and then incrementing brightness
        default is off, toggle to on, then incr
        '''
        with GlobalExceptionWatcher():
            sys.argv=[]
            config = parse_arguments()
            config["has_rgb"] = True
            config["has_w"] = False
            backend = DimmerBackend(config)
            backend.toggle()
            backend.decr()
            self.assertTrue(backend.GPIO_RGB.is_active)
            self.assertEqual(backend.GPIO_RGB.value, (0.9, 0.9, 0.9))  # Assuming incr sets a default value of 0.1
         
    def test_wakeuptime_more_than_wakeup_period_toggle(self):
        with GlobalExceptionWatcher():
            sys.argv=[]
            config = parse_arguments()
            config["has_rgb"] = True
            config["has_w"] = False
            timedelta = config['active_profile']['wakeup_sequence_len'] * 60
            current_epoch = int(time.time())
            wakeup_time = current_epoch + timedelta + 5  # More than wakeup period
            backend = DimmerBackend(config)
            backend.wakeuptime(wakeup_time)
            backend.incr()
            self.assertFalse(backend.GPIO_RGB.is_active)
            self.assertEqual(backend.GPIO_RGB.value, (0.0, 0.0, 0.0))  # Assuming incr sets a default value of 0.1
            self.assertFalse(backend.wakeup_task.finished.is_set())
            backend.interrupt_wakeup()

    def test_wakeuptime_less_than_wakeup_period_toggle(self):
        with GlobalExceptionWatcher():
            sys.argv=[]
            config = parse_arguments()
            config["has_rgb"] = True
            config["has_w"] = False
            timedelta = config['active_profile']['wakeup_sequence_len'] * 60
            current_epoch = int(time.time())
            wakeup_time = current_epoch + timedelta + 5  # More than wakeup period
            backend = DimmerBackend(config)
            backend.wakeuptime(wakeup_time)
     
            backend.incr()
            self.assertFalse(backend.GPIO_RGB.is_active)
            self.assertEqual(backend.GPIO_RGB.value, (0.0, 0.0, 0.0))  # Assuming incr sets a default value of 0.1
            self.assertFalse(backend.wakeup_task.finished.is_set()) # Ensure the wakeup task has finished
            backend.interrupt_wakeup()

    def test_wakeuptime_wakeuptime_toggle(self):
        with GlobalExceptionWatcher():
            sys.argv=[]
            config = parse_arguments()
            config["has_rgb"] = True
            config["has_w"] = False
            timedelta = config['active_profile']['wakeup_sequence_len'] * 60
            current_epoch = int(time.time())
            wakeup_time_old = current_epoch + timedelta + 6  # More than wakeup period
            wakeup_time_new = current_epoch + timedelta + 5  # More than wakeup period
            backend = DimmerBackend(config)
            backend.wakeuptime(wakeup_time_old)
            backend.wakeuptime(wakeup_time_new)
     
            self.assertFalse(backend.GPIO_RGB.is_active)
            self.assertEqual(backend.wakeup_task.interval, 5)  # Ensure the wakeup task has finished
            backend.interrupt_wakeup()

    def test_wakeuptime_wakeuptime_interupt(self):
        with GlobalExceptionWatcher():
            sys.argv=[]
            config = parse_arguments()
            config["has_rgb"] = True
            config["has_w"] = False
            timedelta = config['active_profile']['wakeup_sequence_len'] * 60
            current_epoch = int(time.time())
            wakeup_time_old = current_epoch + timedelta + 2  # More than wakeup period
            wakeup_time_new = current_epoch + timedelta + 10  # More than wakeup period
            backend = DimmerBackend(config)
            backend.wakeuptime(wakeup_time_old)
            time.sleep(4)
            backend.wakeuptime(wakeup_time_new)
     
            self.assertFalse(backend.GPIO_RGB.is_active)
            self.assertEqual(backend.wakeup_task.interval, 6)  # Ensure the wakeup task has finished
            backend.interrupt_wakeup()

    def test_sunrise_interupt(self):
        with GlobalExceptionWatcher():
            sys.argv=[]
            config = parse_arguments()
            config["has_rgb"] = True
            config["has_w"] = False
            backend = DimmerBackend(config)
            backend.sunrise()
     
            self.assertFalse(backend.GPIO_RGB.is_active)
            backend.interrupt_wakeup()

    def test_sunrise_sunrise_interupt(self):
        with GlobalExceptionWatcher():
            sys.argv=[]
            config = parse_arguments()
            config["has_rgb"] = True
            config["has_w"] = False
            backend = DimmerBackend(config)
            backend.sunrise()
            backend.sunrise()
     
            self.assertFalse(backend.GPIO_RGB.is_active)
            backend.interrupt_wakeup()
            
 
 

if __name__ == '__main__':
    unittest.main()