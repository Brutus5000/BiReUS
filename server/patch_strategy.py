# coding=utf-8
import abc
from typing import List, Tuple

from networkx import Graph


class AbstractStrategy(abc.ABC):
    """
    Abstract strategy class that determines, which patches need to be created on a new version
    """

    @abc.abstractclassmethod
    def get_required_patches(self, version_graph: Graph, last_version: str, new_version: str) -> List[Tuple[str, str]]:
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

    def get_required_patches(self, version_graph: Graph, last_version: str, new_version: str) -> List[Tuple[str, str]]:
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

    def get_required_patches(self, version_graph: Graph, last_version: str, new_version: str) -> List[Tuple[str, str]]:
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
