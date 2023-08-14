# use configparser to approximate gitconfig format

import os
import pathlib
from configparser import ConfigParser

import paths


def get_config(section, key):
    config_file_local = paths.find_git_root() / "config"
    config_file_global = pathlib.Path(os.environ["HOME"]) / ".gitconfig"

    config_local = ConfigParser()
    config_local.read(config_file_local)

    config_global = ConfigParser()
    config_global.read(config_file_global)

    try:
        val = config_local[section][key]
    except KeyError:
        try:
            val = config_global[section][key]
        except KeyError:
            val = None
    return val
