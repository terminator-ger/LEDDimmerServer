import os
from pathlib import Path
import ssl
from typing import Tuple


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


import traceback
import threading 
import os


class GlobalExceptionWatcher(object):
    def _store_excepthook(self, args):
        '''
        Uses as an exception handlers which stores any uncaught exceptions.
        '''
        self.__org_hook(args)
        formated_exc = traceback.format_exception(args.exc_type, args.exc_value, args.exc_traceback)
        self._exceptions.append('\n'.join(formated_exc))
        return formated_exc

    def __enter__(self):
        '''
        Register us to the hook.
        '''
        self._exceptions = []
        self.__org_hook = threading.excepthook
        threading.excepthook = self._store_excepthook

    def __exit__(self, type, value, traceback):
        '''
        Remove us from the hook, assure no exception were thrown.
        '''
        threading.excepthook = self.__org_hook
        if len(self._exceptions) != 0:
            tracebacks = os.linesep.join(self._exceptions)
            raise Exception(f'Exceptions in other threads: {tracebacks}')