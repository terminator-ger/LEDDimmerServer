import numpy as np
import json
from scipy.interpolate import CubicSpline

def load_json(f, name="sunrise_01_rgb"):
    colors = json.load(f)
    if name not in colors:
        raise KeyError(f"{name} cannot be found")
    return colors

def safe_json(f, colors):
    with open(f, "w") as fp:
        json.dump(colors, fp, sort_keys=True, indent=4)

def modify_json(key, value, json_name):
    _dict = json.load(json_name)
    _dict[key] = value
    safe_json(_dict)


def hex2np(color_hex_code):
    if "#" in color_hex_code:
        color_hex_code = color_hex_code.trim("#")
    assert len(color_hex_code) == 6

    r = int(color_hex_code[:2], 16)
    g = int(color_hex_code[2:4], 16)
    b = int(color_hex_code[4:], 16)
    return r,g,b


def get_sunrise_color(t_cur, interpolation='linear', scale="sunrise_01_rgb") -> tuple[float, float, float]:
    """
        t_cur is relative percentual progress
    """
    color_pallet = load_json("config/color.json", scale)
    colors = [hex2np(x) for x in color_pallet]
    time_ref = [0, .25, .5, .75, 1]
    if interpolation == 'linear':
        r,g,b = [np.interp(t_cur, time_ref, color) for color in colors]
    elif interpolation == 'poly':
        r_cs, g_cs, b_cs = [CubicSpline(time_ref, color) for color in colors]
        r, b, b = r_cs[t_cur], g_cs[t_cur], b_cs[t_cur]
    else:
        # fallback linear
        r, g, b = [np.interp(t_cur, time_ref, color) for color in colors]
    
    r /= 255
    g /= 255
    b /= 255
    return r,g,b


def get_sunrise_intensity(t_cur, interpolation='linear', gradient="exp") -> float:
    grad = load_json("config.gradient.json", gradient)
    time_ref = [0, .25, .5, .75, 1]

    if interpolation == 'linear':
        lum = np.interp(t_cur, time_ref, grad)
    elif interpolation == 'poly':
        cs = CubicSpline(time_ref, grad)
        lum = cs[t_cur]
    else:
        # fallback linear
        lum = np.interp(t_cur, time_ref, lum)
    return lum
