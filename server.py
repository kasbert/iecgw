#!/usr/bin/env python3

import socket
import sys
import os
import io
from stat import *
from enum import Enum
from struct import pack,unpack

import zipfile
import tempfile
import shutil

import cbmcodecs
from d64 import DiskImage
from cbm_files import ProgramFile
from d64.dos_path import DOSPath

HOST = '127.0.0.1'  # The server's hostname or IP address
PORT = 1541        # The port used by the server

class IOErrorMessage(Enum):
  ErrOK = 0
  ErrFilesScratched = 1 # Files scratched response, not an error condition.

  ErrBlockHeaderNotFound = 20
  ErrSyncCharNotFound = 21
  ErrDataBlockNotFound = 22
  ErrChecksumInData = 23
  ErrByteDecoding = 24
  ErrWriteVerify = 25
  ErrWriteProtectOn = 26
  ErrChecksumInHeader = 27
  ErrDataExtendsNextBlock = 28
  ErrDiskIdMismatch = 29
  ErrSyntaxError = 30
  ErrInvalidCommand = 31
  ErrLongLine = 32
  ErrInvalidFilename = 33
  ErrNoFileGiven = 34 # The file name was left out of a command or the DOS does not
                  # recognize it as such.
  # Typically, a colon or equal character has been left out of the command

  ErrCommandNotFound = 39  # This error may result if the command sent to
                           # command channel (secondary address 15) is
                           # unrecognizedby the DOS.
  ErrRecordNotPresent = 50
  ErrOverflowInRecord = 51
  ErrFileTooLarge = 52

  ErrFileOpenForWrite = 60
  ErrFileNotOpen = 61
  ErrFileNotFound = 62
  ErrFileExists = 63
  ErrFileTypeMismatch = 64
  ErrNoBlock = 65
  ErrIllegalTrackOrSector = 66
  ErrIllegalSystemTrackOrSector = 67

  ErrNoChannelAvailable = 70
  ErrDirectoryError = 71
  ErrDiskFullOrDirectoryFull = 72
  ErrIntro = 73           # power up message or write attempt with DOS mismatch
  ErrDriveNotReady = 74   # typically in this emulation could also mean: not
                      # supported on this file system.
  ErrSerialComm = 97 # something went sideways with serial communication to
                      # the file server.
  ErrNotImplemented = 98 # The command or specific operation is not yet
                          # implemented in this device.
  ErrUnknownError = 99
  ErrCount =100 # Not really

class IECGW:
    def __init__(self, host = HOST, port = PORT):
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.s.connect((host, port))

    def iecSend(self, data):
        self.s.sendall(data)
        print('>', repr(data))

    def iecSendMsg(self, cmd, secondary, data):
        header = pack('cBB', cmd, secondary, len(data))
        self.s.sendall(header)
        if len(data) > 0:
            self.s.sendall(data)
        print('>', repr(header), repr(data))

    def iecRead(self, length):
        # TODO receive all fragments
        data = self.s.recv(length)
        print('<', repr(data))
        return data

    def iecReadUntil(self, char):
        buf = bytearray()
        while True:
            data = self.s.recv(1)
            if len(data) == 0:
                break
            buf.append(data[0])
            if data[0] == ord(char):
                break
        print('<', repr(buf))
        return buf

def toIEC(s):
    buf = bytearray()
    for c in s:
        #c = ord(c)
        if c >= 'a' and c <= 'z':
            buf.append(ord(c) - 0x20)
        elif c >= 'A' and c <= 'Z':
            buf.append(ord(c) + 0x20)
        else:
            buf.append(ord(c))
    return buf

def fromIEC(b):
    buf = bytearray()
    for c2 in b:
        c = chr(c2)
        #if type(c2) == int:
        #    c = chr(c2)
        #else:
        #    c = c2
        #    c2 = ord(c2)
        if c >= 'a' and c <= 'z':
            buf.append(c2 - 0x20)
        elif c >= 'A' and c <= 'Z':
            buf.append(c2 + 0x20)
        else:
            buf.append(c2)
    return buf

def toPETSCII(s):
    buf = bytearray()
    for c in s:
        c2 = ord(c)
        if c2 >= 0x40 and c2 <= 0x5f:
            buf.append(ord(c) + 0x80)
        elif c >= 'a' and c <= 'z':
            buf.append(ord(c) - 0x20)
        elif c >= 'A' and c <= 'Z':
            buf.append(ord(c) + 0x20)
        else:
            buf.append(ord(c))
    return buf

def fromPETSCII(b):
    buf = bytearray()
    for c2 in b:
        c = chr(c2)
        #if type(c2) == int:
        #    c = chr(c2)
        #else:
        #    c = c2
        #    c2 = ord(c2)
        if c >= 'a' and c <= 'z':
            buf.append(c2 - 0x20)
        elif c >= 'A' and c <= 'Z':
            buf.append(c2 + 0x20)
        elif c2 >= 0xc0 and c2 <= 0xdf:
            buf.append(c2 - 0x60)
        else:
            buf.append(c2)
    return buf

class C64File:
    def __init__(self, fh, filesize, filename):
        self.fh = fh
        self.filesize = filesize
        self.filename = filename

    def read(self, buflen):
        return self.fh.read(buflen)

    def write(self, data):
        return self.fh.write(data)

    def close(self):
        self.fh.close()

class C64MemoryFile(C64File):
    def __init__(self, data, filename):
        self.fh = io.BytesIO(data)
        self.filesize = len(data)
        self.filename = filename

class DirNode:
    def __init__(self, cwd, name):
        self.path = os.path.normpath(cwd + '/' + name)
        self.subdir = False
        self.wfile = None
        self.rfile = None
        self.mapFiles()

    def mapFiles(self):
        self.files = []
        for entry in sorted(os.scandir(self.path), key=lambda x: x.name.lower()):
            if not entry.name.startswith('.'): # and entry.is_file():
                size = int((entry.stat().st_size + 255) / 256)
                if size > 65535:
                    size = 65535
                name = entry.name
                extension = ''
                if name.endswith('.prg') or name.endswith('.PRG'):
                    extension = 'PRG'
                    name = name[0:-4]
                if name.endswith('.d64') or name.endswith('.D64'):
                    extension = 'D64'
                    name = name[0:-4]
                if name.endswith('.zip') or name.endswith('.ZIP'):
                    extension = 'ZIP'
                    name = name[0:-4]
                if S_ISDIR(entry.stat().st_mode):
                    extension = 'DIR' 
                if len(name) > 16:
                    name = name[0:16]
                    # FIXME how about similar names ?
                name = toPETSCII(name)
                entry = { 'size': size, 'name': name, 'extension': extension, 'real_name': entry.name}
                print('ENTRY', entry)
                self.files.append(entry)

    def matchFile(self, iecname):
        for entry in self.files:
            #print('MATCH', repr(entry['name']), iecname)
            if DOSPath.wildcard_match(entry['name'], entry['extension'], iecname):
                #print('MATCH OK', repr(iecname), entry)
                return entry
        iecname = fromPETSCII(iecname)
        for entry in self.files:
            #print('MATCH', repr(entry['name']), iecname)
            if DOSPath.wildcard_match(entry['name'], entry['extension'], iecname):
                #print('MATCH OK', repr(iecname), entry)
                return entry
        return None

    def cwd(self):
        if self.subdir:
            return self.subdir.cwd()
        return self.path

    def title(self):
        if self.subdir:
            return self.subdir.title()
        title = self.path
        if len(title) > 16:
            title = '...' + title[-13:]
        return toIEC(title)

    def free(self):
        if self.subdir:
            return self.subdir.free()
        s = os.statvfs(self.path)
        free = s.f_bavail * s.f_bsize
        if free > 65535:
            free = 65535
        return free

    def haschild(self):
        return self.subdir

    def cd(self, iecname):
        print ('CD', repr(iecname))
        self.close()
        if iecname == b'':
            self.mapFiles() # Just in case
            return True
        if iecname == b'..':
            if self.subdir:
                if self.subdir.haschild():
                    self.subdir.cd(iecname)
                else:
                    self.subdir.close()
                    self.subdir = False
            else:
                print ("ERROR cannot go up")
            return
        if self.subdir:
            return self.subdir.cd(iecname)

        entry = self.matchFile(iecname)
        if entry is None:
            raise #FIXME
            return False
        if entry['extension'] == 'D64':
            self.subdir = D64Node(self.cwd(), entry['real_name'])
            return True
        if entry['extension'] == 'ZIP':
            self.subdir = ZipNode(self.cwd(), entry['real_name'])
            return True
        print ('CD', self.cwd(), entry['real_name'])
        self.subdir = DirNode(self.cwd(), entry['real_name'])
        return True

    def list(self):
        if self.subdir:
            return self.subdir.list()
        arr = self.files
        return arr

    def isdir(self, iecname):
        if self.subdir:
            return self.subdir.isdir(iecname)
        entry = self.matchFile(iecname)
        if entry is None:
            filepath = os.path.normpath(self.cwd() + '/' + fromIEC(iecname).decode('latin1'))
            return os.path.isdir(filepath)
        if entry['extension'] == 'DIR' or entry['extension'] == 'D64' or entry['extension'] == 'ZIP':
            return True
        return False

    def load(self, iecname):
        if self.subdir:
            return self.subdir.load(iecname)
        self.close()
        entry = self.matchFile(iecname)
        if entry is None:
            return None
        # TODO check if path is allowed
        filepath = os.path.normpath(self.cwd() + '/' + entry['real_name'])
        filesize = os.stat(filepath).st_size
        print ('OPEN FILE', filepath, filesize)
        self.rfile = open(filepath, 'rb')
        filename = entry['name']
        return C64File(self.rfile, filesize, filename)
        #return { 'fh': self.rfile, 'size': filesize, 'filename': filename}

    def save(self, iecname, overwrite = True):
        if self.subdir:
            return self.subdir.save(iecname)
        entry = self.matchFile(iecname)
        if not overwrite and entry is not None:
            return None
        if entry is not None:
            filepath = os.path.normpath(self.cwd() + '/' + entry['real_name'])
        else:
            filepath = os.path.normpath(self.cwd() + '/' + fromIEC(iecname).decode('latin1'))
        # TODO check if path is allowed
        print ("SAVE", filepath)
        self.wfile = open(filepath, 'wb')
        return C64File(self.wfile, 0, iecname)
        #return { 'fh': self.wfile, 'size': 0, 'filename': iecname}

    def close(self):
        if self.subdir:
            self.subdir.close()
        if self.wfile is not None:
            self.wfile.close()
            self.wfile = None
        if self.rfile is not None:
            self.rfile.close()
            self.rfile = None


class ZipNode:
    def __init__(self, cwd, name):
        self.path = os.path.normpath(cwd + '/' + name)
        self.subdir = False
        self.wfile = None
        self.rfile = None
        self.image = zipfile.ZipFile(self.path)
        self.workdir=''
        prefix = None
        for zipinfo in self.image.infolist():
            if prefix == None or prefix.startswith(zipinfo.filename):
                prefix = zipinfo.filename
            elif not zipinfo.filename.startswith(prefix):
                prefix = ''
                break
        # TODO implement
        print('COMMON PREFIX', prefix)
        self.prefix = prefix
        self.mapFiles()

    def __del__(self):
        if hasattr(self, 'image') and self.image is not None:
            self.image.close()
            self.image = None

    def mapFiles(self):
        self.files = []
        # FIXME add a shortcut for common prefix in all zipfiles
        for zipinfo in self.image.infolist():
            size = int((zipinfo.file_size + 255) / 256)
            if size > 65535:
                size = 65535
            name = zipinfo.filename
            if self.workdir != '':
                if not name.startswith(self.workdir):
                    continue
                name = name[len(self.workdir):]
            name = name.rstrip('/')
            if '/' in name or name == '':
                continue
            extension = ''
            if name.endswith('.prg') or name.endswith('.PRG'):
                extension = 'PRG'
                name = name[0:-4]
            if name.endswith('.d64') or name.endswith('.D64'):
                extension = 'D64'
                name = name[0:-4]
            if zipinfo.is_dir():
                extension = 'DIR'
            if len(name) > 16:
                name = name[0:16]
                # FIXME how about similar names ?
            name = toIEC(name)
            entry = { 'size': size, 'name': name, 'extension': extension, 'real_name': zipinfo.filename}
            print('ENTRY', entry)
            self.files.append(entry)

    def matchFile(self, iecname):
        for entry in self.files:
            if DOSPath.wildcard_match(entry['name'], entry['extension'], iecname):
                print('MATCH', repr(iecname), entry)
                return entry
        return None

    def cwd(self):
        if self.subdir:
            return self.subdir.cwd()
        return self.path + ':' + self.workdir.rstrip('/')

    def title(self):
        if self.subdir:
            return self.subdir.title()
        if self.workdir != '':
            title = self.workdir.rstrip('/')
        else:
            title = self.path
        if len(title) > 16:
            title = '...' + title[-13:]
        return toIEC(title)

    def free(self):
        if self.subdir:
            return self.subdir.free()
        s = os.statvfs(self.path)
        free = s.f_bavail * s.f_bsize
        if free > 65535:
            free = 65535
        return free

    def haschild(self):
        return self.subdir or self.workdir

    def cd(self, iecname):
        print ('CD', repr(iecname))
        self.close()
        if iecname == b'':
            self.mapFiles() # Just in case
            return True
        if iecname == b'..':
            if self.subdir:
                if self.subdir.haschild():
                    self.subdir.cd(iecname)
                else:
                    self.subdir.close()
                    self.subdir = False
            else:
                elems = self.workdir.rstrip('/').split('/')
                elems.pop()
                self.workdir = '/'.join(elems)
                if self.workdir != '':
                    self.workdir += '/'
            return
        if self.subdir:
            return self.subdir.cd(iecname)

        entry = self.matchFile(iecname)
        if entry is None:
            raise #FIXME
            return False
        print ('CD2', self.cwd(), entry['real_name'])
        if entry['extension'] == 'D64':
            filepath = entry['real_name']
            with self.image.open(filepath, 'r') as inh:
                print ('COPY FILE', filepath)
                tempf = tempfile.NamedTemporaryFile(prefix='d64-', dir='/tmp',
                                                delete=True)
                shutil.copyfileobj(inh, tempf)
                print('TEMP', tempf.name)
                self.subdir = D64Node('', tempf.name)
                tempf.close()
                return True
        if entry['extension'] == 'DIR':
            self.workdir = entry['real_name']
            print ('WORKDIR', self.workdir)
            self.mapFiles()
            return True
        return False

    def list(self):
        if self.subdir:
            return self.subdir.list()
        arr = self.files
        return arr

    def isdir(self, iecname):
        if self.subdir:
            return self.subdir.isdir(iecname)
        entry = self.matchFile(iecname)
        if entry is None:
            filepath = os.path.normpath(self.cwd() + '/' + fromIEC(iecname).decode('latin1'))
            return os.path.isdir(filepath)
        if entry['extension'] == 'DIR' or entry['extension'] == 'D64' or entry['extension'] == 'ZIP':
            return True
        return False

    def load(self, iecname):
        if self.subdir:
            return self.subdir.load(iecname)
        self.close()
        entry = self.matchFile(iecname)
        print("LOAD", entry, repr(iecname))
        if entry is None:
            entry = self.matchFile(fromPETSCII(iecname))
            print("LOAD", entry, iecname)
            if entry is None:
                return False
        # TODO check if path is allowed
        filepath = entry['real_name']
        print ('OPEN FILE', filepath)
        self.rfile = self.image.open(filepath, 'r')
        filename = entry['name']
        zipinfo = self.image.getinfo(filepath)
        filesize = zipinfo.file_size
        return C64File(self.rfile, filesize, filename)
        #return { 'fh': self.rfile, 'size': filesize, 'filename': filename}

    def save(self, iecname):
        if self.subdir:
            return self.subdir.save(iecname)
        entry = self.matchFile(iecname)
        if entry is not None:
            return None
        # TODO add support for save
        return None

    def close(self):
        if self.subdir:
            self.subdir.close()
        if self.wfile is not None:
            self.wfile.close()
            self.wfile = None
        if self.rfile is not None:
            self.rfile.close()
            self.rfile = None

class D64Node:
    def __init__(self, parent, name):
        self.path = os.path.normpath(parent + '/' + name)
        print ("INIT", parent, name)
        self.subdir = False
        self.wfile = None
        self.rfile = None
        self.image = DiskImage(self.path).open()

    def __del__(self):
        if hasattr(self, 'image') and self.image is not None:
            self.image.close()
            self.image = None

    def cwd(self):
        return self.path

    def title(self):
        return self.image.name
        # /home/kasper/.local/lib/python3.7/site-packages/d64/dos_image.py 

    def free(self):
        return self.image.bam.total_free()

    def haschild(self):
        return False

    def cd(self, iecname):
        print ("CD", repr(iecname))
        if iecname == b'..':
            print ("ERROR cannot go up")
        name = fromIEC(iecname)
        if name == b'':
            return True
        raise

    def list(self):
        arr = []
        for path in self.image.glob(b'*'):
            print("LIST", path.size_blocks, path.name, path.entry.file_type)
            arr.append({ 'size': path.size_blocks, 'name': path.name, 'extension': path.entry.file_type})
        return arr

    def isdir(self, iecname):
        return False

    def load(self, iecname):
        print ('LOAD', iecname)
        #self.path = self.image.path(iecname.encode('petscii-c64en-uc'))
        path = self.image.path(iecname)
        if not path.exists():
            return None
        self.rfile = path.open("rb")
        filesize = path.size_bytes
        return C64File(self.rfile, filesize, iecname)
        #return { 'fh': self.rfile, 'size': filesize, 'filename': iecname}

    def save(self, iecname):
        self.filename = fromIEC(iecname)
        path = self.image.path(iecname.encode('petscii-c64en-uc'))
        if not self.path.exists():
            return None
        self.wfile = path.open('wb')
        return C64File(self.wfile, 0, iecname)
        #return { 'fh': self.wfile, 'size': 0, 'filename': iecname}

    def close(self):
        if self.wfile is not None:
            self.wfile.close()
            self.wfile = None
        if self.rfile is not None:
            self.rfile.close()
            self.rfile = None
        self.path = None

global rootNode
rootNode = DirNode('../', 'warez')
rootNode.buflen = 254
global openFiles
openFiles = [None for i in range(16)] 



def loadDir():
    global rootNode
    title = rootNode.title()
    free = rootNode.free()

    print ("TITLE", title, rootNode)
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

    for entry in rootNode.list():
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
    print ('DIR DATA', dirdata)
    return C64MemoryFile(dirdata, b'$')
    #return { 'fh': inmemoryfile, 'size': inmemoryfilelen, 'filename': b'$'}

def doLoad(s, name):
    global rootNode
    global openFiles
    if openFiles[0] is not None:
        openFiles[0].close()
    if name == b'$':
        print ("LOAD DIR", rootNode.cwd())
        openFiles[0] = loadDir()
        return
    elif rootNode.isdir(name):
        print ("LOAD CD", rootNode.cwd(), name)
        rootNode.cd(name)
        openFiles[0] = loadDir()
        return
    else:
        print ("JUST LOAD", rootNode.cwd(), name)
        openFiles[0] = rootNode.load(name)
    print ("LOAD", repr(openFiles[0]))
    if openFiles[0] == None:
        openFiles[15] = C64MemoryFile(b'62, FIXME FILE NOT FOUND OR SOMETHING,00,00\r', b'status')
    else:
        openFiles[15] = C64MemoryFile(b'00, OK,00,00\r', b'status')

def doSave(s, name):
    global rootNode
    global openFiles
    if openFiles[1] is not None:
        openFiles[1].close()
    print ("SAVE", name)
    openFiles[1] = rootNode.save(name)
    print ("SAVE", name, openFiles[1])
    if openFiles[1] == None:
        print ("File not opened")
        openFiles[15] = C64MemoryFile(b'62, FIXME FILE NOT FOUND OR SOMETHING,00,00\r', b'status')
    else:
        openFiles[15] = C64MemoryFile(b'00, OK,00,00\r', b'status')

def doOpen(s, channel, name):
    global rootNode
    if name.startswith(b'0:'):
        name = name[2:]
    if channel == 15: # CONTROL
        ret = True
        if name.startswith(b'CD:'):
            if name == b'CD:_':
                ret = rootNode.cd(b'..')
            else:
                ret = rootNode.cd(name[3:])
            if ret:
                ret = IOErrorMessage.ErrOK.value
                openFiles[0] = loadDir()
            else:
                ret = IOErrorMessage.ErrFileNotFound.value
            print ("CWD", ret, rootNode.cwd())
        if name.startswith(b'M-W'):
            address, size = unpack('<HB', name[3:6])
            print ('MEMORY WRITE', address, size, len(name[6:]), repr(name[6:]))
    else: # channels 2-14
        elems = fromIEC(name).decode('latin1').split(',', 3)
        print ('OPEN CHANNEL', channel, elems)
        # FIXME write, too
        openFiles[channel] = rootNode.load(toIEC(elems[0]))
        print ("READ SEQ", repr(openFiles[channel]))
        if openFiles[channel] == None:
            openFiles[15] = C64MemoryFile(b'62, FIXME FILE NOT FOUND OR SOMETHING,00,00\r', b'status')
        else:
            openFiles[15] = C64MemoryFile(b'00, OK,00,00\r', b'status')


def doCmd(s, cmd, secondary, data):
    global rootNode
    global openFiles
    print ("SOCKET CMD", cmd, "secondary", secondary, 'data[',len(data),']')
    if cmd == 'I':
        data = data.decode('latin1')
        print('INIT', repr(data))
        s.iecSendMsg(b'I', 8, b'') # hw device id 8

    elif cmd == 'P':
        doOpen(s, secondary, data)
        print('DOS', repr(data))

    elif cmd == 'O':
        name = fromIEC(data)
        if secondary == 0: # LOAD
            doLoad(s, data)
        elif secondary == 1: # SAVE
            doSave(s, data)
        else:
            doOpen(s, secondary, data)
        print('OPEN', repr(name), repr(data))

    elif cmd == 'C':
        if openFiles[secondary] is not None:
            openFiles[secondary].close()
        openFiles[secondary] = None
        # FIXME check secondary
        rootNode.close()
        print("CLOSE")

    elif cmd == 'T': # Talk
        print('TALK')
        if openFiles[secondary] is None:
            s.iecSendMsg(b'>', secondary, IOErrorMessage.ErrFileNotFound.value)
        else:
            s.iecSendMsg(b'>', secondary, IOErrorMessage.ErrOK.value)

    elif cmd == 'L': # Listen
        print('LISTEN')
        # FIXME check if writable
        if openFiles[secondary] is None:
            s.iecSendMsg(b'>', secondary, IOErrorMessage.ErrDiskFullOrDirectoryFull.value)
        else:
            s.iecSendMsg(b'>', IOErrorMessage.ErrOK.value)

    elif cmd == 'R':
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
            print('READ OK')

    elif cmd == 'W':
        print ('WRITE', openFiles[secondary])
        # TODO check datalen
        openFiles[secondary].write(data)

    elif cmd == 'D':
        data = data.decode('latin1')
        print('DEBUG', repr(data))

s = IECGW()

while True:
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


