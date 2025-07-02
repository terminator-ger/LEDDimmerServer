import json
import unittest
from LEDDimmerServer.LEDDimmer import LEDDimmer, parse_arguments
import time
import sys
from threading import Thread
import requests

class HttpTest(unittest.TestCase):
    def setUp(self):
        from gpiozero import Device
        from gpiozero.pins.mock import MockFactory, MockPWMPin
        Device.pin_factory = MockFactory(pin_class=MockPWMPin)
        config = parse_arguments(["--host", "127.0.0.1", "--port", "8080"])
        config["has_rgb"] = False
        config["has_w"] = True
        self.srv = LEDDimmer(config)
        self.srv_thread = Thread(target=self.srv.run)
        self.srv_thread.daemon = True  # Do not make us wait for you to exit
        self.srv_thread.start() 

        return super().setUp()
    
    def tearDown(self):
        self.srv.shutdown()
        self.srv_thread.join()
        return super().tearDown()
    
    def test_http_toggle(self):
        r = requests.put("http://127.0.0.1:8080/toggle", data = {})#, data=payload) 
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.text, "TOGGLE ON")
        self.assertTrue(self.srv.backend.GPIO_W.is_active)  # Simulate the LED being on


    def test_http_toggle_invalid_payload(self):
        r = requests.put("http://127.0.0.1:8080/toggle", data = {"test": 12385})#, data=payload) 
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.text, "TOGGLE ON")
        self.assertTrue(self.srv.backend.GPIO_W.is_active)  # Simulate the LED being on


    def test_http_on_payload(self):
        r = requests.put("http://127.0.0.1:8080/on", data = {})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.text, "ON")
        self.assertTrue(self.srv.backend.GPIO_W.is_active)  # Simulate the LED being on
        
    def test_http_off_payload(self):
        r = requests.put("http://127.0.0.1:8080/off", data = {})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.text, "OFF")
        self.assertFalse(self.srv.backend.GPIO_W.is_active)  # Simulate the LED being on

    def test_http_incr(self):
        r = requests.put("http://127.0.0.1:8080/incr", data = {})
        self.assertEqual(r.status_code, 405)
        self.assertEqual(r.text, "INCR")
        self.assertFalse(self.srv.backend.GPIO_W.is_active)  # Simulate the LED being on

    def test_http_decr(self):
        r = requests.put("http://127.0.0.1:8080/decr", data = {})
        self.assertEqual(r.status_code, 405)    
        self.assertEqual(r.text, "DECR")
        self.assertFalse(self.srv.backend.GPIO_W.is_active)  # Simulate the LED being on

    def test_http_wakeup(self):
        now = int(time.time()) + 60 * 30 + 1
        r = requests.put("http://127.0.0.1:8080/wakeuptime", data = json.dumps({"time": now}))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.text, f"WAKEUP {now}")
        self.assertFalse(self.srv.backend.GPIO_W.is_active)  # Simulate the LED being on

    def test_http_wakeup_cancel(self):
        now = int(time.time()) + 60 * 30 + 1
        r = requests.put("http://127.0.0.1:8080/wakeuptime", data = json.dumps({"time": now}))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.text, f"WAKEUP {now}")
        self.assertFalse(self.srv.backend.GPIO_W.is_active)  # Simulate the LED being on
        self.assertTrue(self.srv.backend.wakeup_task.is_alive())
        r = requests.put("http://127.0.0.1:8080/wakeuptime", data = json.dumps({"time": 0}))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.text, f"WAKEUP {0}")
        self.assertFalse(self.srv.backend.wakeup_task.is_alive())
 

    def test_http_wakeup_malformed_json(self):
        now = int(time.time()) + 60 * 30 + 1
        r = requests.put("http://127.0.0.1:8080/wakeuptime", data = json.dumps({"time_": now}))
        self.assertEqual(r.status_code, 400)

    def test_http_wakeup_malformed_time(self):
        r = requests.put("http://127.0.0.1:8080/wakeuptime", data = json.dumps({"time": "test"}))
        self.assertEqual(r.status_code, 400)

    def test_http_sunrise(self):
        r = requests.put("http://127.0.0.1:8080/sunrise", data = {})
        self.assertEqual(r.status_code, 200)
        self.assertIn("SUNRISE", r.text)
        
    def test_http_sunrise_sunrise(self):
        r = requests.put("http://127.0.0.1:8080/sunrise", data = {})
        self.assertEqual(r.status_code, 200)
        self.assertIn("SUNRISE", r.text)
        self.assertTrue(self.srv.backend.wakeup_task.is_alive())
        r = requests.put("http://127.0.0.1:8080/sunrise", data = {})
        self.assertEqual(r.status_code, 200)
        self.assertIn("SUNRISE", r.text)
        self.assertFalse(self.srv.backend.wakeup_task.is_alive())


    def test_http_color(self):
        r = requests.put("http://127.0.0.1:8080/color", data = json.dumps({"high_sky": "#0000FF #00FF00 #FF0000 #FFFFFF #000000"}))
        self.assertEqual(r.status_code, 200)
        self.assertEqual("COLOR", r.text)

    def test_http_gradient(self):
        r = requests.put("http://127.0.0.1:8080/gradient", data = json.dumps({"custom": [0, 0.1, 0.2, 0.6, 0.8, 1.0]}))
        self.assertEqual(r.status_code, 200)
        self.assertEqual("GRADIENT", r.text)

    def test_http_status(self):
        r = requests.put("http://127.0.0.1:8080/status", data={})
        self.assertEqual(r.status_code, 200)
        self.assertIn("STATUS", r.text)









