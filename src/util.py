import sys
import pathlib
import hashlib
import zlib

import paths

def die_error(*args,**kwargs):
    print(*args,file=sys.stderr,**kwargs)
    sys.exit(1)

def hash_content(content:bytes) -> str:
    sha1 = hashlib.sha1(content).hexdigest()
    return sha1

def load_raw_content(sha1:str) -> bytes:
    path = paths.make_object_path(sha1)
    with open(path,"rb") as f:
        content = f.read()
        decompressed_content = zlib.decompress(content)
    return decompressed_content

def store_raw_content(content:bytes):
    sha1 = hash_content(content)
    path = paths.make_object_path(sha1,make_dirs=True)
    if (path.exists()):
        return
    obj_compressed = zlib.compress(content)
    with open(path,"wb") as f:
        f.write(obj_compressed)
