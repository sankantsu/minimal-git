# make file tree from plain path-names

import pathlib
from collections import namedtuple

from git_objects import TreeEntry, Tree
from staging import Index, parse_index

def get_logger():
    import logging
    return logging.getLogger(__name__)

logger = get_logger()

class FileTree:
    def __init__(self,path,children,existing_entry=None):
        self.path = path
        self.name = path.name
        self.children = []
        self._tree_entry = existing_entry
        for t in children:
            self.add_child(t)

    def add_child(self,tree):
        self.children.append(tree)

    def has_no_child(self):
        return len(self.children) == 0

    def to_git_tree(self):
        if self.has_no_child():
            raise ValueError
        git_tree = Tree()
        for child in self.children:
            git_tree.add_entry(child.to_tree_entry())
        # create if there are no corresponding tree object
        git_tree.write()
        return git_tree

    def to_tree_entry(self):
        if self._tree_entry:
            return self._tree_entry
        git_tree = self.to_git_tree()
        directory_mode = int("040000",base=8)
        self._tree_entry = TreeEntry(directory_mode,self.name,git_tree.hash())
        return self._tree_entry

    def write_tree_recursive(self):
        if self.has_no_child():
            return []
        for child in self.children:
            child.write_tree_recursive()
        top = self.to_git_tree()
        logger.debug(f"writing tree of {self.path} (hash={top.hash()})")
        logger.debug(str(top))
        return top

    # for debugging
    def print(self):
        def helper(tree):
            base = tree.path.name or "/"
            n_children = len(tree.children)
            if (n_children == 0):
                return [base]
            else:
                res = [base]
                for i,t in enumerate(tree.children):
                    indent = "| " if i != n_children - 1 else "  "
                    sub = helper(t)
                    first_line = "|_" + sub[0]
                    other_lines = list(map(lambda s: indent + s,sub[1:]))
                    indented = [first_line] + other_lines
                    res += indented
                return res

        s = "\n".join(helper(self))
        print(s)

# extract dir names from file paths
def directory_paths(paths):
    dirs = []
    def add_directories(path):
        par = path.parent
        if par not in dirs:
            dirs.append(par)
            add_directories(par)
    for path in paths:
        add_directories(path)
    return dirs

def build_file_tree_form_paths(paths,to_tree_entry):
    # sort descendants to ancestors
    paths = sorted(paths,key=lambda p: len(p.parts),reverse=True)
    # make tree structure in bottom up way
    trees = set()
    for p in paths:
        children = []
        for t in trees:
            if p == t.path.parent:
                children.append(t)
        if (len(children) == 0):
            trees.add(FileTree(p,[],existing_entry=to_tree_entry[p]))
        else:
            for t in children:
                trees.remove(t)
            tree = FileTree(p,sorted(children,key=lambda t: t.name))
            trees.add(tree)
    assert(len(trees) == 1) # only the repository root tree shold remain
    return next(iter(trees)) # returns first element

def index_to_file_tree(index:Index):
    to_existing_entry = {}
    paths = []
    for entry in index:
        path = pathlib.Path(entry.file_name)
        paths.append(path)
        to_existing_entry[path] = entry.to_tree_entry()
    paths += directory_paths(paths)
    file_tree = build_file_tree_form_paths(paths,to_existing_entry)
    return file_tree
