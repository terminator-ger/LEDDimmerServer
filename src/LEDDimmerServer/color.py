from asyncio import Task
import logging
from threading import Lock
import time
from typing import Dict, List, Tuple
import json
import os

from gpiozero import PWMLED, RGBLED
from importlib.resources import files

def load_json_dict(f) -> Dict:
    logging.info(f"Loading json file {f}")
    config_file = files("config").joinpath(f)
    with config_file.open() as fp:
        return json.load(fp)
 
def load_json(f, name="sunrise_01_rgb"):
    logging.info(f"Loading json file {f} for {name}")
    config_file = files("config").joinpath(f)
    with config_file.open() as fp:
        colors = json.load(fp)
        if name not in colors:
            raise KeyError(f"{name} cannot be found")
    return colors[name]

def safe_json(f, dict: Dict):
    config_file = files("config").joinpath(f)
    with config_file.open("w", encoding='utf-8') as fp:
        json.dump(dict, fp, sort_keys=True, indent=4)

def modify_json(key: str, value, json_name: str):
    """    Modify a json file by adding or updating a key-value pair.
    If the key already exists, it will be updated with the new value.
    If the key does not exist, it will be added.
    """
    logging.info(f"Modifying json file {json_name} with key {key} and value {value}")
    config_file = files("config").joinpath(json_name)
    with config_file.open("r", encoding='utf-8') as json_file:
        _dict = json.load(json_file)
    if _dict is None:
        raise ValueError(f"Cannot load json file {json_name}")
    _dict[key] = value
    safe_json(json_name, _dict)


def hexcodes2list(color_hex_codes: List[str]) -> Tuple[List[int], List[int], List[int]]:
    r = []
    g = []
    b = []
    for color_hex_code in color_hex_codes:
        if "#" in color_hex_code:
            color_hex_code = color_hex_code.lstrip("#")
        assert len(color_hex_code) == 6

        r.append(int(color_hex_code[:2], 16))
        g.append(int(color_hex_code[2:4], 16))
        b.append(int(color_hex_code[4:], 16))
    return r,g,b

def interp(x0, xs, ys):
    for x,y in zip(xs,ys):
        if x==x0:       # <- exact "hit"
            return y
        if x>x0:        # px<x0<x - assuming there was a px already
            return py+(y-py)*(x0-px)/(x-px)
        px=x
        py=y

class SunriseProgress:
    def __init__(self, config, rgb_pwm: RGBLED, w_pwm: PWMLED):
        self.reload(config)
        # copy pins
        self.GPIO_RGB = rgb_pwm
        self.GPIO_W = w_pwm

        self.pause = (self.config['active_profile']
                 ['wakeup_sequence_len'] * 60) / self.config['active_profile']['pwm_steps']

        self.is_in_wakeup_sequence: Lock = Lock()
    
    def wakeup_sequence_is_locked(self) -> bool:
        return self.is_in_wakeup_sequence.locked()

    def wakeup_sequence_lock(self) -> None:
        self.is_in_wakeup_sequence.acquire_lock()
    
    def wakeup_sequence_release_lock(self) -> None:
        self.is_in_wakeup_sequence.release_lock()

    def run(self):
        logging.debug("starting up with the lightshow")
        self.wakeup_sequence_lock()
 
        for progress in range(0, self.config['active_profile']['pwm_steps']):
            p = progress / self.config['active_profile']['pwm_steps']
            lum = self.get_sunrise_intensity(
                        p, 
                        self.config['active_profile']['gradient_interpolation'], 
                        self.config['active_profile']['gradient'])
            
            logging.info("setting light to %s", str(lum))
            
            if self.config['has_w']:
                self.GPIO_W.value = lum
            if self.config['has_rgb']:
                color = self.get_sunrise_color(
                        t_cur=p, 
                        lum=lum,
                        interpolation=self.config['active_profile']['color_interpolation'], 
                        scale=self.config['active_profile']['color'])
 
                self.GPIO_RGB.value = color
                
            time.sleep(self.pause)
            print('wakeup')
            if not self.is_in_wakeup_sequence.locked():
                # if the wakeup sequence is cancelled, stop the lightshow
                print('cancelled')
                logging.info("wakeup sequence cancelled")
                return
        
    def reload(self, config):
        """
            Reload the color and gradient json files
        """
        self.config = config
        self.color_pallet = load_json_dict("colors.json")
        self.grad = load_json_dict("gradient.json")

    def get_sunrise_color(self, t_cur:float, lum:float=1.0, interpolation:str='linear', scale:str="sunrise_01_rgb") -> tuple[float, float, float]:
        """
            t_cur is relative percentual progress
        """
        if scale not in self.color_pallet:
            raise KeyError(f"{scale} cannot be found")
        color_pallet = self.color_pallet[scale]
        colors = hexcodes2list(color_pallet)
        time_ref = [0, .25, .5, .75, 1]
        if interpolation == 'linear':
            r,g,b = [interp(t_cur, time_ref, color) for color in colors]
        else:
            # fallback linear
            r, g, b = [interp(t_cur, time_ref, color) for color in colors]
        
        # normalize
        r /= 255
        g /= 255
        b /= 255
        # scale by luminecence
        r *= lum
        g *= lum
        b *= lum
        return r,g,b


    def get_sunrise_intensity(self, t_cur, interpolation='linear', gradient="exp") -> float:
        grad = self.grad[gradient]
        
        time_ref = [0, .25, .5, .75, 1]

        if interpolation == 'linear':
            lum = interp(t_cur, time_ref, grad)
        else:
            lum = interp(t_cur, time_ref, grad)
            
        return lum


"""
    Based on: http://www.tannerhelland.com/4435/convert-temperature-rgb-algorithm-code/
    Comments resceived: https://gist.github.com/petrklus/b1f427accdf7438606a6
"""

import math
def convert_K_to_RGB(colour_temperature):
    """
    Converts from K to RGB, algorithm courtesy of 
    http://www.tannerhelland.com/4435/convert-temperature-rgb-algorithm-code/
    """
    #range check
    if colour_temperature < 1000: 
        colour_temperature = 1000
    elif colour_temperature > 40000:
        colour_temperature = 40000
    
    tmp_internal = colour_temperature / 100.0
    
    # red 
    if tmp_internal <= 66:
        red = 255
    else:
        red = 329.698727446 * math.pow(tmp_internal - 60, -0.1332047592)
        red = min(max(red, 0), 255)
   
    # green
    if tmp_internal <=66:
        green = 99.4708025861 * math.log(tmp_internal) - 161.1195681661
        green = min(max(green, 0), 255)
    else:
        green = 288.1221695283 * math.pow(tmp_internal - 60, -0.0755148492)
        green = min(max(green, 0), 255)
    
    # blue
    if tmp_internal >=66:
        blue = 255
    elif tmp_internal <= 19:
        blue = 0
    else:
        blue = 138.5177312231 * math.log(tmp_internal - 10) - 305.0447927307
        blue = min(max(blue, 0), 255)
   
    return red, green, blue


'''
    From https://github.com/python/cpython/blob/3.13/Lib/colorsys.py
'''
ONE_THIRD = 1.0/3.0
ONE_SIXTH = 1.0/6.0
TWO_THIRD = 2.0/3.0

# HLS: Hue, Luminance, Saturation
# H: position in the spectrum
# L: color lightness
# S: color saturation

def rgb_to_hsi(r, g, b):

    M = max(r, g, b)
    m = min(r, g, b)
    sumc = (M+m)
    C = (M-m)

    # I
    i = (r+g+b)/3.0

    if m == M:
        return 0.0, i, 0.0
    
    # S
    if i == 0:
       s = 0
    else:
        s = 1 - (m/i)

    # H
    rc = (M-r) / C
    gc = (M-g) / C
    bc = (M-b) / C    
    if r == M:
        h = bc-gc
    elif g == M:
        h = 2.0+rc-bc
    else:
        h = 4.0+gc-rc
    h = (h/6.0) % 1.0
    return h, i, s

def _v(m1, m2, hue):
    hue = hue % 1.0
    if hue < ONE_SIXTH:
        return m1 + (m2-m1)*hue*6.0
    if hue < 0.5:
        return m2
    if hue < TWO_THIRD:
        return m1 + (m2-m1)*(TWO_THIRD-hue)*6.0
    return m1


def clip(value, min_value, max_value):
    """
    Clip the value to be within the specified range.
    """
    return max(min_value, min(value, max_value))

def rad2deg(radians):
    """
    Convert radians to degrees.
    """
    return radians * (180.0 / math.pi)

def rgb2hsi(red,green,blue):
    s = 0
    i = 0
    h = []
    RG = red-green+0.001  # Red-Green, add a constant to prevent undefined value
    RB = red-blue+0.001  # Red-Blue
    GB = green-blue+0.001  # Green-Blue
    theta = math.acos(clip(((0.5*(RG+RB))/(RG**2+RB*GB)**0.5), -1, 1))  # Still in radians
    theta = rad2deg(theta)  # Convert to degrees
    if blue <= green:
        h = theta
    else:
        h = 360 - theta
    # Hue range will be automatically scaled to 0-255 by matplotlib for display
    # We will need to convert manually to range of 0-360 in hsi2rgb function
    #h = ((h - h.min()) * (1/(h.max() - h.min()) * 360))  # Scale h to 0-360
    minRGB = min(min(red, green), blue)
    s = 1-((3/(red+green+blue+0.001))*minRGB)  # Add 0.001 to prevent divide by zero
    i = (red+green+blue)/3  # Intensity: 0-1
    return h, s, i

def hsi_to_rgb(h, s, i):
    h_ = h / 6.0
    z = 1 - abs((h_ % 2) -1)
    c = (3*i*s) / (1+z)
    x = c*z
    if 0 <= h_ <= 1:
        r_, g_, b_ = c, x, 0
    elif 1 <= h_ <= 2:
        r_, g_, b_ = x, c, 0
    elif 2 <= h_ <= 3:
        r_, g_, b_ = 0, c, x
    elif 3 <= h_ <= 4:
        r_, g_, b_ = 0, x, c
    elif 4 <= h_ <= 5:
        r_, g_, b_ = x, 0, c 
    elif 4 <= h_ <= 5:
        r_, g_, b_ = c, 0, x 
    else:
        r_, g_, b_ = 0, 0, 0
    
    m_ = i * (1-s)
    r = r_ + m_
    g = g_ + m_
    b = b_ + m_
    return r, g, b
