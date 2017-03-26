# coding=utf-8
import abc
import logging
from typing import List, Tuple

import networkx
from networkx import Graph

logger = logging.getLogger(__name__)


class AbstractStrategy(abc.ABC):
    """
    Abstract strategy class that determines, which patches need to be created on a new version
    """

    def new_repo(self, first_version: str) -> Graph:
        """
        Creates a graph for a new repo with a first version
        Override this method if the strategy requires a certain setup
        :return: valid graph
        """
        version_graph = networkx.DiGraph()
        version_graph.add_node(first_version)
        return version_graph

    @abc.abstractclassmethod
    def add_version(self, version_graph: Graph, last_version: str, new_version: str) -> List[Tuple[str, str]]:
        """
        Calculates which patches need to be generated
        :param version_graph: graph of all versions - Attention! gets manipulated!
        :param last_version: predecessor of new_version
        :param new_version: the new version
        :return: a list of version-pairs for which patches need to be created
        """
        pass


class IncrementalStrategy(AbstractStrategy):
    def __init__(self, bidirectional: bool = True):
        self.bidirectional = bidirectional

    def add_version(self, version_graph: Graph, last_version: str, new_version: str) -> List[Tuple[str, str]]:
        required_patches = [(last_version, new_version)]

        version_graph.add_node(new_version)
        version_graph.add_edge(last_version, new_version)

        if self.bidirectional:
            version_graph.add_edge(new_version, last_version)
            required_patches.append((new_version, last_version))

        return required_patches


class InstantStrategy(AbstractStrategy):
    def __init__(self, bidirectional: bool = True):
        self.bidirectional = bidirectional

    def add_version(self, version_graph: Graph, last_version: str, new_version: str) -> List[Tuple[str, str]]:
        required_patches = []

        versions = list(version_graph)
        version_graph.add_node(new_version)

        for version in versions:
            required_patches.append((version, new_version))
            version_graph.add_edge(version, new_version)

            if self.bidirectional:
                required_patches.append((new_version, version))
                version_graph.add_edge(new_version, version)

        return required_patches


def is_set(graph_object: object, property: str):
    return property in graph_object and graph_object[property] == "yes"


class MajorMinorStrategy(AbstractStrategy):
    def __init__(self, bidirectional: bool = True, minor_range: int = 10):
        self.bidirectional = bidirectional
        self.minor_range = minor_range

    def new_repo(self, first_version: str):
        version_graph = super().new_repo(first_version)
        version_graph.graph['isMajorMinor'] = "yes"
        return version_graph

    def add_version(self, version_graph: Graph, last_version: str, new_version: str) -> List[Tuple[str, str]]:
        required_patches = []

        if not is_set(version_graph.graph, "isMajorMinor"):
            logger.error("version graph is no major/minor graph")
            raise Exception("version graph is no major/minor graph")

        if last_version not in version_graph:
            logger.error("versions %s not found" % last_version)
            raise Exception("versions %s not found" % last_version)

        patches_required = []  # all versions that we need to create patches to/from new_version
        all_existing_versions = list(version_graph)
        all_major_versions = []  # all major versions in graph

        for version in version_graph:
            if is_set(version_graph.node[version], "isMajorVersion"):
                all_major_versions.append(version)

        new_version_is_major = False

        if len(all_major_versions) == 0:
            # no major versions exist
            # check whether new_version needs to be major_version
            # -1 because the first version of a graph is not major
            if len(all_existing_versions) >= self.minor_range - 1:
                new_version_is_major = True

            # we need to create patches to all versions in both cases
            patches_required.extend(all_existing_versions)
        else:
            if is_set(version_graph.node[last_version], "isMajorVersion"):
                # first minor version after major version - only last_version and new_version affected
                patches_required.append(last_version)
            else:
                # in this case we need to patch with all neighbours of last_version
                neighbors = set(networkx.all_neighbors(version_graph, last_version))
                neighbors.add(last_version)

                if len(neighbors) >= self.minor_range:
                    new_version_is_major = True
                    neighbors |= set(all_major_versions)

                patches_required.extend(neighbors)

        version_graph.add_node(new_version)
        if new_version_is_major:
            logger.info("new major version: %s", new_version)
            version_graph.node[new_version]["isMajorVersion"] = "yes"

        for version in patches_required:
            version_graph.add_edge(version, new_version)
            required_patches.append((version, new_version))

            if self.bidirectional:
                version_graph.add_edge(new_version, version)
                required_patches.append((new_version, version))

        return required_patches
