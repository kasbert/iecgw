import re
from html.parser import HTMLParser
from html.entities import name2codepoint
from urllib.parse import urljoin
import tempfile
import logging

from .codec import fileEntry, fromPETSCII, toPETSCII, matchFile
from .ZipNode import ZipNode
from .D64Node import D64Node
from .IECGW import C64MemoryFile

#from .DirNode import DirNode
import urllib.request

CSDB_URL='https://csdb.dk/toplist.php?type=release&subtype=%282%29'

class CSDBNode:
    def __init__(self, parent, url = CSDB_URL):
        self.parent = parent
        self.url = url
        self.title_ = 'CSDB.DK'
        self.tempf = None
        self.offset = 0
        self.files = []

    def __str__(self):
        return 'CSDBNode ' + repr(self.url)

    def start(self):
        parser = MyHTMLParser()
        parser.files = []
        data = self.readPage(self.url)
        if data is None:
            return False
        parser.feed(data.decode('latin1'))
        logging.info('TITLE %s', parser.title_)
        self.files = []
        self.title_ = parser.title_
        for entry in parser.files[0:50]:
            name = re.sub(r'^.*/', '', entry['name'])
            file = fileEntry(0, name, self.files)
            file['href'] = entry['href']
            logging.info('ENTRY %s', file)
            self.files.append(file)
        return True

    def cwd(self):
        return ''

    def title(self):
        return self.title_.encode('latin1')

    def free(self):
        return 0

    def cd(self, iecname):
        self.close()
        if iecname == b'..' or iecname == b'_':
            if self.parent:
                return self.parent
            return None
        if iecname == b'':
            return self
        if iecname.startswith(b'Q='):
            url = b'https://csdb.dk/search/?search=' + fromPETSCII(iecname)[2:]
            logging.info('CD SEARCH %s %s', self.cwd(), url)
            node = CSDBNode(self, url.decode('latin1'))
            if not node.start():
                return None
            return node
        if iecname == b'== MORE ==' or iecname == b'== more ==': # Next page
            self.offset += 40
            return self
        entry = matchFile(self.files, iecname)
        if entry is None:
            return None
        url = urljoin(self.url, entry['href'])
        if entry['extension'] == 'D64':
            data = self.readPage(url)
            if data is None:
                return None
            tempf = tempfile.NamedTemporaryFile(prefix='d64-', dir='/tmp',
                                            delete=True)
            tempf.write(data)
            node = D64Node(self, '', tempf.name)
            if not node.start():
                return None
            self.tempf = tempf
            #tempf.close()
            return node
        if entry['extension'] == 'ZIP':
            data = self.readPage(url)
            if data is None:
                return None
            tempf = tempfile.NamedTemporaryFile(prefix='zip-', dir='/tmp',
                                            delete=True)
            tempf.write(data)
            node = ZipNode(self, '', tempf.name)
            if not node.start():
                return None
            self.tempf = tempf
            #tempf.close()
            return node
        logging.info('CD %s %s', self.cwd(), url)
        node = CSDBNode(self, url)
        if not node.start():
            return None
        return node

    def list(self):
        arr = self.files[self.offset:]
        if len(arr) > 40:
            entry = { 'size': 0, 'name': b'== MORE ==', 'extension': 'DIR'}
            arr = arr[0:40]
            arr.append(entry)
        return arr

    def isdir(self, iecname):
        if iecname.startswith(b'Q='):
            return True
        if iecname == b'== MORE ==' or iecname == b'== more ==': # Next page
            return True
        entry = matchFile(self.files, iecname)
        logging.info("LOAD %s %s", entry, repr(iecname))
        if entry is None:
            return False
        if entry['extension'] == 'PRG':
            return False
        return True

    def load(self, iecname):
        entry = matchFile(self.files, iecname)
        logging.info("LOAD %s %s", entry, repr(iecname))
        if entry is None:
            return None
        #... if entry['extension'] == 'PRG':
        if entry['extension'] == 'PRG':
            url = urljoin(self.url, entry['href'])
            data = self.readPage(url)
            if data is None:
                return None
            return C64MemoryFile(data, entry['name'])
        return None

    def save(self, iecname):
        return None

    def close(self):
        if self.tempf is not None:
            self.tempf.close()
            self.tempf = None

    def readPage(self, url):
        logging.info("OPEN %s", url)
        try:
            webUrl  = urllib.request.urlopen(url)
        except Exception as e:
            logging.exception("Error opening %s", url)
            return None
        logging.info("result code: %d", webUrl.getcode())
        data = webUrl.read()
        return data

class MyHTMLParser(HTMLParser):
    def __init__(self):
        HTMLParser.__init__(self)
        self.a = False
        self.title = False
        self.title_ = 'CSDB.DK'

    def handle_starttag(self, tag, attrs):
        #logging.debug("Start tag: %s", tag)
        #for attr in attrs:
        #    logging.debug("     attr: %s", attr)
        attrs = dict(attrs)
        # TODO add configurable filtering
        if tag == 'a' and 'href' in attrs and (attrs['href'].startswith('/release') or attrs['href'].startswith('download')) and '&' not in attrs['href']:
            self.a = True
            self.href = attrs['href']
        if tag == 'title':
            self.title = True

    def handle_endtag(self, tag):
        #logging.debug("End tag  : %s", tag)
        if tag == 'a' and self.a:
            self.a = False
            self.files.append({ 'size': 0, 'name': self.data, 'extension': 'DIR', 'href': self.href })
        if tag == 'title':
            #logging.debug ('TITLE %s', self.data)
            self.title_ = self.data
            self.title = False

    def handle_data(self, data):
        #logging.debug("Data     : %s", data)
        if self.a or self.title:
            self.data = data.strip()

    def handle_comment(self, data):
        #logging.debug("Comment  : %s", data)
        pass

    def handle_entityref(self, name):
        c = chr(name2codepoint[name])
        logging.info("Named ent: %s", c)

    def handle_charref(self, name):
        if name.startswith('x'):
            c = chr(int(name[1:], 16))
        else:
            c = chr(int(name))
        logging.info("Num ent  : %s", c)

    def handle_decl(self, data):
        #logging.info("Decl     : %s", data)
        self.a = False
        self.title = False

__all__ = [
    "D64Node",
]
