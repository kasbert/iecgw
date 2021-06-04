

from .codec import matchFile,fromPETSCII
from .CSDBNode import CSDBNode

class MenuNode:
    def __init__(self, files = []):
        self.next = False
        self.files = files

    def cwd(self):
        return ''

    def title(self):
        return b'MENU'

    def free(self):
        return 0

    def cd(self, iecname):
        self.close()
        if iecname == b'..' or iecname == b'_':
            if self.next:
                next = self.next
                self.next = False
                return next
            return self # Already at top
        if iecname == b'':
            return self
        if iecname.startswith(b'Q='):
            url = b'https://csdb.dk/search/?search=' + fromPETSCII(iecname)[2:]
            print ('CD SEARCH', self.cwd(), url)
            node = CSDBNode(url.decode('latin1'))
            node.next = self
            return node
        entry = matchFile(self.files, iecname)
        if entry is None:
            return None
        node = entry['node']()
        node.next = self
        return node

    def list(self):
        return self.files

    def isdir(self, iecname):
        return True

    def load(self, iecname):
        return None

    def save(self, iecname):
        return None

    def close(self):
        pass

__all__ = [
    "D64Node",
]