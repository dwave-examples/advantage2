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

from enum import Enum


class AnnealType(Enum):
    """Options for type of annealing."""

    STANDARD = 0
    FAST = 1

    @property
    def label(self):
        return {
            AnnealType.STANDARD: "Standard Anneal",
            AnnealType.FAST: "Fast Anneal",
        }[self]


class SchemeType(Enum):
    """The strategy for choosing weights."""

    UNIFORM = 0
    POWER_LAW = 1

    @property
    def label(self):
        return {
            SchemeType.UNIFORM: "Uniform",
            SchemeType.POWER_LAW: "Power Law",
        }[self]
