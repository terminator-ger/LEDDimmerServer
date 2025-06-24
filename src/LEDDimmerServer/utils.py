import os
from pathlib import Path
import ssl
from typing import Tuple

ROOT_DIR = Path(os.path.abspath(__file__)).parent.parent.parent.absolute()

def get_ssl_context(certfile, keyfile):
    context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
    context.load_cert_chain(certfile, keyfile)
    context.set_ciphers("@SECLEVEL=1:ALL")
    return context
 

def add_float_tuple(rgb: Tuple[float,float,float], val: float) -> Tuple[float,float,float]:
    """
    """ 
    if any([(x + val) > 1.0 for x in rgb]):
        #scale by largest value
        return (rgb[0] + (1-max(rgb)), rgb[1] + (1-max(rgb)), rgb[2] + (1-max(rgb)))

    if any([(x + val) < 0.0 for x in rgb]):
        # scale by least value
        return (rgb[0] + min(rgb), rgb[1] + min(rgb), rgb[2] + min(rgb))
    
    return (rgb[0] + val, rgb[1] + val, rgb[2] + val)
