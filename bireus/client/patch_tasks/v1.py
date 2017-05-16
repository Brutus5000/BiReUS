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
            # do nothing: the new files are already in the patch_path
            pass
        elif diff.action == 'remove':
            # do nothing: the files don't exist in the patch_path
            pass
        elif diff.action == 'delta':
            self.patch(diff, base_path, patch_path, inside_zip)

        self._notification_service.finish_patching_directory(base_path)

    def patch_file(self, diff: DiffItem, base_path: Path, patch_path: Path, inside_zip: bool) -> None:
        logger.debug('Patching file -> action=%s,  file=%s, path=%s', diff.action, diff.name, str(base_path))

        if diff.action == 'add':
            # do nothing: the new files are already in the patchPath
            pass
        elif diff.action == 'remove':
            # do nothing: the files don't exist in the patchPath
            pass
        elif diff.action == 'zipdelta':
            self.patch_zipdelta(diff, base_path, patch_path)
        elif diff.action == 'bsdiff':
            self._notification_service.begin_patching_file(base_path)

            # apply the patch onto a temporary file and replace the file in patchPath
            # if checksum does not fit, load file from server and save in patchPath

            try:
                crc_before_patching = crc32_from_file(base_path)
                if diff.base_crc == crc_before_patching:
                    # using bsdiff4.file_patch_inplace not possible until 1.1.5
                    bsdiff4.file_patch(str(base_path), str(patch_path) + ".patched", str(patch_path))
                    patch_path.unlink()
                    move_file(str(patch_path) + ".patched", patch_path)

                    crc_after_patching = crc32_from_file(patch_path)
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
                            base_path.relative_to(self._repo_path)), patch_path)
        elif diff.action == 'unchanged':
            copy_file(base_path, patch_path)

    def patch_zipdelta(self, diff: DiffItem, base_path: Path, patch_path: Path) -> None:
        # we need a temporary folder to extract the zip content from the base files
        temp_root = self._repo_path.joinpath(".bireus").joinpath("__temp__")
        temp_root.mkdir(parents=True, exist_ok=True)
        tempdir = tempfile.TemporaryDirectory(prefix="bireus_unzipped_", dir=str(temp_root))

        # extract the original files, attention: the patch files aren't zipped anymore
        logger.debug("Extracting files to %s", str(temp_root))
        unpack_archive(base_path, tempdir.name, 'zip')

        # now we can start the patching
        self.patch(diff, Path(tempdir.name), patch_path, inside_zip=True)

        # the patched files are now in patchPath
        # therefore we can remove the temporaryFolder
        logger.debug("Removing the temporary base folder {}", str(patch_path))
        tempdir.cleanup()

        # patch_path is a folder with the patch files but is supposed to be the zip file,
        # therefore we rename the folder for a second before compressing
        logger.debug("Re-compressing files at {}", str(patch_path))
        intermediate_folder = Path(str(patch_path) + ".patched")
        patch_path.rename(intermediate_folder)

        make_archive(str(patch_path), 'zip', str(intermediate_folder))
        move_file(str(patch_path) + ".zip", patch_path)
        remove_folder(intermediate_folder)
