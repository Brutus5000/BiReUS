# coding=utf-8
import networkx
import pytest

from server.patch_strategy import IncrementalStrategy, InstantStrategy


@pytest.fixture
def incremental_bi_three_version_graph() -> networkx.Graph:
    version_graph = networkx.DiGraph()

    version_graph.add_nodes_from(["v1", "v2", "v3"])
    version_graph.add_edge("v1", "v2")
    version_graph.add_edge("v2", "v1")
    version_graph.add_edge("v2", "v3")
    version_graph.add_edge("v3", "v2")

    return version_graph


@pytest.fixture
def incremental_uni_three_version_graph():
    version_graph = networkx.DiGraph()

    version_graph.add_nodes_from(["v1", "v2", "v3"])
    version_graph.add_edge("v1", "v2")
    version_graph.add_edge("v2", "v3")

    return version_graph


def test_incremental_bi_3_to_4(incremental_bi_three_version_graph):
    version_graph = incremental_bi_three_version_graph  # type: networkx.Graph

    strategy = IncrementalStrategy()
    patches = strategy.add_version(version_graph, "v3", "v4")

    assert len(patches) == 2
    assert patches[0][0] == "v3"
    assert patches[0][1] == "v4"
    assert patches[1][0] == "v4"
    assert patches[1][1] == "v3"

    assert not version_graph.has_edge("v1", "v4")
    assert not version_graph.has_edge("v2", "v4")
    assert version_graph.has_edge("v3", "v4")
    assert not version_graph.has_edge("v4", "v1")
    assert not version_graph.has_edge("v4", "v2")
    assert version_graph.has_edge("v4", "v3")


def test_instant_bi_3_to_4(incremental_bi_three_version_graph):
    version_graph = incremental_bi_three_version_graph  # type: networkx.Graph

    strategy = InstantStrategy()
    patches = strategy.add_version(version_graph, "v3", "v4")

    assert len(patches) == 6

    assert version_graph.has_edge("v1", "v4")
    assert version_graph.has_edge("v2", "v4")
    assert version_graph.has_edge("v3", "v4")
    assert version_graph.has_edge("v4", "v1")
    assert version_graph.has_edge("v4", "v2")
    assert version_graph.has_edge("v4", "v3")


def test_incremental_uni_3_to_4(incremental_uni_three_version_graph):
    version_graph = incremental_uni_three_version_graph  # type: networkx.Graph

    strategy = IncrementalStrategy(False)
    patches = strategy.add_version(version_graph, "v3", "v4")

    assert len(patches) == 1
    assert patches[0][0] == "v3"
    assert patches[0][1] == "v4"

    assert not version_graph.has_edge("v1", "v4")
    assert not version_graph.has_edge("v2", "v4")
    assert version_graph.has_edge("v3", "v4")
    assert not version_graph.has_edge("v4", "v1")
    assert not version_graph.has_edge("v4", "v2")
    assert not version_graph.has_edge("v4", "v3")


def test_instant_uni_3_to_4(incremental_uni_three_version_graph):
    version_graph = incremental_uni_three_version_graph  # type: networkx.Graph

    strategy = InstantStrategy(False)
    patches = strategy.add_version(version_graph, "v3", "v4")

    assert len(patches) == 3

    assert version_graph.has_edge("v1", "v4")
    assert version_graph.has_edge("v2", "v4")
    assert version_graph.has_edge("v3", "v4")
    assert not version_graph.has_edge("v4", "v1")
    assert not version_graph.has_edge("v4", "v2")
    assert not version_graph.has_edge("v4", "v3")
