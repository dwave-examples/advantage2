# Copyright 2024 D-Wave
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import annotations

from typing import Union

import dash
import dimod
import networkx as nx
import plotly.graph_objects as go
from dash import MATCH
from dash.dependencies import Input, Output, State
from dash.exceptions import PreventUpdate
from dwave.system import DWaveSampler

from demo_interface import ANNEAL_TIME_RANGES, generate_problem_details_table
from src.demo_enums import AnnealType, SchemeType
from src.utils import (
    deserialize,
    get_chip_intersection_graph,
    get_energies,
    plot_solution,
    serialize,
)


@dash.callback(
    Output({"type": "to-collapse-class", "index": MATCH}, "className"),
    inputs=[
        Input({"type": "collapse-trigger", "index": MATCH}, "n_clicks"),
        State({"type": "to-collapse-class", "index": MATCH}, "className"),
    ],
    prevent_initial_call=True,
)
def toggle_left_column(collapse_trigger: int, to_collapse_class: str) -> str:
    """Toggles a 'collapsed' class that hides and shows some aspect of the UI.

    Args:
        collapse_trigger (int): The (total) number of times a collapse button has been clicked.
        to_collapse_class (str): Current class name of the thing to collapse, 'collapsed' if not
            visible, empty string if visible.

    Returns:
        str: The new class name of the thing to collapse.
    """

    classes = to_collapse_class.split(" ") if to_collapse_class else []
    if "collapsed" in classes:
        classes.remove("collapsed")
        return " ".join(classes)
    return to_collapse_class + " collapsed" if to_collapse_class else "collapsed"


@dash.callback(
    Output("advantage-graph", "figure"),
    Output("advantage2-graph", "figure"),
    Output("chimera-g", "data"),
    Output("best-mapping", "data"),
    Output("run-button", "disabled"),
    inputs=[
        Input("advantage-setting", "value"),
        Input("advantage2-setting", "value"),
    ],
)
def render_initial_state(
    advantage_system: str, advantage2_system: str
) -> tuple[go.Figure, go.Figure, str, str, bool]:
    """Update graphs when the selected Advantage or Advantage2 systems change.

    Args:
        advantage2_system: The name of the Advantage2 system selected.
        advantage_system: The name of the Advantage system selected.

    Returns:
        graph: The Advantage graph with highlighted intersection graph.
        graph2: The Advantage2 graph with highlighted intersection graph.
        intersection_graph: The intersection chimera graph.
        best_mapping: The mapping of the chimera intersection graph onto each system
            (Advantage and Advantage2).
        run-button-disabled: Whether to disable the run button.
    """
    if (
        not advantage_system
        or not advantage2_system
        or not "Advantage" in advantage_system.split("_")[0]
    ):
        raise PreventUpdate

    graph, graph2, intersection_graph, best_mapping = get_chip_intersection_graph(
        advantage_system, advantage2_system
    )
    return graph, graph2, serialize(intersection_graph), serialize(best_mapping), False


@dash.callback(
    Output("annealing-time-setting", "min"),
    Output("annealing-time-setting", "max"),
    Output("anneal-time-help", "children"),
    inputs=[
        Input("advantage-setting", "value"),
        Input("advantage2-setting", "value"),
        Input("anneal-type-setting", "value"),
    ],
)
def update_anneal_time(
    advantage_system: str,
    advantage2_system: str,
    anneal_type: str,
) -> tuple[float, float, str]:
    """Update annealing time min/max and help text.

    Args:
        advantage2_system: The name of the Advantage2 system selected.
        advantage_system: The name of the Advantage system selected.
        anneal_type: The AnnealType, either 0: STANDARD or 1: FAST.

    Returns:
        annealing-time-setting-min: Min value for annealing time setting.
        annealing-time-setting-max: Max value for annealing time setting.
        anneal-time-help: Annealing time help text.
    """
    if (
        not advantage_system
        or not advantage2_system
        or not "Advantage" in advantage_system.split("_")[0]
    ):
        raise PreventUpdate

    anneal_type = "standard" if anneal_type is AnnealType.STANDARD.value else "fast"
    min_anneal = max(
        ANNEAL_TIME_RANGES[advantage_system][anneal_type][0],
        ANNEAL_TIME_RANGES[advantage2_system][anneal_type][0],
    )
    max_anneal = min(
        ANNEAL_TIME_RANGES[advantage_system][anneal_type][1],
        ANNEAL_TIME_RANGES[advantage2_system][anneal_type][1],
    )

    return (min_anneal, max_anneal, f"Must be between {min_anneal} and {max_anneal}")


@dash.callback(
    Output("run-button", "disabled", allow_duplicate=True),
    Input("annealing-time-setting", "value"),
    prevent_initial_call=True,
)
def validate_anneal_time(anneal_time: int) -> bool:
    """Disable run button if no annealing time."""
    return not anneal_time


@dash.callback(
    Output("results-graph", "figure"),
    Output("problem-details", "children"),
    background=True,
    inputs=[
        Input("run-button", "n_clicks"),
        State("advantage2-setting", "value"),
        State("advantage-setting", "value"),
        State("anneal-type-setting", "value"),
        State("annealing-time-setting", "value"),
        State("scheme-type-setting", "value"),
        State("precision-setting", "value"),
        State("random-seed-setting", "value"),
        State("chimera-g", "data"),
        State("best-mapping", "data"),
    ],
    running=[
        (Output("cancel-button", "className"), "", "display-none"),  # Show/hide cancel button.
        (Output("run-button", "className"), "display-none", ""),  # Hides run button while running.
        (Output("results-tab", "disabled"), True, False),  # Disables results tab while running.
        (Output("results-tab", "label"), "Loading...", "Results"),
        (Output("tabs", "value"), "input-tab", "input-tab"),  # Switch to input tab while running.
    ],
    cancel=[Input("cancel-button", "n_clicks")],
    prevent_initial_call=True,
)
def run_optimization(
    run_click: int,
    advantage2_system: str,
    advantage_system: str,
    anneal_type: Union[AnnealType, int],
    anneal_time: float,
    scheme_type: Union[SchemeType, int],
    precision: int,
    random_seed: int,
    intersection_graph: nx.Graph,
    best_mapping: dict,
) -> tuple[go.Figure, list]:
    """Runs the optimization and updates UI accordingly.

    This is the main function which is called when the ``Run Optimization`` button is clicked.
    This function takes in all form values and runs the optimization, updates the run/cancel
    buttons, deactivates (and reactivates) the results tab, and updates all relevant HTML
    components.

    Args:
        run_click: The (total) number of times the run button has been clicked.
        advantage2_system: The name of the Advantage2 system selected.
        advantage_system: The name of the Advantage system selected.
        anneal_type: The AnnealType, either 0: STANDARD or 1: FAST.
        anneal_time: The anneal time in microseconds.
        scheme_type: The SchemeType, either 0: UNIFORM or 1: POWER_LAW.
        precision: The precision for the problem.
        random_seed: The random seed for the generator.
        intersection_graph: The chimera intersection graph.
        best_mapping: The mapping of the chimera intersection graph onto each system
            (Advantage and Advantage2).

    Returns:
        A tuple containing all outputs to be used when updating the HTML
        template (in ``demo_interface.py``). These are:

            fig: The histogram comparing energies.
            problem-details: List of the table rows for the problem details table.
    """
    scheme_type = SchemeType(scheme_type)
    anneal_type = AnnealType(anneal_type)

    generator = (
        dimod.generators.ran_r if scheme_type is SchemeType.UNIFORM else dimod.generators.power_r
    )
    intersection_graph = deserialize(intersection_graph)
    best_mapping = deserialize(best_mapping)

    bqm = generator(precision, intersection_graph, seed=random_seed)

    pegasus_qpu = DWaveSampler(solver=advantage_system)
    zephyr_qpu = DWaveSampler(solver=advantage2_system)

    energies_pegasus, info_pegasus = get_energies(
        pegasus_qpu,
        intersection_graph,
        best_mapping[advantage_system],
        anneal_time,
        anneal_type,
        bqm,
    )
    energies_zephyr, info_zephyr = get_energies(
        zephyr_qpu,
        intersection_graph,
        best_mapping[advantage2_system],
        anneal_time,
        anneal_type,
        bqm,
    )

    fig = plot_solution(advantage_system, advantage2_system, energies_pegasus, energies_zephyr)

    # Generates a list of table rows for the problem details table.
    problem_details_table = generate_problem_details_table(
        {advantage2_system: info_zephyr["timing"], advantage_system: info_pegasus["timing"]}
    )

    return fig, problem_details_table
