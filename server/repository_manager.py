import logging
from typing import List

from server import get_subdirectory_names
from server.repository import Repository
from shared import *


class InvalidRepositoryPathError(Exception):
    pass


class RepositoryManager(object):
    def __init__(self, path: Path):
        self.logger = logging.getLogger('server.RepositoryManager')

        if not path.is_dir():
            self.logger.fatal('%s is no valid directory', str(path))
            raise InvalidRepositoryPathError(path)

        change_dir(path)

        self.path = path  # type: Path
        self.repositories = []  # type: List[Repository]
        for repo_dir in get_subdirectory_names(self.path):
            self.repositories.append(Repository(path.joinpath(repo_dir), repo_dir))

    def full_cleanup(self) -> None:
        self.logger.info('full_cleanup started for %s', str(self.path))

        for repo in self.repositories:
            repo.cleanup()

        self.logger.info('full_cleanup finished')

    def full_update(self, forward_only: bool = False) -> None:
        self.logger.info('full_update started for %s', str(self.path))

        for repo in self.repositories:
            repo.update(forward_only)

        self.logger.info('full_update finished')
