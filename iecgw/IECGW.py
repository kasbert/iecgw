import socket
from struct import pack,unpack
import io

HOST = '127.0.0.1'  # The server's hostname or IP address
PORT = 1541        # The port used by the server

class IECGW:
    def __init__(self, host = HOST, port = PORT):
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.s.connect((host, port))

    def close(self):
        self.s.close()

    def iecSend(self, data):
        self.s.sendall(data)
        if len(data) < 20:
            print('>', repr(data))
        else:
            print('>', repr(data[0:20]), '...')

    def iecSendMsg(self, msg):
        data = msg.data
        if isinstance(data, int):
            data = bytes([data])
        header = pack('cBB', msg.cmd, msg.secondary, len(data))
        self.s.sendall(header)
        if len(data) > 0:
            self.s.sendall(data)
        if len(data) < 20:
            print('>', repr(header), '[', len(data), ']', repr(data))
        else:
            print('>', repr(header), '[', len(data), ']', repr(data[0:20]), '...')

    def iecReadMsg(self):
        data = self.iecRead(3)
        if data == b'':
            return None
        cmd = chr(data[0])
        secondary = data[1]
        size = data[2]
        data = b''
        if size > 0:
            data = self.iecRead(size)
        msg = IECMessage(cmd, secondary, data)
        return msg

    def iecRead(self, length):
        buf = bytearray()
        while len(buf) < length:
            data = self.s.recv(length - len(buf))
            if data == b'':
                print('<*', repr(buf))
                return None
            buf += data
        print('<', repr(buf))
        return buf

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

class IECMessage:
    def __init__(self, cmd, secondary, data):
        self.cmd = cmd
        self.secondary = secondary
        self.data = data

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

__all__ = [
    "IECGW",
    "IECMessage"
    "C64File",
    "C64MemoryFile",
]