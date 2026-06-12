# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.

from copy import deepcopy

from act.core.carbon import Carbon, SourceType
from act.core.common import ModelType
from act.core.processes import (
    DRAMProcess,
    HDDProcess,
    LOGIC_DATA,
    LogicProcess,
    NOT_SCALING_PROCESSES,
    SSDProcess,
)
from act.core.scaling.power_scaling_model import PowerScalingModel
from act.core.utils.logger import log
from act.core.utils.units import g


class TechScalingManager:
    """Manager for applying technology scaling to carbon analysis.

    This class handles scaling of power consumption and embodied carbon
    when projecting devices to different technology nodes.

    Attributes:
        power_scaling_model (PowerScalingModel): Model for power scaling factors.
    """

    def __init__(self):
        """Initialize the Technology Scaling Manager."""
        self.power_scaling_model = PowerScalingModel()

    def apply_power_scaling(self, bom, scaling_config):
        """Apply power technology scaling to devices in the BOM.

        Must be applied prior to carbon analysis.

        Args:
            bom (BOM): The bill of materials to modify.
            scaling_config (ScalingConfig): Configuration specifying target processes.
        """

        # for each device that matches in the tech scaling config path, override the process with the specified one
        if scaling_config is None:
            return

        for dname, dev in bom.devices.items():
            for path, data in scaling_config.scaling_paths.items():
                if data.process is None or not dname.startswith(path):
                    continue
                dst_process = data.process
                src_process = dev.process

                if not isinstance(src_process, type(dst_process)):
                    log.warning(
                        f"Attempted to scale device {dname} which has original process {src_process} to new process {dst_process}. Scaling will not be applied as these process types are incompatible."
                    )
                    continue

                # apply the power scaling factor only if the model is logic or AP since those are the only ones we have power scaling factors for
                if isinstance(dev.process, LogicProcess):
                    scale_factor = self.power_scaling_model.get_scale_factor(
                        src=src_process, dst=dst_process
                    )
                    assert scale_factor > 0
                    dev.power *= scale_factor

    def apply_tech_scaling(self, act):
        """Apply technology scaling to embodied carbon results.

        Must be applied after carbon analysis since it modifies results.

        Args:
            act (ACTModel): The ACT model with completed analysis.
        """

        act_results = act.results
        bom = act.bom
        logic_model = act.logic_model
        dram_model = act.dram_model
        ssd_model = act.ssd_model
        hdd_model = act.hdd_model
        scaling_config = act.scaling_config

        # for each device that matches in the tech scaling config path, override the process with the specified one
        if scaling_config is None:
            return

        # only apply technology scaling to the silicon devices as scaling for other devices is ill-defined
        for dname in act_results.carbon_by_device:
            for path, data in scaling_config.scaling_paths.items():
                if data.process is None or not dname.startswith(path):
                    continue

                dst_process = data.process
                dev = bom.devices[dname]
                model = dev.model
                src_process = dev.process

                if not isinstance(src_process, type(dst_process)):
                    log.warning(
                        f"Attempted to scale device {dname} which has original process {src_process} to new process {dst_process}. Scaling will not be applied as these process types are incompatible."
                    )
                    continue
                elif (
                    src_process in NOT_SCALING_PROCESSES
                    or dst_process in NOT_SCALING_PROCESSES
                ):
                    continue  # don't scale if process is NA

                # if this is a logic process, the die area needs to also be scaled
                if isinstance(src_process, LogicProcess):
                    area_scale_factor = (
                        LOGIC_DATA[dst_process].size / LOGIC_DATA[src_process].size
                    ) ** 2

                    # for logic carbon, call logic model since there are other partials
                    if model is ModelType.LOGIC:
                        scaled_dev = deepcopy(dev)
                        scaled_dev.process = dst_process
                        scaled_area = dev.area * area_scale_factor
                        scaled_dev.area = scaled_area
                        scaled_carbon = logic_model.get_carbon(scaled_dev)
                    # for manual models, the area is not provided so just directly scale
                    elif model is ModelType.MANUAL:
                        scaled_carbon = (
                            Carbon(dev.carbon, dev.ctype) * area_scale_factor
                        )

                    else:
                        raise NotImplementedError(
                            f"Model type {model} does not have a technology scaling calculation."
                        )

                    act_results.carbon_by_device[dname].set_partials(scaled_carbon)
                else:
                    if isinstance(src_process, DRAMProcess):
                        scale_factor = (
                            dram_model.fab_model[dst_process]
                            / dram_model.fab_model[src_process]
                        )
                    elif isinstance(src_process, HDDProcess):
                        scale_factor = (
                            hdd_model.fab_model[dst_process]
                            / hdd_model.fab_model[src_process]
                        )
                    elif isinstance(src_process, SSDProcess):
                        scale_factor = (
                            ssd_model.fab_model[dst_process]
                            / ssd_model.fab_model[src_process]
                        )
                    else:
                        raise TypeError(
                            f"Unsupported scaling process type {src_process} with type {type(src_process)}."
                        )

                    # only scale the fabrication cost as the IC packaging cost model is currently orthogonal
                    unscaled_carbon = act_results.carbon_by_device[dname].partial(
                        SourceType.FABRICATION
                    )

                    if unscaled_carbon > 0 * g:
                        scaled_carbon = unscaled_carbon * scale_factor
                        act_results.carbon_by_device[dname].set_partial(
                            ctype=SourceType.FABRICATION, amt=scaled_carbon
                        )
