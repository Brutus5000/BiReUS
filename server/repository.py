import logging
from typing import List

from server import get_subdirectory_names
from server.compare_task import CompareTask
from shared import *


class Repository(object):
    def __init__(self, absolute_path: Path, name: str):
        self.logger = logging.getLogger('server.Repository')

        self.name = name
        self._absolute_path = absolute_path

    def update(self, forward_only: bool = False) -> None:
        if not self._absolute_path.joinpath('info.json').exists():
            self.logger.error("Repository %s is missing info.json - skipping repo", self.name)
            return

        self.logger.info('Updating repository %s', self.name)

        # load known versions from file
        with self._absolute_path.joinpath('.versions').open(mode='r+') as file:
            known_versions = file.read().splitlines()

        version_list = get_subdirectory_names(self._absolute_path)

        version_list.sort()
        self.logger.info('%s is the latest version', version_list[-1])
        self.logger.debug('generate latest.tar.xz')
        make_archive(self._absolute_path.joinpath('latest'), 'xztar',
                     self._absolute_path.joinpath(version_list[-1]))

        self.logger.debug('begin patching')

        # check for new versions
        for version_dir in version_list:
            if version_dir not in known_versions:
                self.logger.info("new version: %s", version_dir)
                self.add_version(known_versions, version_dir, forward_only)

    def add_version(self, existing_versions: List[str], new_version: str, forward_only: bool = False) -> None:
        self.logger.debug("existing versions: %s", existing_versions)

        with self._absolute_path.joinpath('.versions').open(mode='a') as version_file:
            for old_version in existing_versions:
                self.logger.debug('Generating diffs %s -> %s', old_version, new_version)
                CompareTask(self.name, old_version, new_version).generate_diff()

                if (forward_only):
                    self.logger.info('--forward-only: skipping backward patch')
                else:
                    self.logger.debug('Generating diffs %s -> %s', new_version, old_version)
                    CompareTask(self.name, new_version, old_version).generate_diff()

            self.logger.debug('append %s to known versions', new_version)
            version_file.write('\n' + new_version)
            existing_versions.append(new_version)

    def cleanup(self) -> None:
        self.logger.debug('Cleanup %s', self.name)
        remove_folder(self._absolute_path.joinpath("__patches__"))
