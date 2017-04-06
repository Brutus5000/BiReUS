# coding=utf-8
import logging

from bireus.server import get_subdirectory_names
from typing import List

from bireus.server.repository import ServerRepository
from bireus.shared import *

logger = logging.getLogger(__name__)


class InvalidRepositoryPathError(Exception):
    pass


class RepositoryManager(object):
    def __init__(self, path: Path):
        if not path.is_dir():
            logger.fatal('%s is no valid directory', str(path))
            raise InvalidRepositoryPathError(path)

        self.path = path  # type: Path
        self.repositories = []  # type: List[ServerRepository]
        for repo_dir in get_subdirectory_names(self.path):
            self.repositories.append(ServerRepository(path.joinpath(repo_dir)))

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

    def create(self, name: str, first_version: str = "1.0.0", strategy="inst-bi") -> ServerRepository:
        """
        Creates a new repository
        :param name: name of repository
        :param first_version: name of the first version
        :param strategy: 'bi' for bidirectional patching, 'fo' for forward only patching
        :return: representation of the new repository
        """

        logger.info('create repository %s with version %s (strategy=%s)' % (name, first_version, strategy))
        repository = ServerRepository.create(self.path.joinpath(name), name, first_version, strategy)
        self.repositories.append(repository)
        return repository
