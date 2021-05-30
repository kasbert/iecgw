
import os

import cbmcodecs
from d64 import DiskImage
from cbm_files import ProgramFile
from d64.dos_path import DOSPath

from .IECGW import C64File

class D64Node:
    def __init__(self, parent, name):
        self.path = os.path.normpath(parent + '/' + name)
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

    def cd(self, iecname):
        self.close()
        if iecname == b'..':
            if self.next:
                return self.next
            return None
        if iecname == b'':
            return self
        return None

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

    def save(self, iecname):
        path = self.image.path(iecname.encode('petscii-c64en-uc'))
        if not self.path.exists():
            return None
        self.wfile = path.open('wb')
        return C64File(self.wfile, 0, iecname)

    def close(self):
        if self.wfile is not None:
            self.wfile.close()
            self.wfile = None
        if self.rfile is not None:
            self.rfile.close()
            self.rfile = None
        self.path = None
__all__ = [
    "D64Node",
]