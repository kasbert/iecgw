#!/usr/bin/env python3

import sys
import os
from struct import pack,unpack


from iecgw import MenuNode, DirNode, CSDBNode, ZipNode,D64Node,IECGW,C64MemoryFile
from iecgw.codec import toPETSCII,fromIEC,toIEC,IOErrorMessage

# TODO parse files from command line
global topNode
#topNode = DirNode('../', 'warez')
topNode = MenuNode([
 { 'size': 0, 'name': b'FILES', 'extension': 'DIR', 'node': DirNode('../', 'warez')},
 { 'size': 0, 'name': b'CSDB.DK', 'extension': 'DIR', 'node': CSDBNode()}
])
#topNode = CSDBNode('/release/?id=139278')

global openFiles
openFiles = [None for i in range(16)] 


def loadDir():
    global topNode
    title = topNode.title()
    free = topNode.free()

    print ("TITLE", title, topNode)
    lname = b'\x12"' + title
    while len(lname) < 18:
        lname += b' '
    lname += b'" 12 4A'
 
    basicPtr = 0x0401
    basicPtr += len(lname) + 5

    dirdata = bytearray()
    dirdata.extend(pack('<HHH', 0x401, basicPtr, 0))
    dirdata.extend(lname)
    dirdata.append(0)

    for entry in topNode.list():
        name = entry['name']
        size = entry['size']
        extension = entry['extension']
        if extension == 'D64' or extension == 'ZIP':
            extension = 'DIR'
            size = 0
        if extension == '':
            extension = 'REL'
        lname = bytearray()
        lname.extend(b'"')
        lname.extend(name)
        lname.extend(b'" ')
        while len(lname) < 19:
            lname.append(ord(' '))
        if size < 1000:
            lname.insert(0, ord(' '))
        if size < 100:
            lname.insert(0, ord(' '))
        if size < 10:
            lname.insert(0, ord(' '))
        lname.extend(extension.encode('latin1'))
        while len(lname) < 27:
            lname.append(ord(' '))

        basicPtr += len(lname) + 5
        dirdata.extend(pack('<HH', basicPtr, size))
        dirdata.extend(lname)
        dirdata.append(0)
        if len(dirdata) > 32000:
            break

    lname = 'blocks free'
    basicPtr += len(lname) + 5
    dirdata.extend(pack('<HH', basicPtr, free))
    dirdata.extend(toPETSCII(lname))
    dirdata.append(0)

    dirdata.append(0)
    dirdata.append(0)
    #print ('DIR DATA', repr(dirdata))
    return C64MemoryFile(dirdata, b'$')

def doCd(name):
    global topNode
    print ('CD', repr(name))
    newNode = topNode.cd(name)
    if newNode is None:
        print ("ERROR in cd ", repr(name))
        return
    topNode = newNode
    #ret = IOErrorMessage.ErrOK.value
    #openFiles[0] = loadDir()
    print ("CWD", topNode.cwd())

def doLoad(s, name):
    global topNode
    global openFiles
    if openFiles[0] is not None:
        openFiles[0].close()
    if name == b'$':
        print ("LOAD DIR", topNode.cwd())
        openFiles[0] = loadDir()
        return
    elif topNode.isdir(name):
        print ("LOAD CD", topNode.cwd(), name)
        doCd(name)
        openFiles[0] = loadDir()
        return
    else:
        print ("JUST LOAD", topNode.cwd(), name)
        openFiles[0] = topNode.load(name)
    print ("LOAD RESULT", repr(openFiles[0]))
    if openFiles[0] == None:
        openFiles[15] = C64MemoryFile(b'62, FIXME FILE NOT FOUND OR SOMETHING,00,00\r', b'status')
    else:
        openFiles[15] = C64MemoryFile(b'00, OK,00,00\r', b'status')

def doSave(s, name):
    global topNode
    global openFiles
    if openFiles[1] is not None:
        openFiles[1].close()
    print ("SAVE", name)
    openFiles[1] = topNode.save(name)
    print ("SAVE RESULT", openFiles[1])
    if openFiles[1] == None:
        openFiles[15] = C64MemoryFile(b'62, FIXME FILE NOT FOUND OR SOMETHING,00,00\r', b'status')
    else:
        openFiles[15] = C64MemoryFile(b'00, OK,00,00\r', b'status')

def doOpen(s, channel, name):
    global topNode
    if name.startswith(b'0:'):
        name = name[2:]
    if channel == 15: # CONTROL
        if name.startswith(b'CD:'):
            if name == b'CD:_':
                doCd(b'..')
            else:
                doCd(name[3:])
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
        openFiles[channel] = topNode.load(toIEC(elems[0]))
        print ("READ SEQ", repr(openFiles[channel]))
        if openFiles[channel] == None:
            openFiles[15] = C64MemoryFile(b'62, FIXME FILE NOT FOUND OR SOMETHING,00,00\r', b'status')
        else:
            openFiles[15] = C64MemoryFile(b'00, OK,00,00\r', b'status')

def doCmd(s, cmd, secondary, data):
    global topNode
    global openFiles
    print ("SOCKET CMD", cmd, "secondary", secondary, 'data[',len(data),']')
    if cmd == 'I': # Initialize
        data = data.decode('latin1')
        print('INIT', repr(data))
        s.iecSendMsg(b'I', 8, b'') # hw device id 8
        return

    elif cmd == 'P': # Parse dos command
        doOpen(s, secondary, data)
        return

    elif cmd == 'O':
        if secondary == 0: # LOAD
            doLoad(s, data)
        elif secondary == 1: # SAVE
            doSave(s, data)
        else:
            doOpen(s, secondary, data)
        return

    elif cmd == 'C':
        if openFiles[secondary] is not None:
            openFiles[secondary].close()
        openFiles[secondary] = None
        topNode.close()
        return

    elif cmd == 'T': # Talk not used
        if openFiles[secondary] is None:
            s.iecSendMsg(b'>', secondary, IOErrorMessage.ErrFileNotFound.value)
        else:
            s.iecSendMsg(b'>', secondary, IOErrorMessage.ErrOK.value)
        return

    elif cmd == 'L': # Listen not used
        if openFiles[secondary] is None:
            s.iecSendMsg(b'>', secondary, IOErrorMessage.ErrDiskFullOrDirectoryFull.value)
        else:
            s.iecSendMsg(b'>', secondary, IOErrorMessage.ErrOK.value)
        return

    elif cmd == 'R': # Read
        if secondary == 15 and openFiles[15] is None:
            # Channel status is always available
            openFiles[15] = C64MemoryFile(b'00, OK,00,00\r', b'status')
        if openFiles[secondary] is None:
            s.iecSendMsg(b':', secondary, IOErrorMessage.ErrFileNotFound.value)
            print('READ ERROR')
            return
        buflen = 254
        data = openFiles[secondary].read(buflen)
        if len(data) < buflen:
            # End of file
            s.iecSendMsg(b'E', secondary, data)
            openFiles[secondary].close()
            openFiles[secondary] = None
            print('READ END')
        else:
            s.iecSendMsg(b'B', secondary, data)
            #print('READ OK')

    elif cmd == 'W': # Write
        if openFiles[secondary] is None:
            print('WRITE ERROR')
            return
        #print ('WRITE', openFiles[secondary])
        openFiles[secondary].write(data)

    elif cmd == 'D': # Debug
        data = data.decode('latin1')
        print('DEBUG', repr(data))

s = IECGW()

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
        if c == 'x':
            s.iecSendMsg(b'x', 8, b'$') # hw device id 8
        if c == 'q':
            break

#while True:
    if s.s not in inp:
        continue
    data = s.iecRead(1)
    if data == b'':
        print ("Out of data")
        break
    cmd = chr(data[0])
    data = s.iecRead(1)
    if data == b'':
        print ("Out of data")
        break
    secondary = data[0]
    data = s.iecRead(1)
    if data == b'':
        print ("Out of data")
        break
    size = data[0]
    data = b''
    if size > 0:
        # FIXME read fragmented
        data = s.iecRead(size)
    doCmd(s, cmd, secondary, data)


# Reset the terminal:
termios.tcsetattr(fd, termios.TCSAFLUSH, oldterm)
fcntl.fcntl(fd, fcntl.F_SETFL, oldflags)
s.close()