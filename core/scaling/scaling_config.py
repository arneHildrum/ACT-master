# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.

from dataclasses import dataclass, field

from act.core.processes import DRAMProcess, HDDProcess, LogicProcess, SSDProcess
from act.core.utils.logger import log


@dataclass
class ScalingEntry:
    """Configuration entry for scaling a single device.

    Attributes:
        process (str): Target technology node to scale to.
        year (int): Target year for carbon intensity scaling.
        location (str): Target fabrication location to scale to.
    """

    process: str = None  # target technology node to scale to
    year: int = None  # target year for CI to scale to
    location: str = None  # target fabrication location to scale to

    def __post_init__(self):
        # attempt to cast the target process if it's specified
        if self.process is not None:
            _process = None
            for Enum in [LogicProcess, DRAMProcess, SSDProcess, HDDProcess]:
                try:
                    _process = Enum(self.process)
                except ValueError:
                    continue
            if _process is None:
                log.critical(
                    f"Technology scaling file could not load a target process {self.process}. Ensure the process is correct and exists."
                )
            self.process = _process


@dataclass
class ScalingConfig:
    """Configuration for scaling multiple devices.

    Attributes:
        name (str): Name of the scaling configuration.
        compatible_with (list): List of compatible BOM names.
        scaling_paths (dict): Dictionary mapping device names to ScalingEntry objects.
        macros (dict): Macro definitions for YAML processing.
    """

    name: str
    compatible_with: list = field(default_factory=list)
    scaling_paths: dict = field(default_factory=dict)
    macros: dict = field(default_factory=dict)

    def __post_init__(self):
        # load the
        if type(self.compatible_with) is not list:
            self.compatible_with = [self.compatible_with]

        # load the scaling configurations
        _scaling_paths = dict()
        for path, data in self.scaling_paths.items():
            _scaling_paths[path] = ScalingEntry(**data)
        self.scaling_paths = _scaling_paths
