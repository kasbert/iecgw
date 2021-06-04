import io
import os
from stat import *
from .codec import fileEntry, toIEC, fromIEC, matchFile
from .D64Node import D64Node
from .IECGW import C64File
from .ZipNode import ZipNode

class DirNode:
    def __init__(self, cwd, name):
        self.path = os.path.normpath(cwd + '/' + name)
        self.next = False
        self.wfile = None
        self.rfile = None
        self.mapFiles()

    def mapFiles(self):
        self.files = []
        for entry in sorted(os.scandir(self.path), key=lambda x: x.name.lower()):
            if not entry.name.startswith('.'): # and entry.is_file():
                size = int((entry.stat().st_size + 255) / 256)
                file = fileEntry(size, entry.name, self.files)
                if S_ISDIR(entry.stat().st_mode):
                    file['extension'] = 'DIR' 
                print('ENTRY', file)
                self.files.append(file)

    def cwd(self):
        return self.path

    def title(self):
        title = self.path
        if len(title) > 16:
            title = '...' + title[-13:]
        return toIEC(title)

    def free(self):
        s = os.statvfs(self.path)
        free = s.f_bavail * s.f_bsize
        if free > 65535:
            free = 65535
        return free

    def cd(self, iecname):
        self.close()
        if iecname == b'':
            self.mapFiles() # Just in case
            return self
        if iecname == b'..' or iecname == b'_':
            if self.next:
                return self.next
            return None
        entry = matchFile(self.files, iecname)
        if entry is None:
            return None
        if entry['extension'] == 'D64':
            node = D64Node(self.cwd(), entry['real_name'])
            node.next = self
            return node
        if entry['extension'] == 'ZIP':
            node = ZipNode(self.cwd(), entry['real_name'])
            node.next = self
            return node
        print ('CD', self.cwd(), entry['real_name'])
        node = DirNode(self.cwd(), entry['real_name'])
        node.next = self
        return node

    def list(self):
        return self.files

    def isdir(self, iecname):
        entry = matchFile(self.files, iecname)
        if entry is None:
            filepath = os.path.normpath(self.cwd() + '/' + fromIEC(iecname).decode('latin1'))
            return os.path.isdir(filepath)
        if entry['extension'] == 'DIR' or entry['extension'] == 'D64' or entry['extension'] == 'ZIP':
            return True
        return False

    def load(self, iecname):
        self.close()
        entry = matchFile(self.files, iecname)
        if entry is None:
            return None
        # TODO check if path is allowed
        filepath = os.path.normpath(self.cwd() + '/' + entry['real_name'])
        filesize = os.stat(filepath).st_size
        print ('OPEN FILE', filepath, filesize)
        self.rfile = open(filepath, 'rb')
        filename = entry['name']
        return C64File(self.rfile, filesize, filename)

    def save(self, iecname, overwrite = True):
        entry = matchFile(self.files, iecname)
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

    def close(self):
        if self.wfile is not None:
            self.wfile.close()
            self.wfile = None
        if self.rfile is not None:
            self.rfile.close()
            self.rfile = None

__all__ = [
    "DirNode",
]