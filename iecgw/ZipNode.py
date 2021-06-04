
import zipfile
import tempfile
import shutil
import os
from .codec import toIEC,matchFile,fileEntry
from .D64Node import D64Node
from .IECGW import C64File

class ZipNode:
    def __init__(self, cwd, name):
        self.path = os.path.normpath(cwd + '/' + name)
        self.wfile = None
        self.rfile = None
        self.image = zipfile.ZipFile(self.path)
        self.workdir=''
        prefix = None
        for zipinfo in self.image.infolist():
            if prefix == None or prefix.startswith(zipinfo.filename):
                prefix = zipinfo.filename
            elif not zipinfo.filename.startswith(prefix):
                prefix = ''
                break
        # TODO implement
        print('COMMON PREFIX', prefix)
        self.prefix = prefix
        self.mapFiles()

    def __del__(self):
        if hasattr(self, 'image') and self.image is not None:
            self.image.close()
            self.image = None

    def mapFiles(self):
        self.files = []
        # FIXME add a shortcut for common prefix in all zipfiles
        dirs = []
        for zipinfo in self.image.infolist():
            size = int((zipinfo.file_size + 255) / 256)
            name = zipinfo.filename
            if not name.startswith(self.workdir):
                continue
            name = name[len(self.workdir):]
            name = name.rstrip('/').lstrip('/')
            if name == '':
                continue
            if '/' in name:
                dir = name.split('/', 2)[0]
                if dir in dirs:
                    continue
                dirs.append(dir)
                file = fileEntry(0, dir, self.files)
                file['extension'] = 'DIR'
                print('ENTRY', file)
                self.files.append(file)
                continue
            file = fileEntry(size, name, self.files)
            if zipinfo.is_dir():
                file['extension'] = 'DIR'
            file['real_name'] = zipinfo.filename
            print('ENTRY', file)
            self.files.append(file)

    def cwd(self):
        return self.path + ':' + self.workdir.rstrip('/')

    def title(self):
        if self.workdir != '':
            title = self.workdir.rstrip('/')
        else:
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
            if self.workdir != '':
                elems = self.workdir.rstrip('/').split('/')
                elems.pop()
                self.workdir = '/'.join(elems)
                if self.workdir != '':
                    self.workdir += '/'
                self.mapFiles() # Just in case
                return self
            if self.next:
                return self.next
            return None
        entry = matchFile(self.files, iecname)
        if entry is None:
            return None
        print ('CD2', self.cwd(), entry['real_name'])
        if entry['extension'] == 'D64':
            filepath = entry['real_name']
            with self.image.open(filepath, 'r') as inh:
                print ('COPY FILE', filepath)
                tempf = tempfile.NamedTemporaryFile(prefix='d64-', dir='/tmp',
                                                delete=True)
                shutil.copyfileobj(inh, tempf)
                node = D64Node('', tempf.name)
                node.next = self
                tempf.close()
                return node
        if entry['extension'] == 'DIR':
            self.workdir = entry['real_name']
            self.mapFiles()
            return self
        return None

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
        print("LOAD", entry, repr(iecname))
        if entry is None:
            return False
        filepath = entry['real_name']
        print ('OPEN FILE', filepath)
        self.rfile = self.image.open(filepath, 'r')
        filename = entry['name']
        zipinfo = self.image.getinfo(filepath)
        filesize = zipinfo.file_size
        return C64File(self.rfile, filesize, filename)

    def save(self, iecname):
        entry = matchFile(self.files, iecname)
        if entry is not None:
            return None
        # TODO add support for save
        return None

    def close(self):
        if self.wfile is not None:
            self.wfile.close()
            self.wfile = None
        if self.rfile is not None:
            self.rfile.close()
            self.rfile = None

__all__ = [
    "ZipNode",
]