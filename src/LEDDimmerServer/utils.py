import os
from pathlib import Path
import ssl
ROOT_DIR = Path(os.path.abspath(__file__)).parent.parent.parent.absolute()

def get_ssl_context(certfile, keyfile):
    context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
    context.load_cert_chain(certfile, keyfile)
    context.set_ciphers("@SECLEVEL=1:ALL")
    return context
 