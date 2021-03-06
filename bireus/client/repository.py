# coding=utf-8
import json
import logging
import tempfile
from logging.handlers import RotatingFileHandler

import networkx

from bireus.client.download_service import AbstractDownloadService, BasicDownloadService, DownloadError
from bireus.client.notification_service import NotificationService
from bireus.client.patch_tasks.base import PatchTask
from bireus.shared import *
from bireus.shared.repository import BaseRepository

logger = logging.getLogger(__name__)
logging_configured = False


def configure_logging(logfile: str):
    global logging_configured

    if not logging_configured:
        root = logging.getLogger("bireus")
        root.setLevel(logging.DEBUG)

        handler = RotatingFileHandler(logfile, maxBytes=5000000, backupCount=5)
        formatter = logging.Formatter('%(asctime)s - %(name)-30s - %(levelname)-5s - %(message)s')
        handler.setFormatter(formatter)
        root.addHandler(handler)

        logging_configured = True


class CheckoutError(Exception):
    pass


class ClientRepository(BaseRepository):
    def __init__(self, absolute_path: Path, download_service: AbstractDownloadService = None,
                 file_logging: bool = True):
        super().__init__(absolute_path)

        if file_logging:
            configure_logging(str(absolute_path.joinpath(".bireus", "activity.log")))

        self._patch_task_factory = PatchTask.get_factory(self.protocol)

        if download_service is None:
            logger.debug("Using BasicDownloadService")
            self._download_service = BasicDownloadService()
        else:
            self._download_service = download_service

        self._notification_service = NotificationService(self)

        logger.info("%s initialized, current version: %s", self.name, self.current_version)

    @property
    def notification_service(self):
        return self._notification_service

    @notification_service.setter
    def notification_service(self, value):
        logger.debug("NotificationService replaced with %s", repr(value))
        self._notification_service = value

    @property
    def info_path(self) -> Path:
        return self._absolute_path.joinpath('.bireus', 'info.json')

    @property
    def version_graph_path(self) -> Path:
        return self._absolute_path.joinpath('.bireus', 'versions.gml')

    def get_patch_path(self, version_from: str, version_to: str) -> Path:
        return self._absolute_path.joinpath('.bireus', '%s_to_%s.tar.xz' % (version_from, version_to))

    @property
    def current_version(self) -> str:
        return self._metadata['current_version']

    @property
    def url(self) -> str:
        return self._metadata['url']

    def checkout_latest(self) -> None:
        try:
            self._update_repo_info()
        except DownloadError:
            logger.warning("Remote repository unreachable, use local instead")

        self.checkout_version(self.latest_version)

    def _update_repo_info(self) -> None:
        info_json = self._download_service.read(self.url + '/info.json')
        info_json = json.loads(info_json.decode())

        if info_json['latest_version'] != self.latest_version:
            self._metadata = info_json
            with self.info_path.open('w') as info_file:
                json.dump(self._metadata, info_file)
            self._download_service.download(self.url + '/versions.gml', self.version_graph_path)
            self.version_graph = networkx.read_gml(str(self.version_graph_path))

    def checkout_version(self, version: str) -> None:
        logger.info("Checking out version %s (current version %s)", version, self.current_version)
        self._notification_service.begin_checkout_version(version)

        if self.current_version == version:
            logger.info("Version `%s` is already checked out", version)
            self._notification_service.checked_out_already()
            return

        if not self._check_version_exists(version):
            logger.error("Version `%s` is not listed on server", version)
            self._notification_service.version_unknown(version)
            raise CheckoutError("Version `%s` is not listed on server", version)

        try:
            patch_path = networkx.shortest_path(self.version_graph, self.current_version, version)
        except networkx.NetworkXNoPath:
            logger.error("No valid patch path from %s to %s" % (self.current_version, version))
            self._notification_service.no_patch_path(version)
            raise CheckoutError("No valid patch path from %s to %s" % (self.current_version, version))

        logger.debug("Path path: %s", patch_path)
        self._notification_service.found_patch_path(patch_path)

        i = 1
        while i < len(patch_path):
            version_from = patch_path[i - 1]
            version_to = patch_path[i]

            delta_file = self.get_patch_path(version_from, version_to)
            if not delta_file.exists():
                logger.info("Download deltafile %s_to_%s from server", version_from, version_to)
                self._download_patch(version_from, version_to)
            else:
                logger.info("Deltafile %s_to_%s already on disk", version_from, version_to)

            self._apply_patch(version_from, version_to)
            i += 1

        # set the new version in the info.json
        self._metadata['current_version'] = version
        with self.info_path.open('w') as info_file:
            json.dump(self._metadata, info_file)

        logger.info('Version %s is now checked out', version)
        self._notification_service.finish_checkout_version(version)

    def _check_version_exists(self, target_version: str) -> bool:
        if self.has_version(target_version):
            return True
        else:
            self._update_repo_info()
            return self.has_version(target_version)

    def _download_patch(self, version_from: str, version_to: str) -> None:
        delta_source = self.url + '/__patches__/%s_to_%s.tar.xz' % (version_from, version_to)
        delta_dest = self.get_patch_path(version_from, version_to)

        try:
            self._download_service.download(delta_source, delta_dest)
        except Exception:
            self._notification_service.error("Downloading patch-file failed @ %s" % delta_source)
            logger.error("Downloading patch-file failed @ %s", delta_source)
            raise

    def _apply_patch(self, version_from: str, version_to: str) -> None:
        self._notification_service.begin_apply_patch(version_from, version_to)
        patch_task = self._patch_task_factory(self.notification_service, self._download_service, self.url,
                                              self._absolute_path, self.get_patch_path(version_from, version_to))
        patch_task.run()
        self._notification_service.finish_apply_patch(version_from, version_to)

    @classmethod
    def get_from_url(cls, path: Path, url: str, download_service: AbstractDownloadService = None,
                     file_logging: bool = True) -> 'ClientRepository':
        if download_service is None:
            logger.debug("Using BasicDownloadService")
            download_service = BasicDownloadService()

        try:
            path.mkdir(parents=True, exist_ok=False)
        except FileExistsError:
            logger.error("Repository already exists (%s)", str(path))
            raise

        try:
            info_json_url = url + '/info.json'
            logger.debug("Read info.json from %s", info_json_url)
            content = download_service.read(info_json_url)
            repo_info = json.loads(content.decode('utf-8'))
        except DownloadError:
            logger.error("Error while downloading info.json")
            raise

        sub_dir = path.joinpath('.bireus')
        sub_dir.mkdir()

        repo_info['url'] = url
        repo_info['current_version'] = repo_info['latest_version']

        with sub_dir.joinpath('info.json').open('w+') as info_file:
            json.dump(repo_info, info_file)

        download_service.download(url + '/versions.gml', sub_dir.joinpath("versions.gml"))

        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            tmpfilepath = tmppath.joinpath("latest.tar.xz")
            logger.info("Begin downloading latest version")
            download_service.download(url + '/latest.tar.xz', tmpfilepath)
            unpack_archive(tmpfilepath, path, 'xztar')
            logger.info("Downloaded and unpacked latest.tar.xz")

        return ClientRepository(path, download_service, file_logging)
