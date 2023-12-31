import time
from collections import namedtuple

from . import paths
from . import util
from .mode import object_type_from_mode
from .config import get_config


class UnknownObjectTypeError(BaseException):
    pass


class ObjectMetadata:
    def __init__(self, object_type: str, content_length: int):
        self.type = object_type
        self.content_length = content_length

    def make_header(self) -> bytes:
        header = self.type + " " + str(self.content_length) + "\0"
        return header.encode()


class GitObjectMixin:
    def make_store(self):
        data = self.serialize()
        metadata = ObjectMetadata(self.type_id, len(data))
        header = metadata.make_header()
        return header + data

    def hash(self) -> str:
        store = self.make_store()
        return util.hash_content(store)

    def write(self):
        store = self.make_store()
        util.store_raw_content(store)


class Blob(GitObjectMixin):
    def __init__(self, content: bytes):
        self._content = content

    def __str__(self):
        return self._content.decode()

    @property
    def type_id(self):
        return "blob"

    def serialize(self) -> bytes:
        return self._content

    @staticmethod
    def from_content(content: bytes):
        return Blob(content)

    @staticmethod
    def from_path(path):
        with open(path, "rb") as f:
            content = f.read()
        return Blob.from_content(content)


class TreeEntry:
    def __init__(self, mode: int, name: str, sha1: str):
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
    def __init__(self):
        self._tree_entries = []

    def __iter__(self):
        return iter(self._tree_entries)

    @property
    def type_id(self):
        return "tree"

    def __str__(self):
        lst = []
        for e in self:
            lst.append(str(e))
        return "\n".join(lst)

    def serialize(self):
        data = b""
        for e in self:
            data += e.serialize()
        return data

    def add_entry(self, tree_entry):
        self._tree_entries.append(tree_entry)


AuthorInfo = namedtuple("AuthorInfo", ["name", "email", "unix_time", "time_zone"])


class Commit(GitObjectMixin):
    def __init__(
        self, tree, parents, author_info, committer_info, commit_message
    ):
        self._tree = tree
        self._parents = parents
        self._author = author_info
        self._committer = committer_info
        self._commit_message = commit_message

    def __str__(self):
        s = ""
        s += f"tree {self._tree}\n"
        for parent in self._parents:
            s += f"parent {parent}\n"

        def format_author(author):
            return (
                f"{author.name} <{author.email}> {author.unix_time} {author.time_zone}"
            )

        s += f"author {format_author(self._author)}\n"
        s += f"committer {format_author(self._committer)}\n"
        s += "\n"
        s += self._commit_message
        return s

    @property
    def type_id(self):
        return "commit"

    def serialize(self):
        content = str(self).encode()
        return content

    @staticmethod
    def from_tree(tree, parents, commit_message: str):
        parents = list(map(paths.find_object, parents))
        author = get_config("user", "name")
        email = get_config("user", "email")
        commit_time = int(time.time())
        time_zone = time.strftime("%z")
        author_info = AuthorInfo(author, email, commit_time, time_zone)
        committer_info = author_info
        commit_obj = Commit(
            tree, parents, author_info, committer_info, commit_message
        )
        return commit_obj


class ObjectParser:
    def find_char(self, char: bytes):
        """find first occurence of char after current head position"""
        assert len(char) == 1
        pos = self._data.find(char, self._head)
        return pos

    def read_until(self, char: bytes, *, discard=True):
        pos = self.find_char(char)
        sub = self._data[self._head : pos]
        if discard:
            self._head = pos + 1
        return sub

    def read_n_bytes(self, n: int):
        sub = self._data[self._head : self._head + n]
        self._head += n
        return sub

    def read_all(self):
        sub = self._data[self._head :]
        self._head = len(self._data)
        return sub

    def eof(self):
        return self._head >= len(self._data)

    def check_type(self) -> str:
        types = ["blob", "tree", "commit"]
        assert self._head == 0
        object_type = self.read_until(b" ").decode()
        if object_type in types:
            return object_type
        else:
            raise UnknownObjectTypeError

    def check_content_length(self):
        content_length = int(self.read_until(b"\x00"))
        # check remaining content length
        assert len(self._data) == self._head + content_length
        return content_length

    def parse_metadata(self):
        # check type
        object_type = self.check_type()
        # check content length
        content_length = self.check_content_length()
        # make metadata
        metadata = ObjectMetadata(object_type, content_length)
        return metadata

    def parse_tree_entry(self):
        # read file mode
        mode = int(self.read_until(b" "), base=8)
        # read filename
        filename = self.read_until(b"\x00").decode()
        # read sha1
        sha1_length = 20
        sha1 = self.read_n_bytes(sha1_length).hex()
        return TreeEntry(mode, filename, sha1)

    def parse_tree(self):
        tree = Tree()
        while not self.eof():
            entry = self.parse_tree_entry()
            tree.add_entry(entry)
        return tree

    def parse_commit(self):
        def skip_char(char: bytes):
            assert len(char) == 1
            assert self._data.find(char, self._head) == self._head
            self._head += 1

        def check_entry_name(name):
            entry_name = self.read_until(b" ").decode()
            if entry_name == name:
                return True
            else:
                self._head -= len(entry_name) + 1  # undo
                return False

        def parse_author():
            author = self.read_until(b"<")[:-1].decode()  # strip trailing space
            email = self.read_until(b">").decode()
            skip_char(b" ")
            unix_time = int(self.read_until(b" "))
            time_zone = self.read_until(b"\n").decode()
            author_info = AuthorInfo(author, email, unix_time, time_zone)
            return author_info

        # parse tree entry
        assert check_entry_name("tree")
        tree = self.read_until(b"\n").decode()
        # parse parents
        parents = []
        while check_entry_name("parent"):
            parent = self.read_until(b"\n").decode()
            parents.append(parent)
        # parse author/committer info
        assert check_entry_name("author")
        author_info = parse_author()
        assert check_entry_name("committer")
        committer_info = parse_author()
        # parse commit_message
        skip_char(b"\n")
        commit_message = self.read_all().decode()
        # make commit object
        commit = Commit(
            tree, parents, author_info, committer_info, commit_message
        )
        return commit

    def parse(self, raw_content: bytes, *, metadata_only=False):
        self._data = raw_content
        self._head = 0
        metadata = self.parse_metadata()
        if metadata_only:
            return metadata

        assert metadata.content_length == (len(self._data) - self._head)
        if metadata.type == "blob":
            content = self.read_all()
            return Blob(content)
        elif metadata.type == "tree":
            tree = self.parse_tree()
            return tree
        elif metadata.type == "commit":
            commit = self.parse_commit()
            return commit
        else:
            raise UnknownObjectTypeError


def parse_object(raw_content: bytes, **kwargs):
    return ObjectParser().parse(raw_content, **kwargs)


def load_object(sha1: str):
    full_sha1 = paths.find_object(sha1)
    raw = util.load_raw_content(full_sha1)
    obj = parse_object(raw)
    return obj
