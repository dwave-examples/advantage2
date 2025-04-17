from demo_configs import THEME_COLOR_SECONDARY
from src.demo_enums import AnnealType
import dimod
import networkx as nx
import dwave_networkx as dnx
from dwave.system import DWaveSampler
import plotly.graph_objects as go
import plotly.express as px
import base64
from typing import Any
import dill as pickle
import pandas as pd

def serialize(obj: Any) -> str:
    """Serialize the object using pickle"""
    return base64.b64encode(pickle.dumps(obj)).decode("utf-8")


def deserialize(obj: str) -> Any:
    """Deserialize the object"""
    return pickle.loads(base64.b64decode(obj.encode("utf-8")))


def get_edge_trace(G, pos, color, line_width):
    edge_x = []
    edge_y = []
    for edge in G.edges():
        x0, y0 = pos[edge[0]]
        x1, y1 = pos[edge[1]]
        edge_x.append(x0)
        edge_x.append(x1)
        edge_x.append(None)
        edge_y.append(y0)
        edge_y.append(y1)
        edge_y.append(None)

    edge_trace = go.Scatter(
        x=edge_x, y=edge_y,
        line=dict(width=line_width, color=color),
        hoverinfo='none',
        mode='lines'
    )

    return edge_trace


def get_node_trace(G, pos, color):
    node_x = []
    node_y = []
    for node in G.nodes():
        x, y = pos[node]
        node_x.append(x)
        node_y.append(y)

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


def get_fig(G, subG, pos, title):
    edge_trace = get_edge_trace(G, pos, "#AAAAAA", 0.5)
    node_trace = get_node_trace(G, pos, "#AAAAAA")
    edge_trace_sub = get_edge_trace(subG, pos, THEME_COLOR_SECONDARY, 1)
    node_trace_sub = get_node_trace(subG, pos, THEME_COLOR_SECONDARY)

    fig = go.Figure(
        data=[edge_trace, node_trace, edge_trace_sub, node_trace_sub],
        layout=go.Layout(
            title=dict(
                text=title,
                font=dict(
                    size=16
                )
            ),
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


def get_chip_intersection_graph(pegasus_qpu_name, zephyr_qpu_name):
    pegasus_qpu = DWaveSampler(solver=pegasus_qpu_name)
    pegasus_qpu_g = pegasus_qpu.to_networkx_graph()
    zephyr_qpu = DWaveSampler(solver=zephyr_qpu_name)  # accessed through alpha server atm
    zephyr_qpu_g = zephyr_qpu.to_networkx_graph()

    max_chimera_intersection = min(
        pegasus_qpu.properties["topology"]["shape"][0] - 1,
        zephyr_qpu.properties["topology"]["shape"][0] * 2,
    )
    chimera_g = dnx.chimera_graph(max_chimera_intersection)

    # search for the highest-yielded instersection graph
    best_mapping = {}
    for name, qpu_g, mapper in [
        (
            pegasus_qpu_name,
            pegasus_qpu_g,
            dnx.pegasus_sublattice_mappings,
        ),
        (zephyr_qpu_name, zephyr_qpu_g, dnx.zephyr_sublattice_mappings),
    ]:

        mappings = mapper(chimera_g, qpu_g)  # get all possible mappings between both graphs

        # select the most yielded mapping
        mapping = {}
        coupler_yield = 0
        for m in mappings:
            edges = [edge for edge in chimera_g.edges if tuple(map(m, edge)) in qpu_g.edges]
            if len(edges) > coupler_yield:
                mapping = m
                coupler_yield = len(edges)

        # add the defects to the chimera graph
        edges = [
            edge for edge in chimera_g.edges if tuple(map(mapping, edge)) in qpu_g.edges
        ]
        chimera_g = chimera_g.edge_subgraph(edges).copy()

        best_mapping[name] = mapping

    p_mapping = best_mapping[pegasus_qpu_name]
    z_mapping = best_mapping[zephyr_qpu_name]

    sub = nx.relabel_nodes(chimera_g, p_mapping)
    sub2 = nx.relabel_nodes(chimera_g, z_mapping)
    pegasus_pos = dnx.drawing.pegasus_layout(dnx.pegasus_graph(16), crosses=True)
    zephyr_pos = dnx.drawing.zephyr_layout(dnx.zephyr_graph(12))
    
    fig = get_fig(pegasus_qpu_g, sub, pegasus_pos, "Advantage")
    fig2 = get_fig(zephyr_qpu_g, sub2, zephyr_pos, "Advantage2")

    return fig, fig2, chimera_g, best_mapping


def get_energies(name, qpu, best_mapping, chimera_g, annealing_time, anneal_type, bqm):
    mapping = {node: best_mapping[name](node) for node in chimera_g.nodes()}
    mapped_bqm = bqm.relabel_variables(mapping, inplace=False)
    sampleset = qpu.sample(mapped_bqm, num_reads=1000, annealing_time=annealing_time, fast_anneal=anneal_type is AnnealType.FAST)
    energies = [e for e, o in zip(sampleset.record.energy, sampleset.record.num_occurrences) for _ in range(o)]
    return energies


def plot_solution(
    bqm, pegasus_qpu_name, zephyr_qpu_name, annealing_time, chimera_g, best_mapping, anneal_type
):
    pegasus_qpu = DWaveSampler(solver=pegasus_qpu_name)
    zephyr_qpu = DWaveSampler(solver=zephyr_qpu_name)  # accessed through alpha server atm

    energies_pegasus = get_energies(pegasus_qpu_name, pegasus_qpu, best_mapping, chimera_g, annealing_time, anneal_type, bqm)
    energies_zephyr = get_energies(zephyr_qpu_name, zephyr_qpu, best_mapping, chimera_g, annealing_time, anneal_type, bqm)
    df = pd.DataFrame({
        "Energy": energies_pegasus + energies_zephyr,
        "System": [pegasus_qpu_name] * len(energies_pegasus) + [zephyr_qpu_name] * len(energies_zephyr)
    })
    print(len(energies_pegasus)/10)
    fig = px.histogram(df, x="Energy", color="System", nbins=int(len(energies_pegasus)/10))
    fig.update_layout(yaxis_title="Number of reads")

    return fig
