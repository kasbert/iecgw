#!/usr/bin/env python3

import sys
import os

from iecgw import IECGW,IECMessage,C64MemoryFile
from iecgw.codec import toPETSCII,fromIEC,toIEC,IOErrorMessage,fromPETSCII

class testserver: 
    def __init__(self):
        self.device_id = 0

    def handleMessage(self, msg):
        print ("SOCKET CMD", msg.cmd, "secondary", msg.secondary, 'data[',len(msg.data),']')
        if msg.cmd == ':':
            msg.cmd = 'status'
        func = getattr(self, msg.cmd, None) 
        return func(msg.secondary, msg.data)

    def I(self, secondary, data): # Initialize
        data = data.decode('latin1')
        print('INIT', repr(data))
        return IECMessage(b'I', self.device_id, b'')

    def P(self, secondary, data): # Parse dos command
        print('OPEN', repr(data), fromPETSCII(data))
        return

    def O(self, secondary, data):
        print('OPEN', repr(data))
        print('OPEN', repr(data), fromPETSCII(data))
        print('OPEN', repr(data), fromIEC(data))
        return

    def C(self, secondary, data): # Close
        return

    def R(self, secondary, data): # Read
        print('READ?', repr(data))
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

    def status(self, secondary, data): # Debug
        print('STATUS', secondary, repr(data))
        return

s = IECGW()
testserver = testserver()

import sys, os
import termios, fcntl
import select

fd = sys.stdin.fileno()
newattr = termios.tcgetattr(fd)
newattr[3] = newattr[3] & ~termios.ICANON
newattr[3] = newattr[3] & ~termios.ECHO
termios.tcsetattr(fd, termios.TCSANOW, newattr)

oldterm = termios.tcgetattr(fd)
oldflags = fcntl.fcntl(fd, fcntl.F_GETFL)
fcntl.fcntl(fd, fcntl.F_SETFL, oldflags | os.O_NONBLOCK)

print ("Type some stuff")
while True:
    inp, outp, err = select.select([sys.stdin, s.s], [], [])
    #print (repr (inp))
    if sys.stdin in inp:
        c = sys.stdin.read()
        print ("-", c)
        if c == 'o':
            s.iecSendMsg(IECMessage(b'o', 0, b'$')) # open hw device id 8
        if c == 't':
            s.iecSendMsg(IECMessage(b't', 0, b'')) # talk
        if c == 'c':
            s.iecSendMsg(IECMessage(b'c', 0, b'')) # close
        if c == 'q':
            break
    if s.s not in inp:
        continue
#while True:
    msg = s.iecReadMsg()
    if msg is None:
        print ("Out of data")
        break
    response = testserver.handleMessage(msg)
    if response is not None:
        s.iecSendMsg(response)


# Reset the terminal:
termios.tcsetattr(fd, termios.TCSAFLUSH, oldterm)
fcntl.fcntl(fd, fcntl.F_SETFL, oldflags)
s.close()