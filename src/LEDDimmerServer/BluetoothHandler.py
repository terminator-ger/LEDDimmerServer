import socket
import json
import logging
import simplejson

from LEDDimmerServer.DimmerBackend import DimmerBackend

class BluetoothHandler:
    def __init__(self, backend: DimmerBackend):
        super().__init__()
        self.backend = backend
        self.path = ""
        self.data_string = ""
    
    def _connect(self):
        self.adapter_addr = socket.BDADDR_ANY
        self.port = 3  # Normal port for rfcomm?

        s = socket.socket(socket.AF_BLUETOOTH, socket.SOCK_STREAM, socket.BTPROTO_RFCOMM)
        s.bind((self.adapter_addr, self.port))
        s.listen(1)
        try:
            print('Listening for connection...')
            self.client, address = s.accept()
            print(f'Connected to {address}')

            while True:
                size = self.client.recv(1)
                if size:
                    self.data_string = self.client.recv(size)
                    print(self.data_string)

        except Exception as e:
            print(f'Something went wrong: {e}')
            self.client.close()
            s.close()
        
    def response(self, code, message=None):
        '''Send a response with the given code and message.
        This method is used to send HTTP responses with a specific status code and optional message.
        '''
        codetable = {   
            200: "OK",
            201: "CREATED",  
            204: "NO_CONTENT",
            400: "BAD_REQUEST",         
            401: "UNAUTHORIZED",   
            403: "FORBIDDEN",
            404: "NOT_FOUND",       
            405: "METHOD_NOT_ALLOWED",
            500: "INTERNAL_SERVER_ERROR",
        }
        if code not in codetable:
            code = 500
            
        code_str = codetable[code]
        if code >= 400:
            logging.error("HTTP %d: %s", code, code_str)
        else:
            logging.info("HTTP %d: %s", code, code_str)

        self.client.send(code)
        self.client.send(code_str)
        self.client.send(message) 
        self.client.send('\n')
 
    def do_PUT(self):
        '''Handle PUT requests to control the LED dimmer.
        This method reads the request body, determines the action based on the URL path,    
        and calls the appropriate method on the backend.
        '''
        logging.debug("-- PUT")
        data_string = self.data_string
        
        if self.backend is None:
            raise RuntimeError("Backend not initialized!")

        if "/status" in self.path:
            self.response(200, "STATUS " + json.dumps(self.backend.get_status()))
        
        elif "/config" in self.path:
            self.response(200, "CONFIG " + json.dumps(self.backend.get_config()))
            
        elif "/toggle" in self.path:
            if self.backend.toggle():
                self.response(200, "TOGGLE ON")
            else:
                self.response(200, "TOGGLE OFF")
            
        elif "/on" in self.path:
            if self.backend.on():
                self.response(200, "ON" )
  
        elif "/off" in self.path:
            if self.backend.off():
                self.response(200, "OFF" )
                        
        elif "/incr" in self.path:
            if self.backend.incr():
                self.response(200, "INCR" )
            else:
                self.response(405, "INCR" )
                
        elif "/decr" in self.path:
            if self.backend.decr():
                self.response(200, "DECR")
            else:
                self.response(405, "DECR")
   
        elif "/wakeuptime" in self.path:
            if data_string is None or len(data_string) == 0:
                self.response(400, "PUT request to /wakeuptime without data")
                return
            
            data = simplejson.loads(data_string)
            
            if 'time' not in data.keys():
                self.response(400, "PUT request to /wakeuptime without 'time' in data")
                return
            
            if (isinstance(data['time'], str) and 
                data['time'].isdigit()):
                data['time'] = int(data['time'])
            elif isinstance(data['time'], str):
                self.response(400, "PUT request to /wakeuptime with 'time' not a digit")
                return
            
            wakeup_time = int(data['time'])
            success, returntime = self.backend.wakeuptime(wakeup_time)
            if success:
                self.response(200, f"WAKEUP {returntime}")

        elif "/sunrise" in self.path:
            success, wakeup_time = self.backend.sunrise()
            if success:
                self.response(200, f"SUNRISE {wakeup_time}")

            
        elif '/color' in self.path:
            if data_string is None or len(data_string) == 0:
                self.response(400, "PUT request to /color without data")
                return
 
            data = simplejson.loads(data_string)
            data = {k: [v_ for v_ in v.split(" ")] for k, v in data.items()}
            if self.backend.color(data):
                self.response(200, "COLOR")


        elif '/gradient' in self.path:
            if data_string is None or len(data_string) == 0:
                self.response(400, "PUT request to /gradient without data")
                return
 
            data = simplejson.loads(data_string)
            if self.backend.gradient(data):
                self.response(200, "GRADIENT")

        elif '/preset' in self.path:
            if self.backend.preset(data_string):
                self.response(200, "PRESET")

        elif '/default' in self.path:
            if self.backend.default(data_string):
                self.response(200, "DEFAULT")

        elif '/update_config' in self.path:
            if data_string is None or len(data_string) == 0:
                self.response(400, "UpdateConfig without data")
                return
            data = simplejson.loads(data_string)
            if self.backend.update_config(data):
                self.response(200, "UPDATE_CONFIG")
                return
            self.response(500, "UPDATE_CONFIG failed")
            return

                        
        elif '/update' in self.path:
            self.backend.update()
        else:
            self.response(404, "Unknown PUT request: " + self.path)
            return


