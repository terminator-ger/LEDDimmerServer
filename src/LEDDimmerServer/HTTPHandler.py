import logging
from http.server import SimpleHTTPRequestHandler


class HTTPHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.backend = None
    
    def set_backend(self, backend):
        '''Set the backend for the HTTP handler.
        This method is used to inject the DimmerBackend instance into the HTTP handler. 
        '''
        from LEDDimmerServer.DimmerBackend import DimmerBackend
        self.backend : DimmerBackend = backend

    def do_PUT(self):
        '''Handle PUT requests to control the LED dimmer.
        This method reads the request body, determines the action based on the URL path,    
        and calls the appropriate method on the backend.
        '''
        logging.debug("-- PUT")
        length = int(self.headers["Content-Length"])
        path = self.translate_path(self.path)
        data_string = self.rfile.read(length)
        logging.debug(data_string)
        
        if self.backend is None:
            raise RuntimeError("Backend not initialized!")

        if "/toggle" in self.path:
            self.backend.toggle()

        if "/on" in self.path:
            self.backend.on()
  
        if "/off" in path:
            self.backend.off()
                        
        if "/incr" in path:
            self.backend.incr()

        if "/decr" in path:
            self.backend.decr()
   
        if "/wakeuptime" in path:
            self.backend.wakeuptime(data_string)

        if "/sunrise" in path:
            self.backend.sunrise()
            
        if '/color' in path:
            self.backend.color(data_string)

        if '/gradient' in path:
            self.backend.gradient(data_string)

        if '/preset' in path:
            self.backend.preset(data_string)

        if '/default' in path:
            self.backend.default(data_string)
            
        if '/update' in path:
            self.backend.update()


