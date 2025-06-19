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

"""This file stores input parameters for the app."""

# THEME_COLOR is used for the button, text, and banner and should be dark
# and pass accessibility checks with white: https://webaim.org/resources/contrastchecker/
# THEME_COLOR_SECONDARY can be light or dark and is used for sliders, loading icon, and tabs
THEME_COLOR = "#074C91"  # D-Wave dark blue default #074C91
THEME_COLOR_SECONDARY = "#2A7DE1"  # D-Wave blue default #2A7DE1

THUMBNAIL = "static/dwave_logo.svg"

APP_TITLE = "Advantage2"
MAIN_HEADER = "Advantage2 Performance Comparison"
DESCRIPTION = """\
Choose an Advantage and Advantage2 system to view the highest-yielded intersection graph and run
random spin-glass problems on both to compare energies."""

#######################################
# Sliders, buttons and option entries #
#######################################

DEFAULT_ADVANTAGE2 = "Advantage2_system1.2"
DEFAULT_ADVANTAGE = "Advantage_system4.1"

PRECISION_OPTIONS = [2 ** n for n in range(11)]
PRECISION_DEFAULT = 128  # must be included in the list above
