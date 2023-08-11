import pathlib

def basename(path:str):
    p = pathlib.Path(path)
    return p.name

# repository structure

class NotGitRepositoryError(BaseException):
    pass

git_root = ".git"

def find_repository_root(cur=None):
    cur = cur or pathlib.Path(".").resolve()
    path = cur / git_root
    if (path.is_dir()):
        return cur
    else:
        parent = cur.parent
        if (parent == cur):
            raise NotGitRepositoryError("current directory is not a git repository")
        return find_repository_root(parent)

def find_git_root():
    return find_repository_root() / git_root

def find_object_dir():
    object_dir = pathlib.Path("objects/")
    return find_git_root() / object_dir

def find_index_file():
    index_file = pathlib.Path("index")
    return find_git_root() / index_file

def get_cwd_relative():
    repository_root = find_repository_root()
    cwd = pathlib.Path.cwd()
    return cwd.relative_to(repository_root)

# sha1 object path

class SHA1PrefixTooShortError(BaseException):
    pass

class UmbiguousSHA1PrefixError(BaseException):
    pass

class SHA1NotFoundError(BaseException):
    pass

def extract_sha1(object_path:pathlib.Path):
    posix_path = object_path.as_posix()
    path_elements = posix_path.split("/")
    sha1_elements = path_elements[-2:]
    sha1 = "".join(sha1_elements)
    return sha1

def list_objects():
    objects_root = find_object_dir()
    it = pathlib.Path(objects_root).rglob("*")
    objects = (f for f in it if f.is_file())
    sha1_list = list(map(extract_sha1,objects))
    return sha1_list

def find_object(sha1_prefix:str):
    minimum_prefix_length = 4
    if len(sha1_prefix) < minimum_prefix_length:
        raise SHA1PrefixTooShortError
    sha1_list = list_objects()
    candidates = []
    for sha1 in sha1_list:
        if sha1.startswith(sha1_prefix):
            candidates.append(sha1)
    if (len(candidates) == 0):
        raise SHA1NotFoundError
    if (len(candidates) >= 2):
        raise UmbiguousSHA1PrefixError
    sha1 = candidates[0]
    return sha1

def make_object_path(sha1:str,*,make_dirs=False) -> str:
    dir_name_length = 2
    dir_name = find_object_dir() / pathlib.Path(sha1[:dir_name_length])
    if make_dirs:
        dir_name.mkdir(parents=True,exist_ok=True)
    file = pathlib.Path(sha1[dir_name_length:])
    path = dir_name / file
    return path
