#!/usr/bin/env python3

import sys
import time
from struct import unpack


from iecgw import MenuNode, DirNode, CSDBNode, ZipNode,D64Node,IECGW,IECMessage,C64MemoryFile
from iecgw.codec import toPETSCII,fromIEC,toIEC,IOErrorMessage,packDir

# TODO parse files from command line
global topNode
#topNode = DirNode('../', 'warez')

def dirNode():
    return DirNode('../', 'warez')

def csdbNode():
    return CSDBNode()

topNode = MenuNode([
 { 'size': 0, 'name': b'FILES', 'extension': 'DIR', 'node': dirNode},
 { 'size': 0, 'name': b'CSDB.DK', 'extension': 'DIR', 'node': csdbNode}
])

class FileServer:
    def __init__(self):
        self.openFiles = [None for i in range(16)] 
        self.device_id = 8

    def handleMessage(self, msg):
        print ("SOCKET CMD", msg.cmd, "secondary", msg.secondary, 'data[',len(msg.data),']')
        func = getattr(self, msg.cmd, None) 
        return func(msg.secondary & 0xf, msg.data)

    def doCd(self, name):
        global topNode
        print ('CD', repr(name))
        newNode = topNode.cd(name)
        if newNode is None:
            print ("ERROR in cd ", repr(name))
            return
        topNode = newNode
        #ret = IOErrorMessage.ErrOK.value
        # dirdata = packDir(topNode.title(), topNode.list(), topNode.free())
        # self.openFiles[0] C64MemoryFile(dirdata, b'$')
        print ("CWD", topNode.cwd())

    def doLoad(self, name):
        global topNode
        if self.openFiles[0] is not None:
            self.openFiles[0].close()
        if name == b'$':
            print ("LOAD DIR", topNode.cwd())
            dirdata = packDir(topNode.title(), topNode.list(), topNode.free())
            self.openFiles[0] = C64MemoryFile(dirdata, b'$')
            return
        elif topNode.isdir(name):
            print ("LOAD CD", topNode.cwd(), name)
            self.doCd(name)
            dirdata = packDir(topNode.title(), topNode.list(), topNode.free())
            self.openFiles[0] = C64MemoryFile(dirdata, b'$')
            return
        else:
            print ("JUST LOAD", topNode.cwd(), name)
            self.openFiles[0] = topNode.load(name)
        print ("LOAD RESULT", repr(self.openFiles[0]))
        if self.openFiles[0] == None:
            self.openFiles[15] = C64MemoryFile(b'62, FIXME FILE NOT FOUND OR SOMETHING,00,00\r', b'status')
        else:
            self.openFiles[15] = C64MemoryFile(b'00, OK,00,00\r', b'status')

    def doSave(self, name):
        global topNode
        global openFiles
        if self.openFiles[1] is not None:
            self.openFiles[1].close()
        print ("SAVE", name)
        self.openFiles[1] = topNode.save(name)
        print ("SAVE RESULT", self.openFiles[1])
        if self.openFiles[1] == None:
            self.openFiles[15] = C64MemoryFile(b'62, FIXME FILE NOT FOUND OR SOMETHING,00,00\r', b'status')
        else:
            self.openFiles[15] = C64MemoryFile(b'00, OK,00,00\r', b'status')

    def doOpen(self, channel, name):
        global topNode
        if name.startswith(b'0:'):
            name = name[2:]
        if channel == 15: # CONTROL
            if name.startswith(b'CD:'):
                name = name.rstrip(b'\r')
                if name == b'CD:_':
                    self.doCd(b'..')
                else:
                    self.doCd(name[3:])
            if name.startswith(b'M-W'):
                address, size = unpack('<HB', name[3:6])
                print ('MEMORY WRITE', address, size, len(name[6:]), repr(name[6:]))
            if name.startswith(b'M-E'):
                address = unpack('<H', name[3:5])
                print ('MEMORY EXECUTE', address)
        else: # channels 2-14
            # TODO parse dos command
            elems = fromIEC(name).decode('latin1').split(',', 3)
            print ('OPEN CHANNEL', channel, elems)
            # FIXME write, too
            self.openFiles[channel] = topNode.load(toIEC(elems[0]))
            print ("READ SEQ", repr(self.openFiles[channel]))
            if self.openFiles[channel] == None:
                self.openFiles[15] = C64MemoryFile(b'62, FIXME FILE NOT FOUND OR SOMETHING,00,00\r', b'status')
            else:
                self.openFiles[15] = C64MemoryFile(b'00, OK,00,00\r', b'status')

    def I(self, secondary, data): # Initialize
        data = data.decode('latin1')
        print('INIT', repr(data))
        return IECMessage(b'I', self.device_id, b'') # hw device id 8

    def P(self, secondary, data): # Parse dos command
        if secondary == 0: # LOAD
            self.doLoad(data)
        elif secondary == 1: # SAVE
            self.doSave(data)
        else:
            self.doOpen(secondary, data)

    def O(self, secondary, data):
        if secondary == 0: # LOAD
            self.doLoad(data)
        elif secondary == 1: # SAVE
            self.doSave(data)
        else:
            self.doOpen(secondary, data)
        return

    def C(self, secondary, data): # Close
        if self.openFiles[secondary] is not None:
            self.openFiles[secondary].close()
        self.openFiles[secondary] = None
        topNode.close()
        return

    def T(self, secondary, data): # Talk not used
        if self.openFiles[secondary] is None:
            return IECMessage(b'>', secondary, IOErrorMessage.ErrFileNotFound.value)
        return IECMessage(b'>', secondary, IOErrorMessage.ErrOK.value)

    def L(self, secondary, data): # Listen not used
        if self.openFiles[secondary] is None:
            return IECMessage(b'>', secondary, IOErrorMessage.ErrDiskFullOrDirectoryFull.value)
        return IECMessage(b'>', secondary, IOErrorMessage.ErrOK.value)

    def R(self, secondary, data): # Read
        if secondary == 15 and self.openFiles[15] is None:
            # Channel status is always available
            self.openFiles[15] = C64MemoryFile(b'00, OK,00,00\r', b'status')
        if self.openFiles[secondary] is None:
            print('READ ERROR')
            return IECMessage(b':', secondary, IOErrorMessage.ErrFileNotFound.value)
        buflen = 254
        data = self.openFiles[secondary].read(buflen)
        if len(data) < buflen:
            # End of file
            self.openFiles[secondary].close()
            self.openFiles[secondary] = None
            #print('READ END')
            return IECMessage(b'E', secondary, data)
        #print('READ OK')
        return IECMessage(b'B', secondary, data)
 
    def W(self, secondary, data): # Write
        if self.openFiles[secondary] is None:
            if secondary == 15:
                self.doOpen(secondary, data)
                return
            print('WRITE ERROR')
            return
        #print ('WRITE', openFiles[secondary])
        self.openFiles[secondary].write(data)

    def D(self, secondary, data): # Debug
        data = data.decode('latin1')
        print('DEBUG', repr(data))

while True:
    s = IECGW()
    fileserver = FileServer()

    try:
        while True:
            msg = s.iecReadMsg()
            if msg is None:
                print ("Out of data")
                break
            response = fileserver.handleMessage(msg)
            if response is not None:
                s.iecSendMsg(response)
    except:
        print("Unexpected error:", sys.exc_info()[0])
        time.sleep(10)