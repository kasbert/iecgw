
from enum import Enum
from d64.dos_path import DOSPath
import itertools
from struct import pack

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
            buf.append(c2 - 0x80)
        else:
            buf.append(c2)
    return buf

def matchFile(files, iecname):
    name = fromPETSCII(iecname)
    for entry in files:
        if DOSPath.wildcard_match(entry['name'], entry['extension'], iecname):
            print('MATCH', repr(iecname), entry)
            return entry
        if DOSPath.wildcard_match(entry['name'], entry['extension'], name):
            print('MATCH', repr(name), entry)
            return entry
    return None

def fileEntry(size, realname, files):
    if size > 65535:
        size = 65535
    name = realname
    name = name.replace('?', '_')
    name = name.replace('*', '_')
    name = name.replace('=', '_')
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
    if len(name) > 16:
        name = name[0:16]
        # FIXME how about similar names ?
    name = toPETSCII(name)
    if matchFile(files, name):
        name = name[0:15]
        for c in itertools.chain(range(48,58),range(65,127)):
            nname = name + bytes([c])
            if not matchFile(files, nname):
                name = nname
                break
    entry = { 'size': size, 'name': name, 'extension': extension, 'real_name': realname}
    return entry

def packDir(title, list, free):
    print ("TITLE", title, free)
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

    for entry in list:
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
    return dirdata

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
