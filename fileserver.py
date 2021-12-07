#!/usr/bin/env python3

import sys
import time
from struct import unpack
import argparse
import os
import logging

from iecgw import MenuNode,DirNode,CSDBNode,FileNode,D64Node,ZipNode,IECGW,IECMessage,C64MemoryFile
from iecgw.codec import toPETSCII,fromIEC,fromPETSCII,toIEC,IOErrorMessage,packDir,fileEntry

debug = True

csdbNode = CSDBNode(False, 'https://csdb.dk/')
csdbOneFileNode = CSDBNode(False, 'https://csdb.dk/toplist.php?type=release&subtype=%282%29')
csdbDemosNode = CSDBNode(False, 'https://csdb.dk/toplist.php?type=release&subtype=%281%29')

class FileServer:
    def __init__(self, files):
        self.openFiles = [None for i in range(16)]
        self.device_id = 8
        elems = [
            { 'size': 0, 'name': b'CSDB ONEFILE', 'extension': 'DIR', 'node': csdbOneFileNode},
            { 'size': 0, 'name': b'CSDB DEMOS', 'extension': 'DIR', 'node': csdbDemosNode},
        ]
        # { 'size': 0, 'name': b'CSDB.DK', 'extension': 'DIR', 'node': csdbNode},
        for filepath in files:
            size = int((os.path.getsize(filepath) + 255) / 256)
            entry = fileEntry(size, filepath, [])
            entry['name'] = toPETSCII(os.path.basename(filepath))
            if os.path.isdir(filepath):
                entry['extension'] = 'DIR'
            if entry['extension'] == 'D64':
                entry['node'] = D64Node(False, filepath, entry['real_name'])
            elif entry['extension'] == 'ZIP':
                entry['node'] = ZipNode(False, filepath, entry['real_name'])
            elif entry['extension'] == 'DIR':
                entry['node'] = DirNode(False, filepath)
            else:
                entry['node'] = FileNode(False, filepath)
            logging.info('ENTRY %s', entry)
            elems.insert(0, entry)
        self.current = MenuNode(False, elems)
        self.current.start()

    def handleMessage(self, msg):
        logging.info("SOCKET CMD %s secondary %s data[%d] current %s", msg.cmd, msg.secondary, len(msg.data), self.current)
        func = getattr(self, msg.cmd, None)
        return func(msg.secondary & 0xf, msg.data)

    def cdTop(self):
        while self.current.parent:
            self.current.close()
            self.current = self.current.parent

    def doCd(self, name):
        logging.info('CD %s', repr(name))
        if name == b'CD//':
            self.cdTop()
            return
        if name.startswith(b'/Q=') or name.startswith(b'/q='):
            self.cdTop()
            if name[3:].decode('latin1').isnumeric():
                url = b'https://csdb.dk/release/?id=' + name[3:]
            else:
                url = b'https://csdb.dk/search/?search=' + name[3:]
            logging.info('CSDB SEARCH %s', url)
            node = CSDBNode(self.current, url.decode('latin1'))
            if not node.start():
                return
            self.current = node
            return
        newNode = self.current.cd(name)
        if newNode is None:
            logging.error("ERROR in cd %s", repr(name))
            return
        self.current = newNode
        #ret = IOErrorMessage.ErrOK.value
        # dirdata = packDir(self.current.title(), self.current.list(), self.current.free())
        # self.openFiles[0] C64MemoryFile(dirdata, b'$')
        logging.info("CWD %s", self.current.cwd())

    def doLoad(self, name):
        if self.openFiles[0] is not None:
            self.openFiles[0].close()
        if name == b'$':
            logging.info("LOAD DIR %s", self.current.cwd())
            dirdata = packDir(self.current.title(), self.current.list(), self.current.free())
            self.openFiles[0] = C64MemoryFile(dirdata, b'$')
            return
        elif name == b'CD//' or self.current.isdir(name) or name.startswith(b'/Q=') or name.startswith(b'/q='):
            logging.info("LOAD CD %s %s", self.current.cwd(), name)
            self.doCd(name)
            dirdata = packDir(self.current.title(), self.current.list(), self.current.free())
            self.openFiles[0] = C64MemoryFile(dirdata, b'$')
            return
        else:
            logging.info("JUST LOAD %s %s", self.current.cwd(), name)
            self.openFiles[0] = self.current.load(name)
        logging.info("LOAD RESULT %s", repr(self.openFiles[0]))
        if self.openFiles[0] == None:
            self.openFiles[15] = C64MemoryFile(b'62, FIXME FILE NOT FOUND OR SOMETHING,00,00\r', b'status')
        else:
            self.openFiles[15] = C64MemoryFile(b'00, OK,00,00\r', b'status')

    def doSave(self, name):
        global openFiles
        if self.openFiles[1] is not None:
            self.openFiles[1].close()
        logging.info("SAVE %s", name)
        self.openFiles[1] = self.current.save(name)
        logging.info("SAVE RESULT %s", self.openFiles[1])
        if self.openFiles[1] == None:
            self.openFiles[15] = C64MemoryFile(b'62, FIXME FILE NOT FOUND OR SOMETHING,00,00\r', b'status')
        else:
            self.openFiles[15] = C64MemoryFile(b'00, OK,00,00\r', b'status')

    def doOpen(self, channel, name):
        if name.startswith(b'0:'):
            name = name[2:]
        if channel == 15: # CONTROL
            if name == b'CD//':
                self.doCd(name)
            elif name.startswith(b'CD:'):
                name = name.rstrip(b'\r')
                self.doCd(name[3:])
            elif name.startswith(b'M-W'):
                address, size = unpack('<HB', name[3:6])
                logging.warning('MEMORY WRITE %x %d %d %s', address, size, len(name[6:]), repr(name[6:]))
            elif name.startswith(b'M-E'):
                address = unpack('<H', name[3:5])
                logging.warning('MEMORY EXECUTE %x', address)
        else: # channels 2-14
            # TODO parse dos command
            elems = fromIEC(name).decode('latin1').split(',', 3)
            logging.info('OPEN CHANNEL %s %s', channel, elems)
            # FIXME write, too
            self.openFiles[channel] = self.current.load(toIEC(elems[0]))
            logging.info("READ SEQ %s", repr(self.openFiles[channel]))
            if self.openFiles[channel] == None:
                self.openFiles[15] = C64MemoryFile(b'62, FIXME FILE NOT FOUND OR SOMETHING,00,00\r', b'status')
            else:
                self.openFiles[15] = C64MemoryFile(b'00, OK,00,00\r', b'status')

    def I(self, secondary, data): # Initialize
        data = data.decode('latin1')
        logging.warning('INIT %s', repr(data))
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
        self.current.close()
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
            logging.error('READ ERROR')
            return IECMessage(b':', secondary, IOErrorMessage.ErrFileNotFound.value)
        buflen = 254
        data = self.openFiles[secondary].read(buflen)
        if len(data) < buflen:
            # End of file
            self.openFiles[secondary].close()
            self.openFiles[secondary] = None
            #logging.info('READ END')
            return IECMessage(b'E', secondary, data)
        #logging.info('READ OK')
        return IECMessage(b'B', secondary, data)

    def W(self, secondary, data): # Write
        if self.openFiles[secondary] is None:
            if secondary == 15:
                self.doOpen(secondary, data)
                return
            logging.error('WRITE ERROR')
            return
        #logging.info ('WRITE', openFiles[secondary])
        self.openFiles[secondary].write(data)

    def D(self, secondary, data): # Debug
        data = data.decode('latin1')
        logging.warning('DEBUG %s', repr(data))

def main(argv):
    parser = argparse.ArgumentParser(description='IECGW fileserver')
    parser.add_argument('--debug', '-d', action='count', default=0)
    parser.add_argument('files', nargs="*", help="Directories to serve")
    args = parser.parse_args()
    logging.basicConfig(level=(30 - 10 * args.debug))

    while True:
        s = IECGW()
        fileserver = FileServer(args.files)

        try:
            while True:
                msg = s.iecReadMsg()
                if msg is None:
                    logging.error("Out of data")
                    break
                response = fileserver.handleMessage(msg)
                if response is not None:
                    s.iecSendMsg(response)
        except Exception as e:
            logging.exception("Unexpected error")
            time.sleep(10)

if __name__ == "__main__":
    main(sys.argv)
