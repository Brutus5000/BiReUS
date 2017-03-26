# coding=utf-8
import logging
import tempfile

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
    def __init__(self, download_service: AbstractDownloadService, repository_url: str, repo_path: Path,
                 patch_file: Path):
        self._download_service = download_service
        self._url = repository_url
        self._repo_path = repo_path
        self._patch_file = patch_file
        self._target_version = None

    async def run(self) -> None:
        # unpack the patch into a temp folder
        tempdir = tempfile.TemporaryDirectory(prefix="bireus_patch_")
        unpack_archive(self._patch_file, tempdir.name)

        diff_head = DiffHead.load_json_file(Path(tempdir.name).joinpath('.bireus'))
        self._target_version = diff_head.target_version

        # begin the patching recursion
        # note: a DiffHead's first and only item is the top folder itself
        await self.patch(diff_head.items[0], self._repo_path, Path(tempdir.name), False)

        tempdir.cleanup()

    async def patch(self, diff: DiffItem, base_path: Path, patch_path: Path, inside_zip: bool = False) -> None:
        for item in diff.items:
            if item.type == 'file':
                await self.patch_file(item, base_path.joinpath(item.name), patch_path.joinpath(item.name), inside_zip)
            elif item.type == 'directory':
                await self.patch_directory(item, base_path.joinpath(item.name), patch_path.joinpath(item.name),
                                           inside_zip)

    async def patch_directory(self, diff: DiffItem, base_path: Path, patch_path: Path, inside_zip: bool) -> None:
        logger.debug('Patching directory -> action=%s,  folder=%s, relative path=%s', diff.action, diff.name,
                     str(patch_path))

        if diff.action == 'add':
            if base_path.exists():
                remove_folder(base_path)
            copy_folder(patch_path, base_path)
        elif diff.action == 'remove':
            remove_folder(base_path)
        elif diff.action == 'delta':
            await self.patch(diff, base_path, patch_path, inside_zip)

    async def patch_file(self, diff: DiffItem, base_path: Path, patch_path: Path, inside_zip: bool) -> None:
        logger.debug('Patching file -> action=%s,  file=%s, path=%s', diff.action, diff.name, str(base_path))

        if diff.action == 'add':
            if base_path.exists():
                base_path.unlink()
            copy_file(patch_path, base_path)
        elif diff.action == 'remove':
            base_path.unlink()
        elif diff.action == 'bsdiff':
            try:
                crc_before_patching = crc32_from_file(base_path)
                if diff.base_crc == crc_before_patching:
                    # using bsdiff4.file_patch_inplace not possible until 1.1.5
                    bsdiff4.file_patch(str(base_path), str(base_path) + ".patched", str(patch_path))
                    base_path.unlink()
                    move_file(str(base_path) + ".patched", base_path)

                    crc_after_patching = crc32_from_file(base_path)
                    if diff.target_crc != crc_after_patching:
                        logger.error("Crc mismatch after patching in %s (expected=%s, actual=%s)",
                                     str(base_path), diff.target_crc, crc_before_patching)
                        raise CrcMismatchError(base_path, diff.base_crc, crc_before_patching)
                else:
                    logger.error("Crc mismatch in base file %s (expected=%s, actual=%s), patching aborted",
                                 str(base_path), diff.base_crc, crc_before_patching)
                    raise CrcMismatchError(base_path, diff.base_crc, crc_before_patching)
            except CrcMismatchError:
                if inside_zip:
                    raise
                else:
                    logger.info("Emergency fallback: download %s from original source", base_path)
                    await self._download_service.download(
                        self._url + "/" + self._target_version + "/" + str(
                            base_path.relative_to(self._repo_path)), base_path)

        elif diff.action == 'zipdelta':
            await self.patch_zipdelta(diff, base_path, patch_path, inside_zip)

    async def patch_zipdelta(self, diff: DiffItem, base_path: Path, patch_path: Path, inside_zip: bool) -> None:
        tempdir = tempfile.TemporaryDirectory(prefix="bireus_unzipped_")

        unpack_archive(base_path, tempdir.name, 'zip')
        await self.patch_directory(diff, tempdir.name, patch_path.joinpath(diff.name), inside_zip=True)

        make_archive(str(base_path).replace('.zip', ''), 'zip', tempdir.name)

        tempdir.cleanup()
