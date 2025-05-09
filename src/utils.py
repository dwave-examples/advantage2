from collections.abc import Mapping
from demo_configs import THEME_COLOR, THEME_COLOR_SECONDARY
from src.demo_enums import AnnealType
import networkx as nx
import dwave_networkx as dnx
from dwave.system import DWaveSampler
import plotly.graph_objects as go
import plotly.express as px
import base64
from typing import Any, Callable
import dill as pickle
import pandas as pd
from dimod import BinaryQuadraticModel

def serialize(obj: Any) -> str:
    """Serialize the object using pickle"""
    return base64.b64encode(pickle.dumps(obj)).decode("utf-8")


def deserialize(obj: str) -> Any:
    """Deserialize the object"""
    return pickle.loads(base64.b64decode(obj.encode("utf-8")))


def get_edge_trace(
    G: nx.Graph,
    node_coords: dict[int, tuple],
    color: str,
    line_width: float
) -> go.Scatter:
    """Create a Plotly scatter trace of graph edges.

    Args:
        G (nx.Graph): The graph to plot.
        node_coords (dict): Dictionary mapping nodes to (x, y) coordinates.
        color (str): The color of the edges.
        line_width (float): The width of the edges.

    Returns:
        go.Scatter: A Plotly scatter trace of edges.
    """
    edge_x = []
    edge_y = []
    for start, end in G.edges():
        x0, y0 = node_coords[start]
        x1, y1 = node_coords[end]
        edge_x.extend([x0, x1, None])
        edge_y.extend([y0, y1, None])

    edge_trace = go.Scatter(
        x=edge_x, y=edge_y,
        line=dict(width=line_width, color=color),
        hoverinfo='none',
        mode='lines'
    )

    return edge_trace


def get_node_trace(G: nx.Graph, node_coords: dict[int, tuple], color: str) -> go.Scatter:
    """Create a Plotly scatter trace of graph nodes.

    Args:
        G (nx.Graph): The graph to plot.
        pos (dict): Dictionary mapping nodes to (x, y) coordinates.
        color (str): The node color.

    Returns:
        go.Scatter: A Plotly scatter trace of nodes.
    """
    node_x = [node_coords[node][0] for node in G.nodes()]
    node_y = [node_coords[node][1] for node in G.nodes()]

    node_trace = go.Scatter(
        x=node_x, y=node_y,
        mode='markers',
        hoverinfo='text',
        marker=dict(
            color=color,
            size=3,
        )
    )

    return node_trace


def get_fig(G: nx.Graph, subG: nx.Graph, node_coords: dict[int, tuple], title: str) -> go.Figure:
    """Generate a Plotly fig of a graph with highlighted subgraph.

    Args:
        G (nx.Graph): The complete graph.
        subG (nx.Graph): The subgraph to highlight.
        node_coords (dict): Dictionary mapping nodes to (x, y) coordinates.
        title (str): The title of the figure.

    Returns:
        go.Figure: A Plotly figure showing a graph with highlighted subgraph.
    """
    edge_trace = get_edge_trace(G, node_coords, "#AAAAAA", 0.5)
    node_trace = get_node_trace(G, node_coords, "#AAAAAA")
    edge_trace_sub = get_edge_trace(subG, node_coords, THEME_COLOR_SECONDARY, 1)
    node_trace_sub = get_node_trace(subG, node_coords, THEME_COLOR_SECONDARY)

    fig = go.Figure(
        data=[edge_trace, node_trace, edge_trace_sub, node_trace_sub],
        layout=go.Layout(
            title=dict(text=title, font=dict(size=20, color=THEME_COLOR)),
            showlegend=False,
            hovermode='closest',
            margin=dict(b=20,l=0,r=0,t=40),
            paper_bgcolor="rgba(0, 0, 0, 0)",
            plot_bgcolor="rgba(0, 0, 0, 0)",
            xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            yaxis=dict(showgrid=False, zeroline=False, showticklabels=False)
        )
    )

    return fig


def get_mapping(
    qpu_graph: nx.Graph,
    intersection_graph: nx.Graph,
    mapper: Callable[[nx.Graph, nx.Graph], list],
) -> tuple[nx.Graph, nx.Graph, Mapping]:
    """Map the intersection graph onto the qpu graph.

    Args:
        qpu_graph (nx.Graph): The graph of the requested system (either Pegasus or Zephyr).
        intersection_graph (nx.Graph): The chimera intersection graph.
        mapper (Callable[[nx.Graph, nx.Graph], list]): The mapper function used to map the
            intersection graph to the qpu graph.

    Returns:
        A tuple containing:
            sub_graph (nx.Graph): The intersection graph mapped onto the system graph.
            intersection_graph (nx.Graph): The chimera intersection graph.
            mapping (Mapping): The intersection mapping onto the given system.
    """
    # get all possible mappings between both graphs
    mappings = mapper(intersection_graph, qpu_graph)

    # select the most yielded mapping
    mapping = {}
    coupler_yield = 0
    for m in mappings:
        edges = [edge for edge in intersection_graph.edges if tuple(map(m, edge)) in qpu_graph.edges]
        if len(edges) > coupler_yield:
            mapping = m
            coupler_yield = len(edges)

    # add the defects to the chimera graph
    edges = [
        edge for edge in intersection_graph.edges if tuple(map(mapping, edge)) in qpu_graph.edges
    ]
    intersection_graph = intersection_graph.edge_subgraph(edges).copy()

    sub_graph = nx.relabel_nodes(intersection_graph, mapping)

    return sub_graph, intersection_graph, mapping


def get_chip_intersection_graph(
    pegasus_qpu_name: str,
    zephyr_qpu_name: str
) -> tuple[go.Figure, go.Figure, nx.Graph, dict[str, Mapping]]:
    """Find highest-yielding intersection graph between Pegasus/Advantage
    system and Zephyr/Advantage2 system.

    Args:
        pegasus_qpu_name (str): The name of the Advantage system selected.
        zephyr_qpu_name (str): The name of the Advantage2 system selected.

    Returns:
        A tuple containing:
            fig (go.Figure): A Plotly fig of the intersection on the Pegasus graph associated with
                the Advantage system selected.
            fig2 (go.Figure): A Plotly fig of the intersection on the Zephyr graph associated with
                the Advantage2 system selected.
            intersection_graph (nx.Graph): The chimera intersection graph.
            best_mapping (dict[str, Mapping]): A dict containing an intersection mapping for each
                system.
    """
    # Load graphs for both Advantage and Advantage2
    pegasus_qpu = DWaveSampler(solver=pegasus_qpu_name)
    zephyr_qpu = DWaveSampler(solver=zephyr_qpu_name)
    pegasus_qpu_g = pegasus_qpu.to_networkx_graph()
    zephyr_qpu_g = zephyr_qpu.to_networkx_graph()

    # Find maximum chimera intersection that fits both topologies
    max_chimera_intersection = min(
        pegasus_qpu.properties["topology"]["shape"][0] - 1,
        zephyr_qpu.properties["topology"]["shape"][0] * 2,
    )
    intersection_graph = dnx.chimera_graph(max_chimera_intersection)

    pegasus_sub_g, intersection_graph, pegasus_mapping = get_mapping(
        pegasus_qpu_g, intersection_graph, dnx.pegasus_sublattice_mappings
    )
    zephyr_sub_g, intersection_graph, zephyr_mapping = get_mapping(
        zephyr_qpu_g, intersection_graph, dnx.zephyr_sublattice_mappings
    )

    pegasus_pos = dnx.drawing.pegasus_layout(dnx.pegasus_graph(16), crosses=True)
    zephyr_pos = dnx.drawing.zephyr_layout(dnx.zephyr_graph(12))
    
    fig = get_fig(pegasus_qpu_g, pegasus_sub_g, pegasus_pos, pegasus_qpu_name)
    fig2 = get_fig(zephyr_qpu_g, zephyr_sub_g, zephyr_pos, zephyr_qpu_name)

    return fig, fig2, intersection_graph, {pegasus_qpu_name: pegasus_mapping, zephyr_qpu_name: zephyr_mapping}


def get_energies(
    qpu: DWaveSampler,
    graph: nx.Graph,
    qpu_mapping: Mapping,
    annealing_time: float,
    anneal_type: AnnealType,
    bqm: BinaryQuadraticModel,
) -> list[float]:
    """Run a BQM on a given QPU using a mapped graph and return a list of resulting energies.

    Args:
        qpu (DWaveSampler): The qpu to run the problem on.
        graph (nx.Graph): The chimera intersection graph.
        qpu_mapping (Mapping): The mapping of the chimera graph onto each system (Advantage and Advantage2)
        anneal_time (float): The anneal time in microseconds.
        anneal_type (AnnealType): The AnnealType, either 0: STANDARD or 1: FAST.
        bqm (BinaryQuadraticModel): The Binary Quadratic Model to solve.

    Returns:
        energies: A list of resulting energies.
    """

    mapping = {node: qpu_mapping(node) for node in graph.nodes()}
    mapped_bqm = bqm.relabel_variables(mapping, inplace=False)
    sampleset = qpu.sample(mapped_bqm, num_reads=1000, annealing_time=annealing_time, fast_anneal=anneal_type is AnnealType.FAST)
    energies = [e for e, o in zip(sampleset.record.energy, sampleset.record.num_occurrences) for _ in range(o)]

    return energies, sampleset.info


def plot_solution(
    pegasus_qpu_name: str,
    zephyr_qpu_name: str,
    energies_pegasus: list,
    energies_zephyr: list,
) -> go.Figure:
    """Plot histogram comparing energies.

    Args:
        pegasus_qpu_name (str): The name of the Advantage system selected.
        zephyr_qpu_name (str): The name of the Advantage2 system selected.
        energies_pegasus (list): A list of resulting energies from the Advantage system.
        energies_zephyr (list): A list of resulting energies from the Advantage2 system.

    Returns:
        fig: The histogram comparing energies.
    """

    df = pd.DataFrame({
        "Energy": energies_pegasus + energies_zephyr,
        "System": [pegasus_qpu_name] * len(energies_pegasus) + [zephyr_qpu_name] * len(energies_zephyr)
    })

    fig = px.histogram(df, x="Energy", color="System", nbins=50, barmode="overlay")
    fig.update_layout(yaxis_title="Number of reads")

    return fig
