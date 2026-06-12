# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.

from dataclasses import dataclass, fields as dataclass_fields
from typing import Union

import pint
from act.core.carbon import SourceType
from act.core.common import (
    AbatementLevel,
    CapacitorType,
    DEFAULT_FAB_YIELD,
    ModelType,
    NA,
)
from act.core.models.ci_model import DEFAULT_BUILD_YEAR, DEFAULT_FAB_LOCATION
from act.core.processes import (
    DRAMProcess,
    HDDProcess,
    LogicProcess,
    resolve_logic_process_with_rounding,
    resolve_process,
    SSDProcess,
)
from act.core.utils.logger import log
from act.core.utils.units import dollar, mW, units


@dataclass
class DeviceData:
    """Data class for storing device specifications.

    Attributes:
        model (ModelType): The model type for carbon calculation.
        name (str): The device name.
        n_ics (int): Number of integrated circuits.
        built (int): Year the device was built.
        process (Union[LogicProcess, DRAMProcess, SSDProcess, HDDProcess]): Manufacturing process.
        fab_yield (float): Fabrication yield rate.
        fab_ci (str): Fabrication carbon intensity location.
        area (pint.Quantity): Die area.
        size (pint.Quantity): Physical size.
        weight (pint.Quantity): Device weight.
        capacity (pint.Quantity): Storage capacity.
        carbon (pint.Quantity): Manual carbon amount.
        ctype (pint.Quantity): Carbon source type for manual model.
        gpa (AbatementLevel): Gas abatement level.
        layers (int): Number of PCB layers.
        type (str): Device subtype.
        power (pint.Quantity): Operating power.
        op_ci (str): Operational carbon intensity.
        op_year (int): Year for operational carbon intensity.
        life_cycle (pint.Quantity): Hardware life cycle.
        duty_cycle (float): Device utilization rate.
        cost (str): Device cost.
    """

    model: ModelType = ModelType.LOGIC  # assume logic model by default
    name: str = None  # the device name

    # embodied paramers
    n_ics: int = 0
    built: int = DEFAULT_BUILD_YEAR
    process: Union[LogicProcess, DRAMProcess, SSDProcess, HDDProcess] = None
    fab_yield: float = DEFAULT_FAB_YIELD
    fab_ci: str = DEFAULT_FAB_LOCATION
    area: pint.Quantity = None
    size: pint.Quantity = None
    weight: pint.Quantity = None
    capacity: pint.Quantity = None
    carbon: pint.Quantity = None  # carbon amount if using manual type
    ctype: pint.Quantity = None  # carbon type if using manual model type
    gpa: AbatementLevel = None
    layers: int = None
    type: str = None

    # operational parameters
    power: pint.Quantity = None
    op_ci: str = None
    op_year: int = None
    life_cycle: pint.Quantity = None
    duty_cycle: float = None

    # cost parameters
    cost: str = 0 * dollar

    def unit_or_default(self, quant, default=None):
        """Convert a quantity to units or return a default value.

        Args:
            quant: The quantity to convert (string or pint.Quantity).
            default: Default value if quant is not a valid quantity.

        Returns:
            pint.Quantity: The converted quantity or default value.
        """
        if isinstance(quant, str):
            return units(quant)
        elif isinstance(quant, pint.Quantity):
            return quant
        else:
            return default

    def __post_init__(self):
        # cast embodied carbon fields
        self.area = self.unit_or_default(self.area)
        self.weight = self.unit_or_default(self.weight)
        self.capacity = self.unit_or_default(self.capacity)
        try:
            self.model = ModelType(self.model)
        except ValueError:
            valid_types = ", ".join(t.value for t in ModelType)
            log.critical(
                f"Device '{self.name}': Unknown model type '{self.model}'. "
                f"Valid model types are: {valid_types}"
            )
            exit(-1)
        self.size = self.unit_or_default(self.size)
        self.carbon = self.unit_or_default(self.carbon)
        self.ctype = (
            SourceType(self.ctype) if self.ctype is not None else SourceType.FABRICATION
        )
        self.gpa = (
            AbatementLevel(self.gpa) if self.gpa is not None else AbatementLevel.GPA97
        )

        if self.process is not None and isinstance(self.process, str):
            self.process = self.process.replace(
                " ", ""
            )  # trim any accidental whitespace
        if self.model in (ModelType.LOGIC, ModelType.IMEC_LOGIC, ModelType.AP):
            if self.process is not None:
                original_process = self.process
                self.process, was_rounded = resolve_logic_process_with_rounding(
                    self.process
                )
                if was_rounded:
                    log.warning(
                        f"Device '{self.name}': Technology node '{original_process}' is not available. "
                        f"Rounding to next largest available node: '{self.process.value}'."
                    )
            else:
                self.process = LogicProcess.NA
        elif self.model is ModelType.DRAM:
            self.process = (
                DRAMProcess(self.process)
                if self.process is not None
                else DRAMProcess.NA
            )
        elif self.model is ModelType.FLASH:
            self.process = (
                SSDProcess(self.process) if self.process is not None else SSDProcess.NA
            )
        elif self.model is ModelType.HDD:
            self.process = (
                HDDProcess(self.process) if self.process is not None else HDDProcess.NA
            )
        elif self.model is ModelType.MANUAL:
            self.process = resolve_process(self.process)
        else:  # by default convert with logic process for now
            self.process = LogicProcess.NA

        if self.model is ModelType.CAPACITOR:
            if self.type:
                try:
                    self.type = CapacitorType(self.type)
                except ValueError:
                    valid_types = ", ".join(t.value for t in CapacitorType)
                    log.critical(
                        f"Device '{self.name}': Unsupported capacitor type '{self.type}'. "
                        f"Valid capacitor types are: {valid_types}"
                    )
                    exit(-1)
            else:
                log.critical(
                    f"Device '{self.name}': Capacitor type must be specified. "
                    f"Valid capacitor types are: {', '.join(t.value for t in CapacitorType)}"
                )
                exit(-1)
        elif self.model is ModelType.MATERIALS:
            self.type = self.type if self.type else NA
        elif self.model is ModelType.BATTERY:
            self.type = self.type if self.type else None

        # validate physical quantities
        if self.area is not None and self.area.magnitude < 0:
            log.critical(
                f"Device '{self.name}': Area cannot be negative ({self.area}). "
                f"Please fix the bill of materials."
            )
            exit(-1)
        if self.size is not None and self.size.magnitude < 0:
            log.critical(
                f"Device '{self.name}': Size cannot be negative ({self.size}). "
                f"Please fix the bill of materials."
            )
            exit(-1)
        if self.carbon is not None and self.carbon.magnitude < 0:
            log.critical(
                f"Device '{self.name}': Carbon cannot be negative ({self.carbon}). "
                f"Please fix the bill of materials."
            )
            exit(-1)
        if self.fab_yield is not None and (self.fab_yield <= 0 or self.fab_yield > 1.0):
            log.critical(
                f"Device '{self.name}': Fabrication yield must be between 0 (exclusive) "
                f"and 1.0 (inclusive), got {self.fab_yield}. "
                f"Please fix the bill of materials."
            )
            exit(-1)

        # cast operating power fields
        self.power = self.unit_or_default(self.power, default=0 * mW)
        self.life_cycle = self.unit_or_default(self.life_cycle)
        if not isinstance(self.built, int) and self.built is not None:
            self.built = int(self.built)
        if not isinstance(self.op_year, int) and self.op_year is not None:
            self.op_year = int(self.op_year)

        # cast cost fields
        self.cost = self.unit_or_default(self.cost)
        if isinstance(self.cost, (int, float)):
            self.cost = self.cost * dollar

    def set_op_parameters(self, op_ci, op_year, duty_cycle, life_cycle, override=True):
        """Set operational parameters for this device.

        Args:
            op_ci (str): Operational carbon intensity setting.
            op_year (int): Year for operational carbon intensity lookup.
            duty_cycle (float): Device utilization rate.
            life_cycle (pint.Quantity): Hardware life cycle.
            override (bool): If True, override existing values. If False, only set if not already defined.
        """
        if override:
            self.op_ci = op_ci
            self.op_year = op_year
            self.duty_cycle = duty_cycle
            self.life_cycle = life_cycle
        else:
            if self.op_ci is None:
                self.op_ci = op_ci
            if self.op_year is None:
                self.op_year = op_year
            if self.duty_cycle is None:
                self.duty_cycle = duty_cycle
            if self.life_cycle is None:
                self.life_cycle = life_cycle


# put the device data fields into globals so that validation can refer to them
__DEVICE_DATA_INST__ = DeviceData()
_fields = dataclass_fields(__DEVICE_DATA_INST__)
DEVICE_FIELDS = {field.name.upper(): field.name for field in _fields}
globals().update(DEVICE_FIELDS)
