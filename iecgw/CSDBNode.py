import re
from html.parser import HTMLParser
from html.entities import name2codepoint
from urllib.parse import urljoin
import tempfile

from .codec import fileEntry, fromPETSCII, toPETSCII, matchFile
from .ZipNode import ZipNode
from .D64Node import D64Node
from .IECGW import C64MemoryFile

#from .DirNode import DirNode
import urllib.request

CSDB_URL='https://csdb.dk/toplist.php?type=release&subtype=%282%29'

class CSDBNode:
    def __init__(self, url = CSDB_URL):
        self.url = url
        self.next = False
        self.files = []
        self.mapFiles()
        self.title_ = 'CSDB.DK'
        self.tempf = None

    def mapFiles(self):
        parser = MyHTMLParser()
        parser.files = []
        print ("OPEN", self.url)
        webUrl  = urllib.request.urlopen(self.url)

        print ("result code: " + str(webUrl.getcode()))
        data = webUrl.read()
        #print (data)

        parser.feed(data.decode('latin1'))
        #print(repr(parser.files), parser.title_)
        print('TITLE', parser.title_)
        self.files = []
        self.title_ = parser.title_
        for entry in parser.files[0:20]: # FIXME add paging
            name = re.sub(r'^.*/', '', entry['name'])
            file = fileEntry(0, name, self.files)
            file['href'] = entry['href']
            print('ENTRY', file)
            self.files.append(file)

    def cwd(self):
        return ''

    def title(self):
        return self.title_.encode('latin1')

    def free(self):
        return 0

    def cd(self, iecname):
        self.close()
        if iecname == b'..':
            if self.next:
                return self.next
            return None
        if iecname == b'':
            return self
        entry = matchFile(self.files, iecname)
        if entry is None:
            return None
        url = urljoin(self.url, entry['href'])
        if entry['extension'] == 'D64':
            print ("OPEN", url)
            webUrl  = urllib.request.urlopen(url)
            print ("result code: " + str(webUrl.getcode()))
            data = webUrl.read()
            tempf = tempfile.NamedTemporaryFile(prefix='d64-', dir='/tmp',
                                            delete=True)
            tempf.write(data)
            node = D64Node('', tempf.name)
            node.next = self
            self.tempf = tempf
            #tempf.close()
            return node
        if entry['extension'] == 'ZIP':
            print ("OPEN", url)
            webUrl  = urllib.request.urlopen(url)
            print ("result code: " + str(webUrl.getcode()))
            data = webUrl.read()
            tempf = tempfile.NamedTemporaryFile(prefix='zip-', dir='/tmp',
                                            delete=True)
            tempf.write(data)
            node = ZipNode('', tempf.name)
            node.next = self
            self.tempf = tempf
            #tempf.close()
            return node
        print ('CD', self.cwd(), url)
        node = CSDBNode(url)
        node.next = self
        return node

    def list(self):
        return self.files

    def isdir(self, iecname):
        entry = matchFile(self.files, iecname)
        print("LOAD", entry, repr(iecname))
        if entry is None:
            return False
        if entry['extension'] == 'PRG':
            return False
        return True

    def load(self, iecname):
        entry = matchFile(self.files, iecname)
        print("LOAD", entry, repr(iecname))
        if entry is None:
            return False
        #... if entry['extension'] == 'PRG':
        if entry['extension'] == 'PRG':
            url = urljoin(self.url, entry['href'])
            print ("OPEN", url)
            webUrl  = urllib.request.urlopen(url)
            print ("result code: " + str(webUrl.getcode()))
            data = webUrl.read()
            return C64MemoryFile(data, entry['name'])
        return False

    def save(self, iecname):
        return None

    def close(self):
        if self.tempf is not None:
            self.tempf.close()
            self.tempf = None

class MyHTMLParser(HTMLParser):
    def handle_starttag(self, tag, attrs):
        #print("Start tag:", tag)
        #for attr in attrs:
        #    print("     attr:", attr)
        attrs = dict(attrs)
        if tag == 'a' and 'href' in attrs and (attrs['href'].startswith('/release') or attrs['href'].startswith('download')) and '&' not in attrs['href']:
            self.a = True
            self.href = attrs['href']
        if tag == 'title':
            self.title = True

    def handle_endtag(self, tag):
        #print("End tag  :", tag)
        if tag == 'a' and self.a:
            self.a = False
            self.files.append({ 'size': 0, 'name': self.data, 'extension': 'DIR', 'href': self.href })
        if tag == 'title':
            print ('TITLE', self.data)
            self.title_ = self.data
            self.title = False


    def handle_data(self, data):
        #print("Data     :", data)
        if self.a or self.title:
            self.data = data.strip()

    def handle_comment(self, data):
        #print("Comment  :", data)
        pass

    def handle_entityref(self, name):
        c = chr(name2codepoint[name])
        print("Named ent:", c)

    def handle_charref(self, name):
        if name.startswith('x'):
            c = chr(int(name[1:], 16))
        else:
            c = chr(int(name))
        print("Num ent  :", c)

    def handle_decl(self, data):
        #print("Decl     :", data)
        self.a = False
        self.title = False

__all__ = [
    "D64Node",
]
