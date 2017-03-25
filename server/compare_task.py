import json
import logging
import tempfile
import zipfile
from tempfile import TemporaryDirectory

import bsdiff4

from server import get_subdirectory_names, get_filenames
from shared import *
from shared import crc32_from_file
from shared.diff_head import DiffHead
from shared.diff_item import DiffItem


class CompareTask(object):
    def __init__(self, absolute_path: Path, name: str, base: str, target: str):
        self.logger = logging.getLogger('server.CompareTask')

        self._absolute_path = absolute_path
        self.name = name
        self.base = base
        self.target = target

        self._basepath = absolute_path.joinpath(self.base)  # type: Path
        self._targetpath = absolute_path.joinpath(self.target)  # type: Path
        self._deltapath = absolute_path.joinpath(self.base, '.delta_to', self.target)

    def generate_diff(self, write_deltafile: bool = True) -> DiffHead:
        self.logger.debug('Generating %s delta `%s` -> `%s`', self.name, self.base, self.target)

        self._deltapath.mkdir(parents=True, exist_ok=True)

        bireus_head = DiffHead(repository=self.name,
                               base_version=self.base,
                               target_version=self.target)

        top_folder_diff = self._compare_directory(Path(""))

        bireus_head.items.append(top_folder_diff)

        if write_deltafile:
            with self._deltapath.joinpath('.bireus').open(mode='w+') as diffFile:
                json.dump(bireus_head.to_dict(), diffFile)

            abs_delta_path = self._absolute_path.joinpath(self._deltapath)  # type: Path
            make_archive(self._absolute_path.joinpath('__patches__', '%s_to_%s' % (self.base, self.target)), 'xztar',
                         abs_delta_path)  # file extension gets added to filename automatically
            remove_folder(self._absolute_path.joinpath(self.base, '.delta_to'))

        return bireus_head

    def _compare_directory(self, relative_path: Path) -> DiffItem:
        self.logger.debug("_compare_directory for `%s`", relative_path)

        basepath = self._basepath.joinpath(relative_path)  # type: Path
        targetpath = self._targetpath.joinpath(relative_path)  # type: Path
        deltapath = self._deltapath.joinpath(relative_path)  # type: Path

        subdirectories = set()
        subfiles = set()

        if basepath.exists():
            if targetpath.exists():
                action = 'delta'
                deltapath.mkdir(exist_ok=True)
                subdirectories.update(get_subdirectory_names(targetpath))
                subfiles.update(get_filenames(targetpath))
            else:
                action = 'remove'

            subdirectories.update(get_subdirectory_names(basepath))
            subfiles.update(get_filenames(basepath))
        else:
            action = 'add'
            self._add_directory(relative_path)

            subdirectories.update(get_subdirectory_names(targetpath))
            subfiles.update(get_filenames(targetpath))

        result_diff = DiffItem(iotype='directory',
                               name=relative_path.name,
                               action=action,
                               base_crc='',
                               target_crc='')  # type: DiffItem

        for dirpath in subdirectories:
            result_diff.items.append(self._compare_directory(relative_path.joinpath(dirpath)))

        for file in subfiles:
            result_diff.items.append(self._compare_file(relative_path, file))

        return result_diff

    def _compare_file(self, relative_path: Path, file_path: str) -> DiffItem:
        self.logger.debug("_compare_file for `%s` in `%s`", file_path, relative_path)

        result_diff = DiffItem(iotype='file',
                               name=file_path,
                               base_crc='',
                               target_crc='')  # type: DiffItem

        basepath = self._basepath.joinpath(relative_path, file_path)
        targetpath = self._targetpath.joinpath(relative_path, file_path)
        deltapath = self._deltapath.joinpath(relative_path, file_path)

        if not basepath.exists():
            copy_file(targetpath, deltapath)
            result_diff.action = 'add'
            result_diff.target_crc = crc32_from_file(targetpath)

        elif not targetpath.exists():
            result_diff.action = 'remove'
            result_diff.base_crc = crc32_from_file(basepath)

        elif compare_files(basepath, targetpath):
            result_diff.action = 'unchanged'
            result_diff.base_crc = result_diff.target_crc = crc32_from_file(targetpath)

        else:
            if zipfile.is_zipfile(str(basepath)):
                result_diff.action = 'zipdelta'
                result_diff.base_crc = result_diff.target_crc = "#ZIPFILE"

                temp = tempfile.TemporaryDirectory(suffix='_dir', prefix='bireus_')  # type: TemporaryDirectory

                temp_abspath = Path(temp.name)
                temp_basepath = temp_abspath.joinpath(self._basepath.relative_to(self._absolute_path))
                temp_targetpath = temp_abspath.joinpath(self._targetpath.relative_to(self._absolute_path))
                temp_deltapath = temp_abspath.joinpath(self._deltapath.relative_to(self._absolute_path))

                temp_basepath.mkdir(parents=True, exist_ok=True)
                temp_targetpath.mkdir(parents=True, exist_ok=True)
                temp_deltapath.mkdir(parents=True, exist_ok=True)

                with zipfile.ZipFile(str(basepath)) as baseZip:
                    baseZip.extractall(str(temp_basepath))

                with zipfile.ZipFile(str(targetpath)) as targetZip:
                    targetZip.extractall(str(temp_targetpath))

                self.logger.debug("zipdelta required for `%s`", file_path)
                zip_diff = CompareTask(temp_abspath, self.name, self.base, self.target).generate_diff(False)
                copy_folder(temp_deltapath, self._absolute_path.joinpath(self._deltapath, file_path))

                result_diff.items.extend(zip_diff.items)
            else:
                result_diff.action = 'bsdiff'
                bsdiff4.file_diff(str(basepath), str(targetpath), str(deltapath))
                result_diff.target_crc = crc32_from_file(targetpath)
                result_diff.base_crc = crc32_from_file(basepath)

        return result_diff

    def _add_directory(self, relative_path: Path) -> None:
        self.logger.debug("_add_directory for `%s`", relative_path)

        targetpath = self._targetpath.joinpath(relative_path)
        deltapath = self._deltapath.joinpath(relative_path)

        if not deltapath.exists():
            copy_folder(targetpath, deltapath)
