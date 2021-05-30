
from enum import Enum
from d64.dos_path import DOSPath
import itertools

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
