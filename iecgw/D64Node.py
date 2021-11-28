
import os
import logging

import cbmcodecs
from d64 import DiskImage
from cbm_files import ProgramFile
from d64.dos_path import DOSPath

from .IECGW import C64File

class D64Node:
    def __init__(self, parent, dir, name):
        self.parent = parent
        self.path = os.path.normpath(dir + '/' + name)
        self.wfile = None
        self.rfile = None
        self.image = None

    def __str__(self):
        return 'D64Node ' + repr(self.path)

    def start(self):
        self.image = DiskImage(self.path).open()
        return True

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
        if iecname == b'..' or iecname == b'_':
            if self.parent:
                return self.parent
            return None
        if iecname == b'':
            return self
        return None

    def list(self):
        arr = []
        for path in self.image.glob(b'*'):
            entry = { 'size': path.size_blocks, 'name': path.name, 'extension': path.entry.file_type}
            logging.info('ENTRY %s', entry)
            arr.append(entry)
        return arr

    def isdir(self, iecname):
        return False

    def load(self, iecname):
        logging.info('LOAD %s', iecname)
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
        #self.path = None
__all__ = [
    "D64Node",
]