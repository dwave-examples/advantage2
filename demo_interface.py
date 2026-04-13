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

"""This file stores the Dash HTML layout for the app."""
from __future__ import annotations
from enum import EnumMeta

from dash import dcc, html
import dash_mantine_components as dmc
from dwave.cloud import Client

from demo_configs import (
    DEFAULT_ADVANTAGE,
    DEFAULT_ADVANTAGE2,
    DESCRIPTION,
    MAIN_HEADER,
    PRECISION_DEFAULT,
    PRECISION_OPTIONS,
    THUMBNAIL,
)
from src.demo_enums import AnnealType, SchemeType

THEME_COLOR = "#2d4376"

ANNEAL_TIME_RANGES = {}

# Initialize: available QPUs
try:
    client = Client.from_config(client="qpu")
    qpus = client.get_solvers()
    qpus = [qpu for qpu in qpus if "internal" not in qpu.name]

    for qpu in qpus:
        ANNEAL_TIME_RANGES[qpu.name] = {
            "fast": qpu.properties["fast_anneal_time_range"],
            "standard": qpu.properties["annealing_time_range"],
        }

    qpus = [qpu.name for qpu in qpus]
    ADVANTAGE_SOLVERS = [solver for solver in qpus if solver.split("_")[0] == "Advantage"]
    ADVANTAGE2_SOLVERS = [solver for solver in qpus if solver.split("_")[0] == "Advantage2"]

    if not len(ADVANTAGE_SOLVERS) or not len(ADVANTAGE2_SOLVERS):
        raise Exception

except Exception:
    ADVANTAGE_SOLVERS = ADVANTAGE2_SOLVERS = ["No Leap Access"]


def slider(label: str, id: str, config: dict) -> html.Div:
    """Slider element for value selection.

    Args:
        label: The title that goes above the slider.
        id: A unique selector for this element.
        config: A dictionary of slider configurations, see dmc.Slider Dash Mantine docs.
    """
    return html.Div(
        className="slider-wrapper",
        children=[
            html.Label(label, htmlFor=id),
            dmc.Slider(
                id=id,
                className="slider",
                **config,
                marks=[
                    {"value": config["min"], "label": f'{config["min"]}'},
                    {"value": config["max"], "label": f'{config["max"]}'},
                ],
                labelAlwaysOn=True,
                thumbLabel=f"{label} slider",
                color=THEME_COLOR,
            ),
        ],
    )


def dropdown(label: str, id: str, options: list, value: str | None = None) -> html.Div:
    """Dropdown element for option selection.

    Args:
        label: The title that goes above the dropdown.
        id: A unique selector for this element.
        options: A list of dictionaries of labels and values.
        value: The value of the dropdown that should be preselected.
    """
    return html.Div(
        className="dropdown-wrapper",
        children=[
            html.Label(label, htmlFor=id),
            dmc.Select(
                id=id,
                data=options,
                value=value if value else options[0]["value"],
                allowDeselect=False,
            ),
        ],
    )


def radio(label: str, id: str, options: list, value: str, inline: bool = True) -> html.Div:
    """Radio element for option selection.

    Args:
        label: The title that goes above the radio.
        id: A unique selector for this element.
        options: A list of dictionaries of labels and values.
        value: The value of the radio that should be preselected.
        inline: Whether the options are displayed beside or below each other.
    """
    return html.Div(
        className="radio-wrapper",
        children=[
            dmc.RadioGroup(
                id=id,
                className=f"radio{' radio--inline' if inline else ''}",
                label=label,
                value=value,
                children=dmc.Group(
                    [
                        dmc.Radio(option["label"], value=option["value"], color=THEME_COLOR)
                        for option in options
                    ]
                ),
            ),
        ],
    )


def generate_options(options: list | EnumMeta) -> list[dict]:
    """Generates options for dropdowns, checklists, radios, etc."""
    if isinstance(options, EnumMeta):
        return [
            {"label": option.label, "value": f"{option.value}"} for option in options
        ]

    return [{"label": f"{option}", "value": f"{option}"} for option in options]


def generate_settings_form() -> html.Div:
    """This function generates settings for selecting the scenario, model, and solver.

    Returns:
        html.Div: A Div containing the settings for selecting the scenario, model, and solver.
    """
    radio_options_anneal = generate_options(AnnealType)
    radio_options_scheme = generate_options(SchemeType)
    advantage_options = generate_options(ADVANTAGE_SOLVERS)
    advantage2_options = generate_options(ADVANTAGE2_SOLVERS)
    precision_options = generate_options(PRECISION_OPTIONS)

    advantage = (
        DEFAULT_ADVANTAGE if DEFAULT_ADVANTAGE in ADVANTAGE_SOLVERS else ADVANTAGE_SOLVERS[0]
    )
    advantage2 = (
        DEFAULT_ADVANTAGE2 if DEFAULT_ADVANTAGE2 in ADVANTAGE2_SOLVERS else ADVANTAGE2_SOLVERS[0]
    )

    min_anneal = max_anneal = 0
    if advantage.split("_")[0] == "Advantage" and advantage2.split("_")[0] == "Advantage2":
        min_anneal = max(
            ANNEAL_TIME_RANGES[advantage]["standard"][0],
            ANNEAL_TIME_RANGES[advantage2]["standard"][0],
        )
        max_anneal = min(
            ANNEAL_TIME_RANGES[advantage]["standard"][1],
            ANNEAL_TIME_RANGES[advantage2]["standard"][1],
        )

    return html.Div(
        className="settings",
        children=[
            html.H6("Comparison Systems"),
            html.Div(
                [
                    dropdown(
                        "Advantage2",
                        "advantage2-setting",
                        sorted(advantage2_options, key=lambda op: op["value"]),
                        value=advantage2,
                    ),
                    dropdown(
                        "Advantage",
                        "advantage-setting",
                        sorted(advantage_options, key=lambda op: op["value"]),
                        value=advantage,
                    ),
                ],
                className="settings-flex no-margin-label",
            ),
            html.H6("Optimization Problem"),
            radio(
                "Weight Distribution",
                "scheme-type-setting",
                sorted(radio_options_scheme, key=lambda op: op["value"]),
                "1",
            ),
            html.Div(
                [
                    dropdown(
                        "Weight Precision",
                        "precision-setting",
                        precision_options,
                        value=PRECISION_DEFAULT,
                    ),
                    html.Div(
                        [
                            html.Label("Weight Random Seed", htmlFor="random-seed-setting"),
                            dmc.NumberInput(
                                id="random-seed-setting",
                                type="number",
                            ),
                        ]
                    )
                ],
                className="settings-flex",
            ),
            html.H6("Annealing Protocol"),
            radio(
                "Anneal Type",
                "anneal-type-setting",
                sorted(radio_options_anneal, key=lambda op: op["value"]),
                "0",
            ),
            html.Label("Annealing Time (microseconds)", htmlFor="annealing-time-setting"),
            dmc.NumberInput(
                id="annealing-time-setting",
                type="number",
                min=min_anneal,
                max=max_anneal,
                value=500,
            ),
            html.P(id="anneal-time-help", **{"role": "presentation"}),
        ],
    )


def generate_run_buttons() -> html.Div:
    """Run and cancel buttons to run the optimization."""
    return html.Div(
        id="button-group",
        children=[
            html.Button("Run Job", id="run-button", className="button"),
            html.Button(
                "Cancel Job",
                id="cancel-button",
                className="button",
                style={"display": "none"},
            ),
        ],
    )


def generate_problem_details_table(info: dict[str, dict]) -> list[html.Thead, html.Tbody]:
    """Generates table for the problem details table.

    Args:
        info: Dictionary of system keys and timing details dictionaries.

    Returns:
        list[html.Thead, html.Tbody]: The table header and body for the problem details table.
    """
    table_rows = [[key, *list(timing.values())] for key, timing in info.items()]

    table_headers = ["System"]
    for time_key in info[table_rows[0][0]].keys():
        time_key = [t.capitalize() for t in time_key.split("_")]
        if time_key[0] == "Qpu":
            time_key = time_key[1:]
        table_headers.append(" ".join(time_key))

    return [
        html.Thead([html.Tr([html.Th(header) for header in table_headers])]),
        html.Tbody([html.Tr([html.Td(cell) for cell in row]) for row in table_rows]),
    ]


def problem_details(index: int) -> html.Div:
    """Generate the problem details section.

    Args:
        index: Unique element id to differentiate matching elements.
            Must be different from left column collapse button.

    Returns:
        html.Div: Div containing a collapsable table.
    """
    return html.Div(
        id={"type": "to-collapse-class", "index": index},
        className="details-collapse-wrapper collapsed",
        children=[
            # Problem details collapsible button and header
            html.Button(
                id={"type": "collapse-trigger", "index": index},
                className="details-collapse",
                children=[
                    html.H5("Problem Details"),
                    html.Div(className="collapse-arrow"),
                ],
                **{"aria-expanded": "true"},
            ),
            html.Div(
                className="details-to-collapse",
                id="problem-details",
            ),
        ],
    )


def create_interface():
    """Set the application HTML."""
    return html.Div(
        id="app-container",
        children=[
            html.A(  # Skip link for accessibility
                "Skip to main content",
                href="#main-content",
                id="skip-to-main",
                className="skip-link",
                tabIndex=1,
            ),
            # Below are any temporary storage items, e.g., for sharing data between callbacks.
            dcc.Store(id="pegasus-qpu"),
            dcc.Store(id="zephyr-qpu"),
            dcc.Store(id="chimera-g"),
            dcc.Store(id="best-mapping"),
            # Settings and results columns
            html.Main(
                className="columns-main",
                id="main-content",
                children=[
                    # Left column
                    html.Div(
                        id={"type": "to-collapse-class", "index": 0},
                        className="left-column",
                        children=[
                            html.Div(
                                className="left-column-layer-1",  # Fixed width Div to collapse
                                children=[
                                    html.Div(
                                        className="left-column-layer-2",  # Padding and content wrapper
                                        children=[
                                            html.Div(
                                                [
                                                    html.H1(MAIN_HEADER),
                                                    html.P(DESCRIPTION),
                                                ],
                                                className="title-section",
                                            ),
                                            html.Div(
                                                [
                                                    html.Div(
                                                        html.Div(
                                                            [
                                                                generate_settings_form(),
                                                                generate_run_buttons(),
                                                            ],
                                                            className="settings-and-buttons",
                                                        ),
                                                        className="settings-and-buttons-wrapper",
                                                    ),
                                                    # Left column collapse button
                                                    html.Div(
                                                        html.Button(
                                                            id={
                                                                "type": "collapse-trigger",
                                                                "index": 0,
                                                            },
                                                            className="left-column-collapse",
                                                            title="Collapse sidebar",
                                                            children=[
                                                                html.Div(className="collapse-arrow")
                                                            ],
                                                            **{"aria-expanded": "true"},
                                                        ),
                                                    ),
                                                ],
                                                className="form-section",
                                            ),
                                        ],
                                    )
                                ],
                            ),
                        ],
                    ),
                    # Right column
                    html.Div(
                        className="right-column",
                        children=[
                            dmc.Tabs(
                                id="tabs",
                                value="input-tab",
                                color="white",
                                children=[
                                    html.Header(
                                        className="banner",
                                        children=[
                                            html.Nav(
                                                [
                                                    dmc.TabsList(
                                                        [
                                                            dmc.TabsTab("Input", value="input-tab"),
                                                            dmc.TabsTab(
                                                                "Results",
                                                                value="results-tab",
                                                                id="results-tab",
                                                                disabled=True,
                                                            ),
                                                        ]
                                                    ),
                                                ]
                                            ),
                                            html.Img(src=THUMBNAIL, alt="D-Wave logo"),
                                        ],
                                    ),
                                    dmc.TabsPanel(
                                        value="input-tab",
                                        tabIndex="12",
                                        children=[
                                            html.Div(
                                                className="tab-content-wrapper",
                                                children=[
                                                    dcc.Loading(
                                                        parent_className="input",
                                                        type="circle",
                                                        color=THEME_COLOR,
                                                        children=[
                                                            html.Div(
                                                                className="graph-wrapper",
                                                                children=[
                                                                    html.Div(
                                                                        dcc.Graph(
                                                                            id="advantage-graph",
                                                                            responsive=True,
                                                                            config={
                                                                                "displayModeBar": False
                                                                            },
                                                                        ),
                                                                        className="graph",
                                                                    ),
                                                                    html.Div(
                                                                        dcc.Graph(
                                                                            id="advantage2-graph",
                                                                            responsive=True,
                                                                            config={
                                                                                "displayModeBar": False
                                                                            },
                                                                        ),
                                                                        className="graph",
                                                                    ),
                                                                ],
                                                            ),
                                                        ],
                                                    )
                                                ]
                                            )
                                        ],
                                    ),
                                    dmc.TabsPanel(
                                        value="results-tab",
                                        tabIndex="13",
                                        children=[
                                            html.Div(
                                                className="tab-content-wrapper",
                                                children=[
                                                    dcc.Loading(
                                                        parent_className="results",
                                                        type="circle",
                                                        color=THEME_COLOR,
                                                        children=html.Div(
                                                            html.Div(
                                                                dcc.Graph(
                                                                    id="results-graph",
                                                                    responsive=True,
                                                                    config={
                                                                        "displayModeBar": False
                                                                    },
                                                                ),
                                                                className="graph",
                                                            ),
                                                            className="graph-wrapper",
                                                        ),
                                                    ),
                                                    # Problem details dropdown
                                                    html.Div([html.Hr(), problem_details(1)]),
                                                ],
                                            )
                                        ],
                                    ),
                                ],
                            )
                        ],
                    ),
                ],
            ),
        ],
    )
