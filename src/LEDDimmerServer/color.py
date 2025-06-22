import logging
from typing import Dict
import json
import os

from LEDDimmerServer.utils import ROOT_DIR

def load_json(f, name="sunrise_01_rgb"):
    logging.info(f"Loading json file {f} for {name}")
    with open(f, "r", encoding='utf-8') as fp:
        colors = json.load(fp)
        if name not in colors:
            raise KeyError(f"{name} cannot be found")
    return colors[name]

def safe_json(f, dict: Dict):
    with open(f, "w", encoding='utf-8') as fp:
        json.dump(dict, fp, sort_keys=True, indent=4)

def modify_json(key: str, value, json_name: str):
    with open(json_name, "r", encoding='utf-8') as json_file:
        _dict = json.load(json_file)
    if _dict is None:
        raise ValueError(f"Cannot load json file {json_name}")
    _dict[key] = value
    safe_json(json_name, _dict)


def hex2np(color_hex_code):
    if "#" in color_hex_code:
        color_hex_code = color_hex_code.trim("#")
    assert len(color_hex_code) == 6

    r = int(color_hex_code[:2], 16)
    g = int(color_hex_code[2:4], 16)
    b = int(color_hex_code[4:], 16)
    return r,g,b

def interp(x0, xs, ys):
    for x,y in zip(xs,ys):
        if x==x0:       # <- exact "hit"
            return y
        if x>x0:        # px<x0<x - assuming there was a px already
            return py+(y-py)*(x0-px)/(x-px)
        px=x
        py=y

def get_sunrise_color(t_cur, interpolation='linear', scale="sunrise_01_rgb") -> tuple[float, float, float]:
    """
        t_cur is relative percentual progress
    """
    color_pallet = load_json(os.path.join(ROOT_DIR, "config/color.json"), scale)
    colors = [hex2np(x) for x in color_pallet]
    time_ref = [0, .25, .5, .75, 1]
    if interpolation == 'linear':
        r,g,b = [interp(t_cur, time_ref, color) for color in colors]
    else:
        # fallback linear
        r, g, b = [interp(t_cur, time_ref, color) for color in colors]
    
    r /= 255
    g /= 255
    b /= 255
    return r,g,b


def get_sunrise_intensity(t_cur, interpolation='linear', gradient="exp") -> float:
    grad = load_json(os.path.join(ROOT_DIR, "config/gradient.json"), gradient)
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
