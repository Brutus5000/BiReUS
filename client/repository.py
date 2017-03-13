import json
import logging
import tempfile
from urllib.parse import urljoin


from client.download_service import AbstractDownloadService, BasicDownloadService, DownloadError
from client.patch_task import PatchTask
from shared import *
from shared.DiffHead import DiffHead

logger = logging.getLogger(__name__)


class CheckoutError(Exception):
    pass


class Repository(object):
    def __init__(self, absolute_path: Path, download_service: AbstractDownloadService = None):
        if download_service is None:
            self._download_service = BasicDownloadService()
        else:
            self._download_service = download_service

        if not absolute_path.exists():
            logger.error("repository path `%s` does not exist", absolute_path)
            raise FileNotFoundError("repository path `%s` does not exist", absolute_path)

        info_file = absolute_path.joinpath('.bireus', 'info.json')

        if not info_file.exists():
            logger.error("`%s` is not a valid BiReUS client repository", absolute_path)
            raise ValueError("`%s` is not a valid BiReUS client repository", absolute_path)

        logger.debug("Initialize Repository @ %s ", absolute_path)

        with absolute_path.joinpath('.bireus', 'info.json').open("r") as data_file:
            self._metadata = json.load(data_file)

        self._absolute_path = absolute_path
        self._internal_path = Path('.bireus')

    @property
    def name(self) -> str:
        return self._metadata['name']

    @property
    def current_version(self) -> str:
        return self._metadata['current_version']

    @property
    def latest_version(self) -> str:
        return self._metadata['config']['latest_version']

    @property
    def url(self) -> str:
        return self._metadata['url']

    async def latest_from_remote(self) -> str:
        content = await self._download_service.read(urljoin(self.url, '/info.json'))
        repo_info = json.loads(content.decode('utf-8'))
        logger.info('Latest version in remote repository is ´%s´', repo_info['latest_version'])
        return repo_info['config']['latest_version']

    async def checkout_latest(self) -> None:
        try:
            version = await self.latest_from_remote()
            self._metadata['latest_version'] = version
            with open(str(self._absolute_path / self._internal_path / Path('info.json')), 'w') as info_file:
                json.dump(self._metadata, info_file)
        except:
            logger.warning("Remote repository unreachable, use local instead")
            version = self.latest_version

        await self.checkout_version(self.latest_version)

    async def checkout_version(self, version: str) -> None:
        if self.current_version == version:
            logger.info("Version `%s` is already checked out", version)
            return

        if not await self._check_version(version):
            logger.error("Version `%s` is not listed on server", version)
            raise CheckoutError("Version `%s` is not listed on server", version)

        logger.info("Checking out version %s", version)

        delta_file = self._absolute_path / self._internal_path / Path(
            '%s_to_%s.tar.xz' % (self.current_version, version))  # type: Path
        if not delta_file.exists():
            logger.info("Download deltafile %s_2_%s from server", self.current_version, version)
            await self._download_delta_to(version)
        else:
            logger.info("Deltafile %s_2_%s already on disk", self.current_version, version)

        await self._apply_patch(version)

        # set the new version in the info.json
        self._metadata['current_version'] = version
        with open(str(self._absolute_path / self._internal_path / Path('info.json')), 'w') as info_file:
            json.dump(self._metadata, info_file)

        logger.info('Version %s is now checked out', version)

    async def _check_version(self, target_version: str) -> bool:
        try:
            content = await self._download_service.read(urljoin(self.url, '/.versions'))
            return target_version in content.decode('utf-8')
        except DownloadError:
            return False

    async def _download_delta_to(self, target_version: str) -> None:
        delta_source = urljoin(self.url, '/__patches__/%s_to_%s.tar.xz' % (self.current_version, target_version))
        delta_dest = self._absolute_path / self._internal_path / Path(
            '%s_to_%s.tar.xz' % (self.current_version, target_version))

        try:
            await self._download_service.download(delta_source, delta_dest)
        except Exception:
            logger.error("Downloading patch-file failed @ %s", delta_source)
            raise

    async def _apply_patch(self, target_version) -> None:
        patch_dir = Path(tempfile.TemporaryDirectory(prefix="bireus_", suffix="_" + target_version).name)
        patch_file = self._absolute_path / self._internal_path / Path(
            '%s_to_%s.tar.xz' % (self.current_version, target_version))

        unpack_archive(patch_file, patch_dir, 'xztar')

        diff_head = DiffHead.load_json_file(patch_dir.joinpath('.bireus'))

        if len(diff_head.items) == 0 or len(diff_head.items) > 1:
            logger.error("Invalid diff_head - only top directory allowed")
            raise Exception("Invalid diff_head - only top directory allowed")

        await PatchTask(self._download_service, self.url, self._absolute_path, Path('.'), Path(patch_dir), diff_head, diff_head.items[0]).patch()

    @classmethod
    async def get_from_url(cls, path: Path, url: str, download_service: AbstractDownloadService = None) -> 'Repository':
        if download_service is None:
            logger.debug("Using BasicDownloadService")
            download_service = BasicDownloadService()

        try:
            path.mkdir(parents=True, exist_ok=False)
        except FileExistsError:
            logger.error("Repository already exists (%s)", str(path))
            raise

        try:
            content = await download_service.read(urljoin(url, '/info.json'))
            repo_info = json.loads(content.decode('utf-8'))
        except DownloadError:
            logger.error("Error while downloading info.json")
            raise

        sub_dir = path.joinpath('.bireus')
        sub_dir.mkdir()

        repo_info['current_version'] = repo_info['config']['latest_version']

        with open(str(sub_dir / Path('info.json')), 'w+') as info_file:
            json.dump(repo_info, info_file)

        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            tmpfilepath = tmppath.joinpath("latest.tar.xz")
            await download_service.download(urljoin(url, '/latest.tar.xz'), tmpfilepath)
            unpack_archive(tmpfilepath, path, 'xztar')
            logger.info("Downloaded and unpacked latest.tar.xz")

        return Repository(path, download_service)
