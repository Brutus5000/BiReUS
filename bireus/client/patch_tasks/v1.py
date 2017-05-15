# coding=utf-8
import logging
import tempfile

import bsdiff4

from bireus.client.download_service import AbstractDownloadService
from bireus.client.notification_service import NotificationService
from bireus.client.patch_tasks.base import PatchTask
from bireus.client.patch_tasks.errors import CrcMismatchError
from bireus.shared import *
from bireus.shared.diff_item import DiffItem

logger = logging.getLogger(__name__)


class PatchTaskV1(PatchTask):
    @classmethod
    def get_version(cls) -> int:
        return 1

    @classmethod
    def create(cls, notification_service: NotificationService, download_service: AbstractDownloadService,
               repository_url: str, repo_path: Path, patch_file: Path):
        logger.debug(
            "Create PatchTask v1 (download_service=`%s`, repository_url=`%s`, repo_path=`%s`, patch_file=`%s`",
            repr(download_service), repr(repository_url), repr(repo_path), repr(patch_file))
        return PatchTaskV1(notification_service, download_service, repository_url, repo_path, patch_file)

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
        self._notification_service.begin_patching_directory(base_path)

        if diff.action == 'add':
            if base_path.exists():
                remove_folder(base_path)
            copy_folder(patch_path, base_path)
        elif diff.action == 'remove':
            remove_folder(base_path)
        elif diff.action == 'delta':
            self.patch(diff, base_path, patch_path, inside_zip)

        self._notification_service.finish_patching_directory(base_path)

    def patch_file(self, diff: DiffItem, base_path: Path, patch_path: Path, inside_zip: bool) -> None:
        logger.debug('Patching file -> action=%s,  file=%s, path=%s', diff.action, diff.name, str(base_path))

        if diff.action == 'add':
            self._notification_service.begin_adding_file(base_path)
            if base_path.exists():
                base_path.unlink()
            copy_file(patch_path, base_path)
            self._notification_service.finish_adding_file(base_path)
        elif diff.action == 'remove':
            self._notification_service.begin_removing_file(base_path)
            base_path.unlink()
            self._notification_service.finish_removing_file(base_path)
        elif diff.action == 'bsdiff':
            self._notification_service.begin_patching_file(base_path)

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
                        self._notification_service.crc_mismatch(base_path)
                        raise CrcMismatchError(base_path, diff.base_crc, crc_before_patching)
                    else:
                        self._notification_service.finish_patching_file(base_path)
                else:
                    logger.error("Crc mismatch in base file %s (expected=%s, actual=%s), patching aborted",
                                 str(base_path), diff.base_crc, crc_before_patching)
                    self._notification_service.crc_mismatch(base_path)
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
        self.patch(diff, Path(tempdir.name), patch_path, inside_zip=True)

        base_path.unlink()
        make_archive(str(base_path), 'zip', tempdir.name)
        move_file(str(base_path) + ".zip", base_path)

        tempdir.cleanup()
