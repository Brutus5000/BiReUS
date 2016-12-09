import logging
import os
from typing import List

from server import get_subdirectories
from server.Repository import Repository


class InvalidRepositoryPathError(Exception):
    pass


class RepositoryManager(object):
    def __init__(self, path: str):
        self.logger = logging.getLogger('server.RepositoryManager')

        if not os.path.isdir(path):
            self.logger.fatal('%s is no valid directory', path)
            raise InvalidRepositoryPathError(path)

        self.Path = path  # type: str
        self.Repositories = []  # type: List[Repository]
        for repo_dir in get_subdirectories(self.Path):
            self.Repositories.append(Repository(os.path.join(path, repo_dir), repo_dir))

    def full_cleanup(self) -> None:
        self.logger.info('full_cleanup started for %s', self.Path)

        for repo in self.Repositories:
            repo.cleanup()

        self.logger.info('full_cleanup finished')

    def full_update(self, forward_only: bool = False) -> None:
        self.logger.info('full_update started for %s', self.Path)

        for repo in self.Repositories:
            repo.update(forward_only)

        self.logger.info('full_update finished')
