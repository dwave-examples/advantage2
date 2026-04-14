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

THUMBNAIL = "static/dwave_logo.svg"

APP_TITLE = "Performance Comparison"
MAIN_HEADER = "Performance Comparison"
DESCRIPTION = """\
Choose an Advantage and Advantage2 system to view the highest-yielded intersection graph and run
random spin-glass problems on both to compare energies."""

#######################################
# Sliders, buttons and option entries #
#######################################

DEFAULT_ADVANTAGE2 = "Advantage2_system1"
DEFAULT_ADVANTAGE = "Advantage_system4.1"

PRECISION_OPTIONS = [2**n for n in range(11)]
PRECISION_DEFAULT = "128"  # must be included in the list above
