

from .codec import matchFile

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
        if iecname == b'..':
            if self.next:
                next = self.next
                self.next = False
                return next
            return None
        if iecname == b'':
            return self
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