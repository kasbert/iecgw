import io
import os
from stat import *
import logging

from .codec import fileEntry, toIEC, fromIEC, matchFile
from .IECGW import C64File

class FileNode:
    def __init__(self, parent, path):
        self.parent = parent
        self.path = os.path.normpath(path)
        self.rfile = None

    def __str__(self):
        return 'FileNode ' + repr(self.path)

    def start(self):
        return os.path.exists(self.path)

    def cwd(self):
        return self.path

    def title(self):
        return b''

    def free(self):
        return 0

    def cd(self, iecname):
        self.close()
        if iecname == b'':
            return self
        if iecname == b'..' or iecname == b'_':
            if self.parent:
                return self.parent
            return None
        return None

    def list(self):
        return []

    def isdir(self, iecname):
        return False

    def load(self, iecname):
        self.close()
        # TODO check if path is allowed
        filepath = os.path.normpath(self.path)
        filesize = os.stat(filepath).st_size
        logging.info('OPEN FILE %s %d', filepath, filesize)
        self.rfile = open(filepath, 'rb')
        filename = os.path.basename(filepath)
        return C64File(self.rfile, filesize, filename)

    def save(self, iecname, overwrite = True):
        return None

    def close(self):
        if self.rfile is not None:
            self.rfile.close()
            self.rfile = None

__all__ = [
    "FileNode",
]