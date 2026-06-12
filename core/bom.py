# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.

import os
from dataclasses import dataclass, field

import pint
from act.core.device_data import DeviceData
from act.core.utils.load_yaml_with_macros import load_yaml_with_macros
from act.core.utils.units import units

DEVICES = "devices"
MODEL = "model"
IMPORTS = "imports"
SUBSYSTEM_DELIMITER = "."
YAML_EXTENSION = ".yaml"


@dataclass
class BOM:
    """Bill of Materials data class for specifying device components.

    Attributes:
        name (str): Name of the bill of materials.
        description (str): Description of the BOM.
        macros (dict): Macro definitions for YAML processing.
        devices (dict): Dictionary of device specifications.
        imports (dict): Files to import additional device definitions from.
        file (str): Original file path for this BOM.
        duty_cycle (float): Default device utilization rate.
        life_cycle (pint.Quantity): Default hardware life cycle.
        op_power (str): Operating power specification.
        op_ci (str): Operational carbon intensity setting.
        op_year (int): Year for operational carbon intensity lookup.
        cl_macros (dict[str, str]): Command line macros.
        expected_carbon (str): Expected carbon value for validation.
        parameters (dict): Configuration parameter overrides.
    """

    name: str = "Default Materials List Name"
    description: str = ""
    macros: dict = field(default=None)
    devices: dict = field(default=None)
    imports: dict = field(default=None)
    file: str = None
    duty_cycle: float = None
    life_cycle: pint.Quantity = None
    op_power: str = None
    op_ci: str = None
    op_year: int = None
    cl_macros: dict[str, str] = field(default_factory=dict)
    expected_carbon: str = None
    parameters: dict = field(default=None)

    def __post_init__(self):
        # convert the devices annotation data structure
        devices = dict()
        if self.devices is not None:
            for dname, devices_data in self.devices.items():
                annotation = DeviceData(
                    **devices_data,
                    name=dname,
                )
                devices[dname] = annotation
        self.devices = devices

        # convert the power if it is specified
        if self.op_power is not None:
            self.op_power = units(self.op_power)
        if self.expected_carbon is not None:
            self.expected_carbon = units(self.expected_carbon)
        if self.life_cycle is not None:
            self.life_cycle = units(self.life_cycle)

        # import data from additional files if specified which should already be casted properly
        if self.imports is not None:
            for iname, import_spec in self.imports.items():
                if isinstance(import_spec, dict):
                    filepath = import_spec.get("file")
                    import_macros = {
                        k: str(v) for k, v in import_spec.get("macros", {}).items()
                    }
                else:
                    filepath = import_spec
                    import_macros = {}
                path = os.path.dirname(self.file) + "/" + filepath
                file_data = load_yaml_with_macros(path, cl_macros=import_macros)
                imported_bom = BOM(
                    **file_data,
                    file=path,
                )
                for name, data in imported_bom.devices.items():
                    self.devices[f"{iname}{SUBSYSTEM_DELIMITER}{name}"] = data

    def set_op_parameters(self, op_ci, op_year, duty_cycle, life_cycle, override=True):
        """Set operational parameters for all devices in the BOM.

        Args:
            op_ci (str): Operational carbon intensity setting.
            op_year (int): Year for operational carbon intensity lookup.
            duty_cycle (float): Device utilization rate.
            life_cycle (pint.Quantity): Hardware life cycle.
            override (bool): If True, override existing device parameters. If False, only set if not already defined.
        """
        for dev in self.devices.values():
            dev.set_op_parameters(
                op_ci=op_ci,
                op_year=op_year,
                duty_cycle=duty_cycle,
                life_cycle=life_cycle,
                override=override,
            )
