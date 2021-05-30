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
        print('>', repr(data))

    def iecSendMsg(self, cmd, secondary, data):
        if isinstance(data, int):
            data = bytes([data])
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
    "C64File",
    "C64MemoryFile",
]