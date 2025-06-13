import logging
from http.server import SimpleHTTPRequestHandler


class HTTPHandler(SimpleHTTPRequestHandler):
    def __init__(self, backend, *args, **kwargs):
        self.backend = backend
        super().__init__(*args, **kwargs)
    

    def do_PUT(self):
        '''Handle PUT requests to control the LED dimmer.
        This method reads the request body, determines the action based on the URL path,    
        and calls the appropriate method on the backend.
        '''
        logging.debug("-- PUT")
        length = int(self.headers["Content-Length"])
        #path = self.translate_path(self.path)
        data_string = self.rfile.read(length)
        logging.debug(data_string)
        
        if self.backend is None:
            raise RuntimeError("Backend not initialized!")

        if "/toggle" in self.path:
            if self.backend.toggle():
                self.send_response(200, "TOGGLE_OK")
                self.send_header("Content-type", "text/html")
                self.end_headers()
            
        elif "/on" in self.path:
            if self.backend.on():
                self.send_response(200, "ON_OK")
                self.send_header("Content-type", "text/html")
                self.end_headers()
  
        elif "/off" in self.path:
            if self.backend.off():
                self.send_response(200, "OFF_OK")
                self.send_header("Content-type", "text/html")
                self.end_headers()
                #self.wfile.write(b"")
                        
        elif "/incr" in self.path:
            if self.backend.incr():
                self.send_response(200, "INCR_OK")
                self.send_header("Content-type", "text/html")
                self.end_headers()
                #self.wfile.write(b"")
                
        elif "/decr" in self.path:
            if self.backend.decr():
                self.send_response(200, "INCR_OK")
                self.send_header("Content-type", "text/html")
                self.end_headers()
                #self.wfile.write("")
   
        elif "/wakeuptime" in self.path:
            success, returntime = self.backend.wakeuptime(data_string)
            if success:
                self.send_response(200, 'WAKEUP_OK')
                self.send_header("Content-type", "text/html")
                self.end_headers()
                self.wfile.write(returntime)

        elif "/sunrise" in self.path:
            success, wakeup_time = self.backend.sunrise()
            if success:
                self.send_response(200, "SUNRISE_OK")
                self.send_header("Content-type", "text/html")
                self.end_headers()
                self.wfile.write(f"{wakeup_time}")

            
        elif '/color' in self.path:
            if self.backend.color(data_string):
                self.send_response(200, "COLOR_OK")
                self.send_header("Content-type", "text/html")
                self.end_headers()
                #self.wfile.write("")

        elif '/gradient' in self.path:
            if self.backend.gradient(data_string):
                self.send_response(200, "GRADIENT_OK")
                self.send_header("Content-type", "text/html")
                self.end_headers()

        elif '/preset' in self.path:
            if self.backend.preset(data_string):
                self.send_response(200, "PRESET_OK")
                self.send_header("Content-type", "text/html")
                self.end_headers()

        elif '/default' in self.path:
            if self.backend.default(data_string):
                self.send_response(200, "DEFAULT_OK")
                self.send_header("Content-type", "text/html")
                self.end_headers()
            
        elif '/update' in self.path:
            self.backend.update()
        else:
            logging.error("Unknown PUT request: %s", self.path)
            self.send_response(404, "NOT_FOUND")
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(b"Unknown PUT request")                


