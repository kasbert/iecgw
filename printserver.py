#!/usr/bin/env python3

import sys
import time
from struct import unpack


from iecgw import IECGW,IECMessage
from iecgw.codec import toPETSCII,fromIEC,toIEC,IOErrorMessage,fromPETSCII

class PrintServer:
    def __init__(self):
        self.device_id = 4

    def handleMessage(self, msg):
        #print ("SOCKET CMD", msg.cmd, "secondary", msg.secondary, 'data[',len(msg.data),']')
        func = getattr(self, msg.cmd, None) 
        return func(msg.secondary, msg.data)

    def I(self, secondary, data): # Initialize
        data = data.decode('latin1')
        #print('INIT', repr(data))
        return IECMessage(b'I', self.device_id, b'')

    def P(self, secondary, data): # Parse dos command
        print('OPEN', repr(data), fromPETSCII(data))
        return

    def O(self, secondary, data):
        print('OPEN', repr(data), fromPETSCII(data))
        return

    def C(self, secondary, data): # Close
        return

    def R(self, secondary, data): # Read
        print('READ?')
        return IECMessage(b':', secondary, IOErrorMessage.ErrFileNotFound.value)
        #print('READ END')
        return IECMessage(b'E', secondary, data)
        #print('READ OK')
        return IECMessage(b'B', secondary, data)
 
    def W(self, secondary, data): # Write
        print ('WRITE', repr(data))
        return

    def D(self, secondary, data): # Debug
        data = data.decode('latin1')
        print('DEBUG', repr(data))
        return

while True:
    s = IECGW()
    printserver = PrintServer()

    try:
        while True:
            msg = s.iecReadMsg()
            if msg is None:
                print ("Out of data")
                break
            response = printserver.handleMessage(msg)
            if response is not None:
                s.iecSendMsg(response)
    except:
        print("Unexpected error:", sys.exc_info()[0])
        time.sleep(10)