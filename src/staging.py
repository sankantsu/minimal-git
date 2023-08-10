import paths
from git_objects import TreeEntry, Tree

class IndexFormatError(BaseException):
    pass

class UnsupportedIndexVersionError(BaseException):
    pass

def to_binary(x:int):
    return f"{x:b}"

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
        self.stage = flags& IndexEntryFlags.stage_mask
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

class Index:

    def __init__(self):
        self._index_entries = []

    def __iter__(self):
        return iter(self._index_entries)

    def add_entry(self,entry:IndexEntry):
        self._index_entries.append(entry)

    def print(self,*,debug=False):
        for e in self._index_entries:
            e.print(debug=debug)

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
        if (sig != b"DIRC"):
            raise IndexFormatError

    def check_version(self):
        version = self.read_32_bit_int()
        if (version != 2):
            raise UnsupportedIndexVersionError
        return version

    def parse_index_entry(self):

        def calc_padding(name_len:int):
            return 8 - ((name_len + 6) % 8)

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
        self.read_n_bytes(calc_padding(name_len)) # skip null padding
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
