import filecmp
import os
import shutil
import zlib
from pathlib import Path
from typing import Union, Any


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


def compare_files(file1: Union[str, Path], file2: Union[str, Path]) -> bool:
    return filecmp.cmp(str(file1), str(file2), shallow=False)


def change_dir(path: Union[str, Path]) -> None:
    os.chdir(str(path))


def make_archive(basename: Union[str, Path], format: str, root_dir: Union[str, Path]):
    return shutil.make_archive(str(basename), format, str(root_dir))


def unpack_archive(filename: Union[str, Path], extract_dir: Union[str, Path], format: Any = None):
    return shutil.unpack_archive(str(filename), str(extract_dir), format)
