# coding=utf-8
import logging
import tempfile
import zipfile
from urllib.parse import urljoin

import bsdiff4

from client.download_service import AbstractDownloadService
from shared import *
from shared.diff_head import DiffHead
from shared.diff_item import DiffItem

logger = logging.getLogger(__name__)


class CrcMismatchError(Exception):
    def __init__(self, file: Path, expected_crc: str, actual_crc: str):
        super(CrcMismatchError, self).__init__(self, 'File %s with wrong CRC code (expected=%s, actual=%s)' % (
            str(file), expected_crc, actual_crc))
        self.file = file
        self.expectedCrc = expected_crc
        self.actualCrc = actual_crc


class PatchTask(object):
    def __init__(self, download_service: AbstractDownloadService, repository_url: str, repo_base_path: Path,
                 relative_path: Path, patch_path: Path,
                 patch_info: DiffHead, diff_info: DiffItem, is_zipdelta: bool = False):
        self._download_service = download_service
        self._url = repository_url
        self._repo_base_path = repo_base_path
        self._relative_path = relative_path
        self._patch_info = patch_info
        self._patch_path = patch_path
        self._diff_info = diff_info
        self._is_zipdelta = is_zipdelta

    async def patch(self) -> None:
        if self._diff_info.type == 'file':
            try:
                await self._patch_file()
            except CrcMismatchError:
                if self._is_zipdelta:
                    logger.warning("CRC32-mismatch in ZipFile - raise upwards")
                    raise
                else:
                    logger.warning("CRC32-mismatch - downloading whole file instead")
                    await self._fallback_download()
        elif self._diff_info.type == 'directory':
            await self._patch_directory()

    async def _fallback_download(self):
        delta_source = urljoin(self._url, self._patch_info.target_version)
        if str(self._relative_path) != '.':
            delta_source = delta_source + '/' + str(self._relative_path)
        delta_source = delta_source + '/' + self._diff_info.name
        delta_dest = self._repo_base_path / self._relative_path / self._diff_info.name
        if delta_dest.exists():
            delta_dest.unlink()
        await self._download_service.download(delta_source, delta_dest)

    @property
    def repo_path(self) -> Path:
        return self._repo_base_path / self._relative_path

    @property
    def patch_path(self) -> Path:
        return self._patch_path / self._relative_path

    async def _patch_file(self) -> None:
        action = self._diff_info.action
        src_path = self.patch_path.joinpath(self._diff_info.name)
        dest_path = self.repo_path.joinpath(self._diff_info.name)
        logger.debug('Patching file -> action=%s,  file=%s', action, self._diff_info.name)

        if action == 'add':
            # in case files where added by hand
            if dest_path.exists():
                dest_path.unlink()

            copy_file(src_path, self.repo_path)
        elif action == 'bsdiff':
            target_crc_before_patch = crc32_from_file(dest_path)
            if self._diff_info.base_crc == target_crc_before_patch:
                logger.debug('Patching %s', dest_path)

                # using bsdiff4.file_patch_inplace not possible due to
                # maintainer fail: https://github.com/ilanschnell/bsdiff4/pull/5
                bsdiff4.file_patch(str(dest_path), str(dest_path) + ".patched", str(src_path))
                dest_path.unlink()
                move_file(str(dest_path) + ".patched", dest_path)
            else:
                raise CrcMismatchError(dest_path, str(self._diff_info.base_crc), str(target_crc_before_patch))

        elif action == 'remove':
            dest_path.unlink()
            return
        elif action == 'unchanged':
            return
        elif action == 'zipdelta':
            await self._patch_zipdelta()
            return

        target_crc_after_patch = crc32_from_file(dest_path)
        if self._diff_info.target_crc == target_crc_after_patch:
            logger.debug('CRC32 ok')
        else:
            raise CrcMismatchError(dest_path, self._diff_info.target_crc, target_crc_after_patch)

    async def _patch_directory(self) -> None:
        action = self._diff_info.action
        repo_folder = self.repo_path.joinpath(self._diff_info.name)
        patch_folder = self.patch_path.joinpath(self._diff_info.name)
        logger.debug('Patching directory -> action=%s,  folder=%s', action, self._diff_info.name)

        if action == 'add':
            if repo_folder.exists():
                remove_folder(repo_folder)
            copy_folder(patch_folder, repo_folder)
        elif action == 'remove':
            remove_folder(self.repo_path.joinpath(self._diff_info.name))
        elif action == 'delta':
            for diff_item in self._diff_info.items:
                if diff_item.type == 'file':
                    await PatchTask(self._download_service, self._url, self._repo_base_path,
                                    self._relative_path.joinpath(self._diff_info.name),
                                    self.patch_path, self._patch_info, diff_item, self._is_zipdelta).patch()
                elif diff_item.type == 'directory':
                    await PatchTask(self._download_service, self._url, self._repo_base_path,
                                    self._relative_path.joinpath(self._diff_info.name),
                                    self.patch_path, self._patch_info, diff_item, self._is_zipdelta).patch()

    async def _patch_zipdelta(self) -> None:
        # unpack the zip file in the current repo to temporary folder
        repo_zip_file = Path(self._repo_base_path / self._relative_path / Path(self._diff_info.name))

        zip_temp_folder = tempfile.TemporaryDirectory(prefix="bireus_", suffix='_ziprepo')
        zip_repo_path = Path(zip_temp_folder.name) / self._relative_path
        zip_repo_path.mkdir(parents=True, exist_ok=True)
        logger.debug('extracting zip to %s', zip_repo_path)
        with zipfile.ZipFile(str(repo_zip_file)) as zip_repo:
            zip_repo.extractall(str(zip_repo_path))

        # patch the zip-contents from current repo (in temporary folder)
        for diff_item in self._diff_info.items:
            if diff_item.type == 'file':
                await PatchTask(self._download_service, self._url, zip_repo_path, self._relative_path, self.patch_path,
                                self._patch_info, diff_item, True).patch()
            elif diff_item.type == 'directory':
                await PatchTask(self._download_service, self._url, zip_repo_path, self._relative_path,
                                self.patch_path / Path(self._diff_info.name), self._patch_info, diff_item, True).patch()

        # zip the patched content and replace original zipfile
        repo_zip_file.unlink()
        shutil.make_archive(str(repo_zip_file).replace('.zip', ''), 'zip', str(zip_repo_path))

        zip_temp_folder.cleanup()
