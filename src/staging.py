import pathlib

import paths
from util import hash_content
from git_objects import TreeEntry, Tree, load_object

class IndexFormatError(BaseException):
    pass

class UnsupportedIndexVersionError(BaseException):
    pass

def to_binary(x:int):
    return f"{x:b}"

def int16_to_bytes(x):
    return x.to_bytes(length=2,byteorder="big")

def int32_to_bytes(x):
    return x.to_bytes(length=4,byteorder="big")

# only very limited support
class IndexEntryFlags:
    name_mask_len = 12
    name_mask = 0x0fff
    stage_mask = 0x3000
    extended = 0x4000
    assume_valid = 0x8000

class IndexEntry:

    def __init__(self,
                 ctime, ctime_nsec,
                 mtime, mtime_nsec,
                 dev, ino, mode,
                 uid, gid, file_size,
                 sha1, flags, file_name,
                 ):
        self.ctime = ctime
        self.ctime_nsec = ctime_nsec
        self.mtime = mtime
        self.mtime_nsec = mtime_nsec
        self.dev = dev
        self.ino = ino
        self.mode = mode
        self.uid = uid
        self.gid = gid
        self.file_size = file_size
        self.sha1 = sha1
        self.name_len = flags & IndexEntryFlags.name_mask
        self.stage = flags & IndexEntryFlags.stage_mask
        self.flags = flags & ~IndexEntryFlags.name_mask
        self.file_name = file_name

    def print(self,*,debug=False):
        print(f"{self.mode:06o} {self.sha1} {self.stage}\t{self.file_name}")
        if (debug):
            print(f"  ctime: {self.ctime}:{self.ctime_nsec}")
            print(f"  mtime: {self.mtime}:{self.mtime_nsec}")
            print(f"  dev: {self.dev}\tino: {self.ino}")
            print(f"  uid: {self.uid}\tgid: {self.gid}")
            print(f"  size: {self.file_size}\tflags: {self.flags:x}")

    def to_tree_entry(self):
        basename = paths.basename(self.file_name)
        return TreeEntry(self.mode,basename,self.sha1)

    def to_bytes(self):
        store = b""
        store += int32_to_bytes(self.ctime)
        store += int32_to_bytes(self.ctime_nsec)
        store += int32_to_bytes(self.mtime)
        store += int32_to_bytes(self.mtime_nsec)
        store += int32_to_bytes(self.dev)
        store += int32_to_bytes(self.ino)
        store += int32_to_bytes(self.mode)
        store += int32_to_bytes(self.uid)
        store += int32_to_bytes(self.gid)
        store += int32_to_bytes(self.file_size)
        store += bytes.fromhex(self.sha1)
        store += int16_to_bytes(self.flags | self.name_len)
        store += self.file_name.encode()
        padding = b"\x00" * IndexEntry.calc_padding(self.name_len)
        store += padding
        return store

    @staticmethod
    def from_tree_entry(tree_entry,prefix=pathlib.Path()):
        mode = tree_entry.mode
        name = str(prefix / tree_entry.name)
        sha1 = tree_entry.sha1
        index_entry = IndexEntry(
                ctime=0, ctime_nsec=0,
                mtime=0, mtime_nsec=0,
                dev=0, ino=0, mode=mode,
                uid=0, gid=0, file_size=0,
                sha1=sha1, flags=0,
                file_name=name
                )
        index_entry.name_len = len(index_entry.file_name)
        return index_entry

    @staticmethod
    def calc_padding(name_len:int):
        return 8 - ((name_len + 6) % 8)

class Index:
    SIGNATURE = b"DIRC"

    def __init__(self):
        self._index_entries = []

    def __iter__(self):
        return iter(self._index_entries)

    def __len__(self):
        return len(self._index_entries)

    def add_entry(self,entry:IndexEntry):
        self._index_entries.append(entry)

    def sort_entries(self):
        self._index_entries = sorted(self._index_entries,key=lambda e:e.file_name)

    def print(self,*,debug=False):
        for e in self._index_entries:
            e.print(debug=debug)

    def version(self):
        return 2

    def to_bytes(self):
        store = b""
        store += Index.SIGNATURE
        store += int32_to_bytes(self.version())
        store += int32_to_bytes(len(self))
        for entry in self:
            store += entry.to_bytes()
        checksum = bytes.fromhex(hash_content(store))
        store += checksum
        return store

    def write(self):
        index_file = paths.find_index_file()
        with open(index_file,"wb") as f:
            content = self.to_bytes()
            f.write(content)

    @staticmethod
    def from_tree(tree:Tree, prefix=pathlib.Path(".")):
        index = Index()
        for tree_entry in tree:
            if tree_entry.object_type == "tree":
                subtree = load_object(tree_entry.sha1)
                sub_entries = Index.from_tree(subtree,prefix / tree_entry.name)
                for e in sub_entries:
                    index.add_entry(e)
            else:
                index_entry = IndexEntry.from_tree_entry(tree_entry,prefix)
                index.add_entry(index_entry)
        index.sort_entries()
        return index

class IndexParser:

    def read_n_bytes(self,n:int):
        sub = self._data[self._head:self._head+n]
        self._head += n
        return sub

    def read_16_bit_int(self):
        raw = self.read_n_bytes(2)
        val = int.from_bytes(raw,byteorder="big")
        return val

    def read_32_bit_int(self):
        raw = self.read_n_bytes(4)
        val = int.from_bytes(raw,byteorder="big")
        return val

    def check_signature(self):
        assert(self._head == 0)
        sig = self.read_n_bytes(4)
        if (sig != Index.SIGNATURE):
            raise IndexFormatError

    def check_version(self):
        version = self.read_32_bit_int()
        if (version != 2):
            raise UnsupportedIndexVersionError
        return version

    def parse_index_entry(self):

        ctime = self.read_32_bit_int()
        ctime_nsec = self.read_32_bit_int()
        mtime = self.read_32_bit_int()
        mtime_nsec = self.read_32_bit_int()
        dev = self.read_32_bit_int()
        ino = self.read_32_bit_int()
        mode = self.read_32_bit_int()
        uid = self.read_32_bit_int()
        gid = self.read_32_bit_int()
        file_size = self.read_32_bit_int()
        sha1 = self.read_n_bytes(20).hex()
        flags = self.read_16_bit_int()
        name_len = flags & IndexEntryFlags.name_mask
        file_name = self.read_n_bytes(name_len).decode()
        self.read_n_bytes(IndexEntry.calc_padding(name_len)) # skip null padding
        index_entry = IndexEntry(
                ctime, ctime_nsec,
                mtime, mtime_nsec,
                dev, ino, mode,
                uid, gid, file_size,
                sha1, flags, file_name,
                )
        return index_entry

    def parse(self,raw_content:bytes):
        self._data = raw_content
        self._head = 0
        self.check_signature()
        version = self.check_version()
        num_entry = self.read_32_bit_int()
        index = Index()
        for _ in range(num_entry):
            entry = self.parse_index_entry()
            index.add_entry(entry)
        return index

def parse_index():
    index_file = paths.find_index_file()
    with open(index_file,"rb") as f:
        raw = f.read()
        parser = IndexParser()
        index = parser.parse(raw)
        return index
