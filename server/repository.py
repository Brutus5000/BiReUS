import logging
import json
from typing import List

from server import get_subdirectory_names
from server.compare_task import CompareTask
from shared import *

logger = logging.getLogger(__name__)


class Repository(object):
    def __init__(self, absolute_path: Path, name: str):
        self.name = name
        self._absolute_path = absolute_path

        with absolute_path.joinpath("info.json").open("r") as file:
            info_json = json.load(file)

        self.latest_version = info_json["config"]["latest_version"]
        self.versions = info_json["versions"]

    def update(self, forward_only: bool = False) -> None:
        if not self._absolute_path.joinpath('info.json').exists():
            logger.error("Repository %s is missing info.json - skipping repo", self.name)
            return

        logger.info('Updating repository %s', self.name)

        # load known versions from file
        with self._absolute_path.joinpath('.versions').open(mode='r+') as file:
            known_versions = file.read().splitlines()

        version_list = get_subdirectory_names(self._absolute_path)

        version_list.sort()
        logger.info('%s is the latest version', version_list[-1])
        logger.debug('generate latest.tar.xz')
        make_archive(self._absolute_path.joinpath('latest'), 'xztar',
                     self._absolute_path.joinpath(version_list[-1]))

        logger.debug('begin patching')

        # check for new versions
        for version_dir in version_list:
            if version_dir not in known_versions:
                logger.info("new version: %s", version_dir)
                self.add_version(known_versions, version_dir, forward_only)

    def add_version(self, existing_versions: List[str], new_version: str, forward_only: bool = False) -> None:
        logger.debug("existing versions: %s", existing_versions)

        with self._absolute_path.joinpath('.versions').open(mode='a') as version_file:
            for old_version in existing_versions:
                logger.debug('Generating diffs %s -> %s', old_version, new_version)
                CompareTask(self.name, old_version, new_version).generate_diff()

                if (forward_only):
                    logger.info('--forward-only: skipping backward patch')
                else:
                    logger.debug('Generating diffs %s -> %s', new_version, old_version)
                    CompareTask(self.name, new_version, old_version).generate_diff()

            logger.debug('append %s to known versions', new_version)
            version_file.write('\n' + new_version)
            existing_versions.append(new_version)

    def cleanup(self) -> None:
        logger.debug('Cleanup %s', self.name)
        remove_folder(self._absolute_path.joinpath("__patches__"))

    @classmethod
    def create(cls, path: Path, name: str, first_version: str, mode: str) -> 'Repository':
        repository = Repository(path, name)
        
        # TODO: repository.add_version()
        pass
