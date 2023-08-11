import stat
from collections import namedtuple

import paths
import util

class UnknownObjectTypeError(BaseException):
    pass

def object_type_from_mode(mode:int):
    S_IFGITLINK = 0o160000
    if stat.S_ISREG(mode) or stat.S_ISLNK(mode):
        return "blob"
    elif stat.S_ISDIR(mode):
        return "tree"
    elif stat.S_IFMT(mode) == S_IFGITLINK: # submodule
        return "commit"

class ObjectMetadata:
    def __init__(self,object_type:str,content_length:int):
        self.type = object_type
        self.content_length = content_length

    def make_header(self) -> bytes:
        header = self.type + " " + str(self.content_length) + "\0"
        return header.encode()

class GitObjectMixin:
    @property
    def type_id(self) -> str:
        return self._metadata.type

    def hash(self) -> str:
        data = self.serialize()
        return util.hash_content(data)

    def write(self):
        data = self.serialize()
        util.store_raw_content(data)

class Blob(GitObjectMixin):
    def __init__(self,metadata:ObjectMetadata,content:bytes):
        self._metadata = metadata
        self._content = content

    def __str__(self):
        return self._content.decode()

    def serialize(self) -> bytes:
        header = self._metadata.make_header()
        data = header + self._content
        return data

    @staticmethod
    def from_content(content:bytes):
        object_type = "blob"
        content_length = len(content)
        metadata = ObjectMetadata(object_type,content_length)
        return Blob(metadata,content)

class TreeEntry:
    def __init__(self, mode:int, name:str, sha1:str):
        self.mode = mode
        self.name = name
        self.sha1 = sha1

    @property
    def object_type(self):
        return object_type_from_mode(self.mode)

    def __str__(self):
        return f"{self.mode:06o} {self.object_type} {self.sha1}\t{self.name}"

    def serialize(self) -> bytes:
        mode_b = f"{self.mode:o}".encode()
        name_b = self.name.encode() + b"\x00"
        sha1_b = bytes.fromhex(self.sha1)
        return mode_b + b" " + name_b + sha1_b

class Tree(GitObjectMixin):
    def __init__(self,metadata=None):
        self._metadata = metadata
        self._tree_entries = []

    def __iter__(self):
        return iter(self._tree_entries)

    def __str__(self):
        lst = []
        for e in self._tree_entries:
            lst.append(str(e))
        return "\n".join(lst)

    def serialize(self):
        data = b""
        for e in self._tree_entries:
            data += e.serialize()
        length = len(data)
        if self._metadata:
            assert(self._metadata.content_length == length)
        else:
            self._metadata = ObjectMetadata("tree",length)
        header = self._metadata.make_header()
        return header + data

    def add_entry(self,tree_entry):
        self._tree_entries.append(tree_entry)

AuthorInfo = namedtuple("AuthorInfo", ["name","email","unix_time","time_zone"])

class Commit(GitObjectMixin):
    def __init__(self,metadata,tree,parents,author_info,committer_info,commit_message):
        self._metadata = metadata
        self._tree = tree
        self._parents = parents
        self._author = author_info
        self._committer = committer_info
        self._commit_message = commit_message

    def __str__(self):
        s = ""
        s += f"tree {self._tree}\n"
        for parent in self._parents:
            s += f"parent {self._tree}\n"
        def format_author(author):
            return f"{author.name} <{author.email}> {author.unix_time} {author.time_zone}"
        s += f"author {format_author(self._author)}\n"
        s += f"committer {format_author(self._committer)}\n"
        s += "\n"
        s += self._commit_message
        return s

class ObjectParser:

    def find_char(self,char:bytes):
        """find first occurence of char after current head position"""
        assert(len(char) == 1)
        pos = self._data.find(char,self._head)
        return pos

    def read_until(self,char:bytes,*,discard=True):
        pos = self.find_char(char)
        sub = self._data[self._head:pos]
        if discard:
            self._head = pos + 1
        return sub

    def read_n_bytes(self,n:int):
        sub = self._data[self._head:self._head + n]
        self._head += n
        return sub

    def read_all(self):
        sub = self._data[self._head:]
        self._head = len(self._data)
        return sub

    def eof(self):
        return self._head >= len(self._data)

    def check_type(self) -> str:
        types = ["blob", "tree", "commit"]
        assert(self._head == 0)
        object_type = self.read_until(b" ").decode()
        if object_type in types:
            return object_type
        else:
            raise UnknownObjectTypeError

    def check_content_length(self):
        content_length = int(self.read_until(b"\x00"))
        # check remaining content length
        assert(len(self._data) == self._head + content_length)
        return content_length

    def parse_metadata(self):
        # check type
        object_type = self.check_type()
        # check content length
        content_length = self.check_content_length()
        # make metadata
        metadata = ObjectMetadata(object_type,content_length)
        return metadata

    def parse_tree_entry(self):
        # read file mode
        mode = int(self.read_until(b" "),base=8)
        # read filename
        filename = self.read_until(b"\x00").decode()
        # read sha1
        sha1_length = 20
        sha1 = self.read_n_bytes(sha1_length).hex()
        return TreeEntry(mode,filename,sha1)

    def parse_tree(self,metadata):
        tree = Tree(metadata)
        while(not self.eof()):
            entry = self.parse_tree_entry()
            tree.add_entry(entry)
        return tree

    def parse_commit(self,metadata):

        def skip_char(char:bytes):
            assert(len(char) == 1)
            assert(self._data.find(char,self._head) == self._head)
            self._head += 1
            
        def check_entry_name(name):
            entry_name = self.read_until(b" ").decode()
            if (entry_name == name):
                return True
            else:
                self._head -= (len(entry_name) + 1) # undo
                return False

        def parse_author():
            author = self.read_until(b"<")[:-1].decode() # strip trailing space
            email = self.read_until(b">").decode()
            skip_char(b" ")
            unix_time = int(self.read_until(b" "))
            time_zone = self.read_until(b"\n").decode()
            author_info = AuthorInfo(author,email,unix_time,time_zone)
            return author_info

        # parse tree entry
        assert(check_entry_name("tree"))
        tree = self.read_until(b"\n").decode()
        # parse parents
        parents = []
        while (check_entry_name("parent")):
            parent = self.read_until(b"\n").decode()
            parents.append(parent)
        # parse author/committer info
        assert(check_entry_name("author"))
        author_info = parse_author()
        assert(check_entry_name("committer"))
        committer_info = parse_author()
        # parse commit_message
        skip_char(b"\n")
        commit_message = self.read_all().decode()
        # make commit object
        commit = Commit(
                metadata,
                tree,
                parents,
                author_info,
                committer_info,
                commit_message
                )
        return commit

    def parse(self,raw_content:bytes,*,metadata_only=False):
        self._data = raw_content
        self._head = 0
        metadata = self.parse_metadata()
        if (metadata_only):
            return metadata
        if metadata.type == "blob":
            content = self.read_all()
            return Blob(metadata,content)
        elif metadata.type == "tree":
            tree = self.parse_tree(metadata)
            return tree
        elif metadata.type == "commit":
            commit = self.parse_commit(metadata)
            return commit
        else:
            raise UnknownObjectTypeError

def parse_object(raw_content:bytes,**kwargs):
    return ObjectParser().parse(raw_content,**kwargs)

def load_object(sha1:str):
    full_sha1 = paths.find_object(sha1)
    raw = util.load_raw_content(full_sha1)
    obj = parse_object(raw)
    return obj
