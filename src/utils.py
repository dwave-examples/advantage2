from demo_configs import THEME_COLOR_SECONDARY
import dimod
import networkx as nx
import dwave_networkx as dnx
from dwave.system import DWaveSampler
import matplotlib.pyplot as plt
import plotly.graph_objects as go

# import pandas as pd
# import seaborn as sns


def get_graph_intersection(pegasus_qpu_name, zephyr_qpu_name, pegasus_qpu_g, zephyr_qpu_g, chimera_g):
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

    return best_mapping


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
        mode='lines')

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


def get_fig(G, subG, pos):
    edge_trace = get_edge_trace(G, pos, "#AAAAAA", 0.5)
    node_trace = get_node_trace(G, pos, "#AAAAAA")
    edge_trace_sub = get_edge_trace(subG, pos, THEME_COLOR_SECONDARY, 1)
    node_trace_sub = get_node_trace(subG, pos, THEME_COLOR_SECONDARY)

    fig = go.Figure(
        data=[edge_trace, node_trace, edge_trace_sub, node_trace_sub],
        layout=go.Layout(
            title=dict(
                text="Advantage",
                font=dict(
                    size=16
                )
            ),
            showlegend=False,
            hovermode='closest',
            margin=dict(b=20,l=5,r=5,t=40),
            paper_bgcolor="rgba(0, 0, 0, 0)",
            plot_bgcolor="rgba(0, 0, 0, 0)",
            xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            yaxis=dict(showgrid=False, zeroline=False, showticklabels=False)
        )
    )

    return fig



def get_chip_intersection_graph(pegasus_qpu_name, zephyr_qpu_name):
    pegasus_qpu = DWaveSampler(solver=pegasus_qpu_name, profile="defaults")
    pegasus_qpu_g = pegasus_qpu.to_networkx_graph()
    zephyr_qpu = DWaveSampler(solver=zephyr_qpu_name, profile="alpha")  # accessed through alpha server atm
    zephyr_qpu_g = zephyr_qpu.to_networkx_graph()

    max_chimera_intersection = min(
        pegasus_qpu.properties["topology"]["shape"][0] - 1,
        zephyr_qpu.properties["topology"]["shape"][0] * 2,
    )
    chimera_g = dnx.chimera_graph(max_chimera_intersection)

    best_mapping = get_graph_intersection(pegasus_qpu_name, zephyr_qpu_name, pegasus_qpu_g, zephyr_qpu_g, chimera_g)

    p_mapping = best_mapping[pegasus_qpu_name]
    z_mapping = best_mapping[zephyr_qpu_name]

    sub = nx.relabel_nodes(chimera_g, p_mapping)
    sub2 = nx.relabel_nodes(chimera_g, z_mapping)
    pegasus_pos = dnx.drawing.pegasus_layout(dnx.pegasus_graph(16), crosses=True)
    zephyr_pos = dnx.drawing.zephyr_layout(dnx.zephyr_graph(12))
    
    fig = get_fig(pegasus_qpu_g, sub, pegasus_pos)
    fig2 = get_fig(zephyr_qpu_g, sub2, zephyr_pos)

    return fig, fig2
