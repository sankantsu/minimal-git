import stat

S_IFGITLINK = 0o160000 # submodule

def is_regular(mode:int):
    return stat.S_ISREG(mode)

def is_executable(mode:int):
    return mode & 0o100

def is_dir(mode:int):
    return stat.S_ISDIR(mode)

def is_link(mode:int):
    return stat.S_ISLNK(mode)

def is_gitlink(mode:int):
    return stat.S_IFMT(mode) == S_IFGITLINK

def object_type_from_mode(mode:int):
    if is_regular(mode) or is_link(mode):
        return "blob"
    elif is_dir(mode):
        return "tree"
    elif is_gitlink(mode):
        return "commit"
    else:
        raise ValueError("unknown mode")

def normalize_mode(mode:int):
    if is_regular(mode):
        if is_executable(mode):
            return stat.S_IFREG | 0o755
        else:
            return stat.S_IFREG | 0o644
    elif is_dir(mode):
        return stat.S_IFDIR
    elif is_link(mode):
        return stat.S_IFLNK
    elif is_gitlink(mode):
        return S_IFGITLINK
    else:
        raise ValueError("unknown mode")
