import filecmp
import json
import logging
import os
import shutil
import tempfile
import zipfile
import zlib

import bsdiff4

from server import get_subdirectories, get_files
from server.DiffHead import DiffHead
from server.DiffItem import DiffItem


class CompareTask(object):
    def __init__(self, name: str, base: str, target: str):
        self.logger = logging.getLogger('server.CompareTask')

        self.name = name
        self.base = base
        self.target = target

        self._basepath = os.path.join(self.name, self.base)
        self._targetpath = os.path.join(self.name, self.target)
        self._deltapath = os.path.join(self.name, self.base, '.delta_to', self.target)

    def generate_diff(self, write_deltafile: bool = True) -> DiffHead:
        self.logger.debug('Generating %s delta `%s` -> `%s`', self.name, self.base, self.target)
        self.logger.debug('working directory is `%s`', os.getcwd())

        if not os.path.exists(self._deltapath):
            os.makedirs(self._deltapath)

        bireus_head = DiffHead(repository=self.name,
                               base_version=self.base,
                               target_version=self.target)

        top_folder_diff = self._compare_directory('')

        bireus_head.items.extend(top_folder_diff.items)

        if write_deltafile:
            with open(os.path.join(self._deltapath, '.bireus'), 'w+') as diffFile:
                json.dump(bireus_head.to_dict(), diffFile)

            abs_delta_path = os.path.join(os.getcwd(), self._deltapath)
            shutil.make_archive(abs_delta_path, 'zip', abs_delta_path)  # .zip gets added to filename automatically
            shutil.rmtree(abs_delta_path)  # remove the delta folder, only the zipfile remains

        return bireus_head

    def _compare_directory(self, relative_path: str) -> DiffItem:
        self.logger.debug("_compare_directory for `%s`", relative_path)

        basepath = os.path.join(self._basepath, relative_path)
        targetpath = os.path.join(self._targetpath, relative_path)
        deltapath = os.path.join(self._deltapath, relative_path)

        subdirectories = set()
        subfiles = set()

        if os.path.exists(basepath):
            if os.path.exists(targetpath):
                action = 'delta'
                if not os.path.exists(deltapath):
                    os.mkdir(deltapath)

                subdirectories.update(get_subdirectories(targetpath))
                subfiles.update(get_files(targetpath))
            else:
                action = 'remove'

            subdirectories.update(get_subdirectories(basepath))
            subfiles.update(get_files(basepath))
        else:
            action = 'add'
            self._add_directory(os.path.join(relative_path))

            subdirectories.update(get_subdirectories(targetpath))
            subfiles.update(get_files(targetpath))

        result_diff = DiffItem(iotype='directory',
                               name=os.path.basename(relative_path),
                               action=action)  # type: DiffItem

        for dirname in subdirectories:
            result_diff.items.append(self._compare_directory(os.path.join(relative_path, dirname)))

        for file in subfiles:
            result_diff.items.append(self._compare_file(relative_path, file))

        return result_diff

    def _compare_file(self, relative_path: str, filename: str) -> DiffItem:
        self.logger.debug("_compare_file for `%s` in `%s`", filename, relative_path)

        result_diff = DiffItem(iotype='file',
                               name=filename)  # type: DiffItem

        basepath = os.path.join(self._basepath, relative_path, filename)
        targetpath = os.path.join(self._targetpath, relative_path, filename)
        deltapath = os.path.join(self._deltapath, relative_path, filename)

        if not os.path.exists(basepath):
            shutil.copy2(targetpath, deltapath)
            result_diff.action = 'add'
            result_diff.target_crc = self._crc32_from_file(targetpath)

        elif not os.path.exists(targetpath):
            result_diff.action = 'remove'
            result_diff.base_crc = self._crc32_from_file(basepath)

        elif filecmp.cmp(basepath, targetpath):
            result_diff.action = 'unchanged'
            result_diff.base_crc = result_diff.target_crc = self._crc32_from_file(targetpath)

        else:
            if zipfile.is_zipfile(basepath):
                result_diff.action = 'zipdelta'
                result_diff.base_crc = result_diff.target_crc = "#ZIPFILE"

                working_directory = os.getcwd()

                temp = tempfile.TemporaryDirectory(suffix='_dir', prefix='bireus_')
                os.chdir(temp.name)

                temp_basepath = self._basepath
                temp_targetpath = self._targetpath
                temp_deltapath = self._deltapath

                os.makedirs(temp_basepath)
                os.makedirs(temp_targetpath)
                os.makedirs(temp_deltapath)

                with zipfile.ZipFile(os.path.join(working_directory, basepath)) as baseZip:
                    baseZip.extractall(temp_basepath)

                with zipfile.ZipFile(os.path.join(working_directory, targetpath)) as targetZip:
                    targetZip.extractall(temp_targetpath)

                self.logger.debug("zipdelta required for `%s`", filename)
                zip_diff = CompareTask(self.name, self.base, self.target).generate_diff(False)
                shutil.copytree(temp_deltapath, os.path.join(working_directory, self._deltapath, filename))

                result_diff.items.extend(zip_diff.items)

                os.chdir(working_directory)
            else:
                result_diff.action = 'bsdiff'
                bsdiff4.file_diff(basepath, targetpath, deltapath)
                result_diff.target_crc = self._crc32_from_file(targetpath)
                result_diff.base_crc = self._crc32_from_file(basepath)

        return result_diff

    def _add_directory(self, relative_path: str) -> None:
        self.logger.debug("_add_directory for `%s`", relative_path)

        targetpath = os.path.join(self._targetpath, relative_path)
        deltapath = os.path.join(self._deltapath, relative_path)

        if not os.path.exists(deltapath):
            shutil.copytree(targetpath, deltapath)

    @staticmethod
    def _crc32_from_file(filepath) -> str:
        if os.path.getsize(filepath) > 0:
            with open(filepath, 'rb') as file:
                return hex(zlib.crc32(file.read()) & 0xffffffff)
        else:
            return "#EMPTY"
