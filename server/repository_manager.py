import logging
from typing import List

from server import get_subdirectory_names
from server.repository import Repository
from shared import *

logger = logging.getLogger(__name__)


class InvalidRepositoryPathError(Exception):
    pass


class RepositoryManager(object):
    def __init__(self, path: Path):
        if not path.is_dir():
            logger.fatal('%s is no valid directory', str(path))
            raise InvalidRepositoryPathError(path)

        self.path = path  # type: Path
        self.repositories = []  # type: List[Repository]
        for repo_dir in get_subdirectory_names(self.path):
            self.repositories.append(Repository(path.joinpath(repo_dir), repo_dir))

    def full_cleanup(self) -> None:
        logger.info('full_cleanup started for %s', str(self.path))

        for repo in self.repositories:
            repo.cleanup()

        logger.info('full_cleanup finished')

    def full_update(self) -> None:
        logger.info('full_update started for %s', str(self.path))

        for repo in self.repositories:
            repo.update()

        logger.info('full_update finished')

    def create(self, name: str, first_version: str = "1.0.0", mode="bi") -> Repository:
        """
        Creates a new repository
        :param name: name of repository
        :param first_version: name of the first version
        :param mode: 'bi' for bidirectional patching, 'fo' for forward only patching
        :return: representation of the new repository
        """

        logger.info('create repository %s with version %s (mode=%s)' % (name, first_version, mode))
        repository = Repository.create(self.path.joinpath(name), name, first_version, mode)
        self.repositories.append(repository)
        return repository
