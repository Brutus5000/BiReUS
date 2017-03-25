import json
import logging

import networkx

from server import get_subdirectory_names
from server.compare_task import CompareTask
from shared import *
from shared.repository import BaseRepository

logger = logging.getLogger(__name__)


class ServerRepository(BaseRepository):
    def __init__(self, absolute_path: Path):
        super().__init__(absolute_path)

    @property
    def info_path(self) -> Path:
        return self._absolute_path.joinpath('info.json')

    @property
    def version_graph_path(self) -> Path:
        return self._absolute_path.joinpath('versions.gml')

    def update(self) -> None:
        if not self._absolute_path.joinpath('info.json').exists():
            logger.error("Repository %s is missing info.json - skipping repo", self.name)
            return

        logger.info('Updating repository %s', self.name)

        version_list = get_subdirectory_names(self._absolute_path)

        version_list.sort()
        logger.info('%s is the latest version', version_list[-1])
        logger.debug('generate latest.tar.xz')
        make_archive(self._absolute_path.joinpath('latest'), 'xztar',
                     self._absolute_path.joinpath(version_list[-1]))

        logger.debug('begin patching')

        # check for new versions
        for version_dir in version_list:
            if version_dir not in self.versions:
                logger.info("new version: %s", version_dir)
                self.add_version(version_dir)

    def add_version(self, new_version: str) -> None:
        logger.debug("existing versions: %s", self.versions)

        for old_version in self.versions:
            logger.debug('Generating diffs %s -> %s', old_version, new_version)
            CompareTask(self._absolute_path, self.name, old_version, new_version).generate_diff()

            if (self.strategy == "fo"):
                logger.info('forward-only: skipping backward patch')
            else:
                logger.debug('Generating diffs %s -> %s', new_version, old_version)
                CompareTask(self._absolute_path, self.name, new_version, old_version).generate_diff()

        logger.debug('append %s to known versions', new_version)
        self.versions.append(new_version)
        self._save_info_json()

    def cleanup(self) -> None:
        logger.debug('Cleanup %s', self.name)
        remove_folder(self._absolute_path.joinpath("__patches__"))

    def _save_info_json(self):
        info_json = {
            "config": {
                "name": self.name,
                "first_version": self.first_version,
                "latest_version": self.latest_version,
                "strategy": self.strategy
            },
            "versions": []
        }

        for v in self.versions:
            info_json["versions"].append(v)

        with self._absolute_path.joinpath("info.json").open("w+") as file:
            json.dump(info_json, file)

    @classmethod
    def create(cls, path: Path, name: str, first_version: str, strategy: str) -> 'ServerRepository':
        version_path = path.joinpath(first_version)
        version_path.mkdir(parents=True)

        with path.joinpath("info.json").open("w+") as file:
            info_json = {
                "config": {
                    "name": name,
                    "first_version": first_version,
                    "latest_version": first_version,
                    "strategy": strategy
                },
                "versions": []
            }

            json.dump(info_json, file)

        version_graph = networkx.DiGraph()
        version_graph.add_node(first_version)
        networkx.write_gml(version_graph, str(path.joinpath("versions.gml")))

        logger.info("Repository %s created, copy your content into %s and run update", name, str(version_path))

        return ServerRepository(path)
