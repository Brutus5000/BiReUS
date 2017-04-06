# coding=utf-8
import logging
import tempfile

import bsdiff4

from bireus.client.download_service import AbstractDownloadService
from bireus.client.patch_tasks.errors import CrcMismatchError
from bireus.client.patch_tasks.base import PatchTask
from bireus.shared import *
from bireus.shared.diff_item import DiffItem

logger = logging.getLogger(__name__)


class PatchTaskV1(PatchTask):
    @classmethod
    def get_version(cls) -> int:
        return 1

    @classmethod
    def create(cls, download_service: AbstractDownloadService, repository_url: str, repo_path: Path,
               patch_file: Path):
        return PatchTaskV1(download_service, repository_url, repo_path, patch_file)

    def patch(self, diff: DiffItem, base_path: Path, patch_path: Path, inside_zip: bool = False) -> None:
        for item in diff.items:
            if item.type == 'file':
                self.patch_file(item, base_path.joinpath(item.name), patch_path.joinpath(item.name), inside_zip)
            elif item.type == 'directory':
                self.patch_directory(item, base_path.joinpath(item.name), patch_path.joinpath(item.name),
                                           inside_zip)

    def patch_directory(self, diff: DiffItem, base_path: Path, patch_path: Path, inside_zip: bool) -> None:
        logger.debug('Patching directory -> action=%s,  folder=%s, relative path=%s', diff.action, diff.name,
                     str(patch_path))

        if diff.action == 'add':
            if base_path.exists():
                remove_folder(base_path)
            copy_folder(patch_path, base_path)
        elif diff.action == 'remove':
            remove_folder(base_path)
        elif diff.action == 'delta':
            self.patch(diff, base_path, patch_path, inside_zip)

    def patch_file(self, diff: DiffItem, base_path: Path, patch_path: Path, inside_zip: bool) -> None:
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
                    self._download_service.download(
                        self._url + "/" + self._target_version + "/" + str(
                            base_path.relative_to(self._repo_path)), base_path)

        elif diff.action == 'zipdelta':
            self.patch_zipdelta(diff, base_path, patch_path, inside_zip)

    def patch_zipdelta(self, diff: DiffItem, base_path: Path, patch_path: Path, inside_zip: bool) -> None:
        tempdir = tempfile.TemporaryDirectory(prefix="bireus_unzipped_")

        unpack_archive(base_path, tempdir.name, 'zip')
        self.patch_directory(diff, tempdir.name, patch_path.joinpath(diff.name), inside_zip=True)

        make_archive(str(base_path).replace('.zip', ''), 'zip', tempdir.name)

        tempdir.cleanup()
