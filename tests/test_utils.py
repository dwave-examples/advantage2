# Copyright 2025 D-Wave
#
#    Licensed under the Apache License, Version 2.0 (the "License");
#    you may not use this file except in compliance with the License.
#    You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS,
#    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    See the License for the specific language governing permissions and
#    limitations under the License.

import unittest.mock as mock

import networkx as nx
import plotly.graph_objects as go

from src.demo_enums import AnnealType
from src.utils import (
    get_chip_intersection_graph,
    get_edge_trace,
    get_energies,
    get_fig,
    get_mapping,
    get_node_trace,
    plot_solution,
)

node_coords = {1: (0, 0), 2: (1, 1), 3: (2, 0)}


def test_get_edge_trace():
    G = nx.Graph()
    G.add_edges_from([(1, 2), (2, 3)])

    trace = get_edge_trace(G, node_coords, "white", 2.0)

    assert isinstance(trace, go.Scatter)
    assert trace.mode == "lines"


def test_get_node_trace():
    G = nx.Graph()
    G.add_nodes_from([1, 2, 3])

    trace = get_node_trace(G, node_coords, "white")

    assert isinstance(trace, go.Scatter)
    assert trace.mode == "markers"
    assert len(trace.x) == 3


def test_get_fig():
    G = nx.Graph()
    G.add_edges_from([(1, 2), (2, 3)])

    fig = get_fig(G, G.subgraph([1, 2]), node_coords, "Test Graph")

    assert isinstance(fig, go.Figure)
    assert len(fig.data) == 4  # 2 traces from G, 2 from subgraph
    assert fig.layout.title.text == "Test Graph"


def test_get_mapping():
    # Create dummy mapper to pass into get_mapping function
    def dummy_mapper(intersection_graph, qpu_g):
        def map1(node):
            return f"mapped_{node}"

        def map2(node):
            return f"another_mapped_{node}"

        return [map2, map1]

    # Create intersection graph
    intersection_graph = nx.Graph()
    intersection_graph.add_edges_from([(0, 1), (1, 2)])

    # Create QPU graph
    qpu_graph = nx.Graph()
    qpu_graph.add_edges_from(
        [
            ("mapped_0", "mapped_1"),
            ("mapped_1", "mapped_2"),
        ]
    )

    sub_graph, intersection_graph, mapping = get_mapping(
        qpu_graph, intersection_graph, dummy_mapper
    )

    assert mapping(0) == "mapped_0"
    assert mapping(1) == "mapped_1"
    assert mapping(2) == "mapped_2"
    assert isinstance(sub_graph, nx.Graph)
    assert len(sub_graph.nodes) == 3
    assert isinstance(intersection_graph, nx.Graph)
    assert len(intersection_graph.edges) == 2


@mock.patch("src.utils.get_fig")
@mock.patch("src.utils.get_mapping")
@mock.patch("src.utils.DWaveSampler")
@mock.patch("src.utils.dnx")
def test_get_chip_intersection_graph(mock_dnx, mock_sampler, mock_get_mapping, mock_get_fig):
    # Set up mock samplers and graphs
    mock_pegasus = mock.Mock()
    mock_zephyr = mock.Mock()

    mock_pegasus.properties = {"topology": {"shape": [17]}}  # 17 - 1 = 16
    mock_zephyr.properties = {"topology": {"shape": [8]}}  # 8 * 2 = 16

    mock_pegasus.to_networkx_graph.return_value = nx.complete_graph(5)
    mock_zephyr.to_networkx_graph.return_value = nx.complete_graph(5)

    mock_sampler.side_effect = [mock_pegasus, mock_zephyr]

    # Set up mock get_mapping to return dummy values
    dummy_subgraph = nx.path_graph(3)
    dummy_intersection = nx.path_graph(3)
    dummy_mapping = lambda x: f"mapped_{x}"
    mock_get_mapping.side_effect = [
        (dummy_subgraph, dummy_intersection, dummy_mapping),
        (dummy_subgraph, dummy_intersection, dummy_mapping),
    ]

    # Set up mock figs
    dummy_fig = go.Figure()
    dummy_fig2 = go.Figure()
    mock_get_fig.side_effect = [dummy_fig, dummy_fig2]

    # Set up mock dnx
    mock_dnx_response = mock.Mock()
    mock_dnx_response.chimera_graph.return_value = dummy_intersection
    mock_dnx_response.drawing.pegasus_layout.return_value = {}
    mock_dnx_response.drawing.zephyr_layout.return_value = {}
    mock_dnx.return_value = mock_dnx_response

    fig, fig2, intersection_graph, mapping_dict = get_chip_intersection_graph(
        "Advantage", "Advantage2"
    )

    assert fig is dummy_fig
    assert fig2 is dummy_fig2
    assert isinstance(intersection_graph, nx.Graph)
    assert mapping_dict == {"Advantage": dummy_mapping, "Advantage2": dummy_mapping}


def test_get_energies():
    # Create mock sampleset
    mock_sampleset = mock.Mock()
    mock_sampleset.record.energy = [100, 200, 300]
    mock_sampleset.record.num_occurrences = [1, 2, 1]
    mock_sampleset.info = {}

    # Create mock QPU and add sampleset to it
    mock_qpu = mock.Mock()
    mock_qpu.sample.return_value = mock_sampleset

    # Create mock BQM
    mock_bqm = mock.Mock()
    mock_bqm.relabel_variables.return_value = {}

    graph = nx.complete_graph(5)
    dummy_mapping = lambda x: f"mapped_{x}"

    energies, info = get_energies(
        qpu=mock_qpu,
        graph=graph,
        qpu_mapping=dummy_mapping,
        annealing_time=5,
        anneal_type=AnnealType.STANDARD,
        bqm=mock_bqm,
    )

    assert energies == [100, 200, 200, 300]
    assert info == {}


def test_plot_solution():
    fig = plot_solution("Advantage", "Advantage2", [100, 200, 200], [-200, -200, -100])

    assert isinstance(fig, go.Figure)
    assert len(fig.data) == 2
    assert fig.data[0].legendgroup == "Advantage"
    assert fig.data[1].legendgroup == "Advantage2"
