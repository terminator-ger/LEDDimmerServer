import json
import unittest
from LEDDimmerServer.LEDDimmer import LEDDimmer, parse_arguments
import time
import sys
from LEDDimmerServer.DimmerBackend import DimmerBackend
from threading import Thread

from LEDDimmerServer.color import load_json

class DimmerBackendCommonTest(unittest.TestCase):
    def setUp(self):
        from gpiozero import Device
        from gpiozero.pins.mock import MockFactory, MockPWMPin
        Device.pin_factory = MockFactory(pin_class=MockPWMPin)
        return super().setUp()
    
    def test_update_color(self):
        sys.argv=[]
        config = parse_arguments()
        config["has_rgb"] = True
        config["has_w"] = False
        backend = DimmerBackend(config)
        backend.color({"high_sky": ["#0000FF", "#00FF00", "#FF0000", "#FFFFFF", "#000000"]})
        color = load_json("colors.json", "high_sky")
        self.assertEqual(color, ["#0000FF", "#00FF00", "#FF0000", "#FFFFFF", "#000000"])