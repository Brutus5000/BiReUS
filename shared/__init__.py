import os
import shutil
import zlib
from pathlib import Path
from typing import Union


def crc32_from_file(filepath: Union[str, Path]) -> str:
    if os.path.getsize(str(filepath)) > 0:
        with open(str(filepath), 'rb') as file:
            return hex(zlib.crc32(file.read()) & 0xffffffff)
    else:
        return "#EMPTY"


def copy_file(source: Union[str, Path], dest: Union[str, Path]) -> None:
    shutil.copy(str(source), str(dest))


def copy_folder(source: Union[str, Path], dest: Union[str, Path]) -> None:
    shutil.copytree(str(source), str(dest))


def remove_folder(path: Union[str, Path]) -> None:
    shutil.rmtree(str(path))


def move_file(src: Union[str, Path], dst: Union[str, Path]) -> None:
    shutil.move(str(src), str(dst))
