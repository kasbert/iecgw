import io
import os
from stat import *
import logging

from .codec import fileEntry, toIEC, fromIEC, matchFile
from .D64Node import D64Node
from .IECGW import C64File
from .ZipNode import ZipNode
from .DirNode import DirNode

class FileSearchNode:
    def __init__(self, parent, dirs, query):
        self.parent = parent
        self.dirs = dirs
        self.query = query
        self.rfile = None
        self.files = []

    def __str__(self):
        return 'FileSearchNode ' + repr(self.query)

    def traverse(self, dirpath, query):
        files = []
        logging.debug ('Enter dir', dirpath)
        for entry in sorted(os.scandir(dirpath), key=lambda x: x.name.lower()):
            if entry.name.startswith('.'): # and entry.is_file():
                continue
            if query.lower() in entry.name.lower():
                size = int((entry.stat().st_size + 255) / 256)
                file = fileEntry(size, entry.name, self.files)
                if S_ISDIR(entry.stat().st_mode):
                    file['extension'] = 'DIR'
                file['dirpath'] = dirpath
                logging.info('ENTRY %s', file)
                files.append(file)
            elif S_ISDIR(entry.stat().st_mode):
                files += self.traverse(dirpath + '/' + entry.name, query)
        return files

    def start(self):
        self.files = []
        for dirpath in self.dirs:
            try:
                path = os.path.normpath(dirpath)
                self.files += self.traverse(path, self.query)
            except Exception as e:
                logging.error('Error listing %s', self.path)
                return None
        return True

    def cwd(self):
        return self.query

    def title(self):
        title = self.query
        if len(title) > 16:
            title = '...' + title[-13:]
        return toIEC(title)

    def free(self):
        return 0

    def cd(self, iecname):
        self.close()
        if iecname == b'':
            self.start() # Just in case
            return self
        if iecname == b'..' or iecname == b'_':
            if self.parent:
                return self.parent
            return None
        entry = matchFile(self.files, iecname)
        if entry is None:
            return None
        if entry['extension'] == 'D64':
            node = D64Node(self, entry['dirpath'], entry['real_name'])
        elif entry['extension'] == 'ZIP':
            node = ZipNode(self, entry['dirpath'], entry['real_name'])
        else:
            node = DirNode(self, entry['dirpath'], entry['real_name'])
        if not node.start():
            return None
        return node

    def list(self):
        return self.files

    def isdir(self, iecname):
        entry = matchFile(self.files, iecname)
        if entry is None:
            return False
        if entry['extension'] == 'DIR' or entry['extension'] == 'D64' or entry['extension'] == 'ZIP':
            return True
        return False

    def load(self, iecname):
        self.close()
        entry = matchFile(self.files, iecname)
        if entry is None:
            return None
        # TODO check if path is allowed
        filepath = os.path.normpath(entry['dirpath'] + '/' + entry['real_name'])
        filesize = os.stat(filepath).st_size
        logging.info('OPEN FILE %s %d', filepath, filesize)
        self.rfile = open(filepath, 'rb')
        filename = entry['name']
        return C64File(self.rfile, filesize, filename)

    def save(self, iecname, overwrite = True):
        return None

    def close(self):
        if self.rfile is not None:
            self.rfile.close()
            self.rfile = None

__all__ = [
    "DirNode",
]