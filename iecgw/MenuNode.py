
import logging

from .codec import matchFile,fromPETSCII
from .CSDBNode import CSDBNode

class MenuNode:
    def __init__(self, parent, files = [], title = b'MENU'):
        self.parent = parent
        self.files = files
        self._title = title

    def __str__(self):
        return 'MenuNode ' + repr(self._title)

    def start(self):
        for file in self.files:
            file['node'].parent = self # TODO ?
        return True

    def cwd(self):
        return ''

    def title(self):
        return self._title

    def free(self):
        return 0

    def cd(self, iecname):
        self.close()
        if iecname == b'..' or iecname == b'_':
            if self.parent:
                parent = self.parent
                self.parent = False
                return parent
            return self # Already at top
        if iecname == b'':
            return self
        if iecname.startswith(b'Q='):
            url = b'https://csdb.dk/search/?search=' + fromPETSCII(iecname)[2:]
            logging.info('CD SEARCH %s %s', self.cwd(), url)
            node = CSDBNode(self, url.decode('latin1'), self)
            if not node.start():
                return None
            return node
        entry = matchFile(self.files, iecname)
        if entry is None:
            return None
        node = entry['node']
        if not node.start():
            return None
        return node

    def list(self):
        return self.files

    def isdir(self, iecname):
        return True

    def load(self, iecname):
        entry = matchFile(self.files, iecname)
        if entry is None:
            return None
        return entry['node'].load(iecname)

    def save(self, iecname):
        return None

    def close(self):
        pass

__all__ = [
    "D64Node",
]