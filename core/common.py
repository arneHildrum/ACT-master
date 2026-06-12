# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.

import os
from enum import Enum

from act.core.utils.units import g, year

ACT_ROOT = os.path.dirname(__file__) + "/.."

MACROS = "macros"

DEFAULT_FAB_YIELD = 0.875
NA = "na"

DEFAULT_BUILD_YEAR = 2023
DEFAULT_OP_YEAR = 2023
DEFAULT_LIFE_CYCLE = 2 * year
DEFAULT_DUTY_CYCLE = 1.0


class AbatementLevel(Enum):
    GPA95 = 95
    GPA97 = 97
    GPA99 = 99


class ModelType(Enum):
    LOGIC = "logic"
    IMEC_LOGIC = "imec_logic"
    AP = "ap"
    DRAM = "dram"
    FLASH = "flash"
    HDD = "hdd"
    MANUAL = "manual"
    MATERIALS = "materials"
    CAPACITOR = "capacitor"
    RESISTOR = "resistor"
    DIODE = "diode"
    PCB = "pcb"
    BATTERY = "battery"
    SIGNAL_BEAD = "signal bead"
    POWER = "power"
    OTHER = "other"


class CapacitorType(Enum):
    MLCC = "mlcc"
    TEC = "tec"


PASSIVE_MODEL_TYPES = [
    ModelType.CAPACITOR,
    ModelType.RESISTOR,
    ModelType.DIODE,
    ModelType.SIGNAL_BEAD,
]
MATERIALS_MODEL_TYPES = [
    ModelType.MATERIALS,
    ModelType.PCB,
    ModelType.BATTERY,
]

# IC packaging cost
CARBON_PER_IC_PACKAGE = 150 * g

# BOM parameters field names for cost analysis configuration
DEFAULT_ELECTRICITY_COST = "DEFAULT_ELECTRICITY_COST"
DEFAULT_CARBON_OFFSET_COST = "carbon_offset_cost"
