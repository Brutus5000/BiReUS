import logging
import os
import shutil
from typing import List

from server import get_subdirectories
from server.compare_task import CompareTask


class Repository(object):
    def __init__(self, absolute_path: str, name: str):
        self.logger = logging.getLogger('server.Repository')

        self.name = name
        self._absolute_path = absolute_path

    def update(self, forward_only: bool = False) -> None:
        self.logger.info('Updating repository %s', self.name)

        # load known versions from file
        with open(os.path.join(self._absolute_path, '.versions'), 'r+') as file:
            known_versions = file.read().splitlines()

        version_list = get_subdirectories(self._absolute_path)

        version_list.sort()
        self.logger.info('%s is the latest version', version_list[-1])
        self.logger.debug('generate latest.zip')
        shutil.make_archive(os.path.join(self._absolute_path, 'latest'), 'zip',
                            os.path.join(self._absolute_path, version_list[-1]))

        self.logger.debug('begin patching')

        # check for new versions
        for version_dir in version_list:
            if version_dir not in known_versions:
                self.logger.info("new version: %s", version_dir)
                self.add_version(known_versions, version_dir, forward_only)


    def add_version(self, existing_versions: List[str], new_version: str, forward_only: bool = False) -> None:
        self.logger.debug("existing versions: %s", existing_versions)

        with open(os.path.join(self._absolute_path, '.versions'), 'a') as version_file:
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
        for version_dir in get_subdirectories(self.name):
            remove_path = os.path.join(self._absolute_path, version_dir, '.delta_to')
            if os.path.exists(remove_path):
                self.logger.debug('Cleanup %s', remove_path)
                shutil.rmtree(remove_path)
