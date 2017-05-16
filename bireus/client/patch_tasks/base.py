# coding=utf-8
import abc
import logging
import tempfile

from bireus.client.download_service import AbstractDownloadService
from bireus.client.notification_service import NotificationService
from bireus.shared import *
from bireus.shared.diff_head import DiffHead
from bireus.shared.diff_item import DiffItem
from bireus.shared.repository import ProtocolException

logger = logging.getLogger(__name__)


class PatchTask(abc.ABC):
    _patch_tasks = None

    def __init__(self, notification_service: NotificationService, download_service: AbstractDownloadService,
                 repository_url: str, repo_path: Path, patch_file: Path):
        self._notification_service = notification_service
        self._download_service = download_service
        self._url = repository_url
        self._repo_path = repo_path
        self._patch_file = patch_file
        self._target_version = None

    def run(self) -> None:
        # unpack the patch into a temp folder
        temp_root = self._repo_path.joinpath(".bireus").joinpath("__temp__")
        temp_root.mkdir(parents=True, exist_ok=True)
        tempdir = tempfile.TemporaryDirectory(dir=str(temp_root))
        unpack_archive(self._patch_file, tempdir.name)

        diff_head = DiffHead.load_json_file(Path(tempdir.name).joinpath('.bireus'))

        if diff_head.protocol != self.get_version():
            logger.error(".bireus protocol version %s doesn't match patcher task version %s", diff_head.protocol,
                         self.get_version())
            self._notification_service.error(".bireus protocol version %s doesn't match patcher task version %s" % (
                diff_head.protocol, self.get_version()))
            raise Exception(".bireus protocol version %s doesn't match patcher task version %s"
                            % (diff_head.protocol, self.get_version()))

        self._target_version = diff_head.target_version

        # begin the patching recursion
        # note: a DiffHead's first and only item is the top folder itself
        self.patch(diff_head.items[0], self._repo_path, Path(tempdir.name), False)

        intermediate_folder = Path(self._repo_path.parent.joinpath(self._repo_path.name + ".patched"))
        relative_temp_folder = Path(tempdir.name).relative_to(self._repo_path)
        move_file(self._repo_path, intermediate_folder)
        move_file(intermediate_folder.joinpath(relative_temp_folder), self._repo_path)
        self._repo_path.joinpath(".bireus").unlink()  # remove the patch descriptor
        move_file(intermediate_folder.joinpath(".bireus"), self._repo_path.joinpath(".bireus"))
        remove_folder(intermediate_folder)

    @classmethod
    def get_factory(cls, protocol: int):
        if cls._patch_tasks is None:
            cls._patch_tasks = dict()
            for patch_task_version in PatchTask.__subclasses__():
                cls._patch_tasks[patch_task_version.get_version()] = patch_task_version.create

        if protocol in cls._patch_tasks:
            return cls._patch_tasks[protocol]
        else:
            raise ProtocolException("Protocol version `%s` is not supported in this client version", protocol)

    @abc.abstractclassmethod
    def get_version(cls) -> int:
        pass

    @abc.abstractclassmethod
    def create(cls, notification_service: NotificationService, download_service: AbstractDownloadService, repository_url: str, repo_path: Path,
               patch_file: Path) -> 'PatchTask':
        """
        Abstract factory function for dynamic patcher initialization
        same params as in constructor!
        """
        pass

    @abc.abstractmethod
    def patch(self, diff: DiffItem, base_path: Path, patch_path: Path, inside_zip: bool = False) -> None:
        pass
