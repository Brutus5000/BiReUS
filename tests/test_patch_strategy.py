# coding=utf-8
import networkx
import pytest

from server.patch_strategy import IncrementalStrategy, InstantStrategy, MajorMinorStrategy


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


def test_major_minor_fail_invalid_graph(incremental_bi_three_version_graph):
    version_graph = incremental_bi_three_version_graph  # type: networkx.Graph

    strategy = MajorMinorStrategy()

    with pytest.raises(Exception):
        patches = strategy.add_version(version_graph, "v3", "v4")

    version_graph.graph["isMajorMinor"] = "no"
    with pytest.raises(Exception):
        patches = strategy.add_version(version_graph, "v3", "v4")


def test_major_minor_bi_add_no_major_yet(incremental_bi_three_version_graph):
    version_graph = incremental_bi_three_version_graph  # type: networkx.Graph
    version_graph.graph["isMajorMinor"] = "yes"

    strategy = MajorMinorStrategy(bidirectional=True, minor_range=10)
    patches = strategy.add_version(version_graph, "v3", "v4")

    assert len(patches) == 6

    assert version_graph.has_edge("v1", "v4")
    assert version_graph.has_edge("v2", "v4")
    assert version_graph.has_edge("v3", "v4")
    assert version_graph.has_edge("v4", "v1")
    assert version_graph.has_edge("v4", "v2")
    assert version_graph.has_edge("v4", "v3")

    assert "isMajorVersion" not in version_graph.node["v4"]


def test_major_minor_uni_add_no_major_yet(incremental_bi_three_version_graph):
    version_graph = incremental_bi_three_version_graph  # type: networkx.Graph
    version_graph.graph["isMajorMinor"] = "yes"

    strategy = MajorMinorStrategy(bidirectional=False, minor_range=10)
    patches = strategy.add_version(version_graph, "v3", "v4")

    assert len(patches) == 3

    assert version_graph.has_edge("v1", "v4")
    assert version_graph.has_edge("v2", "v4")
    assert version_graph.has_edge("v3", "v4")
    assert not version_graph.has_edge("v4", "v1")
    assert not version_graph.has_edge("v4", "v2")
    assert not version_graph.has_edge("v4", "v3")

    assert "isMajorVersion" not in version_graph.node["v4"]


def test_major_minor_bi_add_first_major(incremental_bi_three_version_graph):
    version_graph = incremental_bi_three_version_graph  # type: networkx.Graph
    version_graph.graph["isMajorMinor"] = "yes"

    strategy = MajorMinorStrategy(bidirectional=True, minor_range=4)
    patches = strategy.add_version(version_graph, "v3", "v4")

    assert len(patches) == 6

    assert version_graph.has_edge("v1", "v4")
    assert version_graph.has_edge("v2", "v4")
    assert version_graph.has_edge("v3", "v4")
    assert version_graph.has_edge("v4", "v1")
    assert version_graph.has_edge("v4", "v2")
    assert version_graph.has_edge("v4", "v3")

    assert version_graph.node["v4"]["isMajorVersion"]


def test_major_minor_bi_add_first_after_major(incremental_bi_three_version_graph):
    version_graph = incremental_bi_three_version_graph  # type: networkx.Graph
    version_graph.graph["isMajorMinor"] = "yes"
    version_graph.node["v3"]["isMajorVersion"] = "yes"

    strategy = MajorMinorStrategy(bidirectional=True, minor_range=3)
    patches = strategy.add_version(version_graph, "v3", "v4")

    assert len(patches) == 2

    assert not version_graph.has_edge("v1", "v4")
    assert not version_graph.has_edge("v2", "v4")
    assert version_graph.has_edge("v3", "v4")
    assert not version_graph.has_edge("v4", "v1")
    assert not version_graph.has_edge("v4", "v2")
    assert version_graph.has_edge("v4", "v3")

    assert "isMajorVersion" not in version_graph.node["v4"]


def test_major_minor_uni_3_success():
    version_graph = networkx.DiGraph()
    version_graph.graph["isMajorMinor"] = "yes"

    version_graph.add_nodes_from(["v1", "v2", "v3", "v4", "v5", "v6", "v7", "v8", "v9", "v10", "v11"])
    version_graph.add_edge("v1", "v2")
    version_graph.add_edge("v1", "v3")
    version_graph.add_edge("v2", "v3")
    version_graph.add_edge("v3", "v4")
    version_graph.add_edge("v3", "v5")
    version_graph.add_edge("v3", "v6")
    version_graph.add_edge("v4", "v5")
    version_graph.add_edge("v4", "v6")
    version_graph.add_edge("v5", "v6")
    version_graph.add_edge("v6", "v7")
    version_graph.add_edge("v6", "v8")
    version_graph.add_edge("v6", "v9")
    version_graph.add_edge("v7", "v8")
    version_graph.add_edge("v7", "v9")
    version_graph.add_edge("v8", "v9")
    version_graph.add_edge("v9", "v10")
    version_graph.add_edge("v9", "v11")
    version_graph.add_edge("v10", "v11")

    version_graph.add_edge("v3", "v9")

    version_graph.node["v3"]["isMajorVersion"] = "yes"
    version_graph.node["v6"]["isMajorVersion"] = "yes"
    version_graph.node["v9"]["isMajorVersion"] = "yes"

    strategy = MajorMinorStrategy(bidirectional=False, minor_range=3)
    patches = strategy.add_version(version_graph, "v11", "v12")

    assert len(patches) == 5  # 2 minor + 3 major

    return version_graph
