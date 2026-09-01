# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.

from act.core.common import ACT_ROOT
from act.core.models.ci_model import CIModel
from act.core.models.storage_model import StorageModel
from act.core.processes import DRAMProcess
from act.core.utils.load_yaml_with_macros import load_yaml_with_macros
from act.core.utils.units import units


DEFAULT_DRAM_CONFIG = f"{ACT_ROOT}/models/dram/dram_hynix.yaml"


class DRAMModel(StorageModel):
    """Model for estimating DRAM fabrication emissions."""

    MODEL_NAME = "dram"

    def __init__(
        self,
        model_file=DEFAULT_DRAM_CONFIG,
        energy_file: str | None = None,
        non_electric_file: str | None = None,
        ci_model: CIModel | None = None,
    ) -> None:
        """
        Args:
            model_file:
                Legacy total g/GB model.

            energy_file:
                Optional kWh/GB model for location-aware fabrication.

            non_electric_file:
                Optional non-electric g/GB model.

            ci_model:
                Shared ACT carbon-intensity model.
        """

        if (energy_file is None) != (non_electric_file is None):
            raise ValueError(
                "DRAM energy_file and non_electric_file must either "
                "both be specified or both be omitted."
            )

        self.model_file = model_file
        self.energy_file = energy_file
        self.non_electric_file = non_electric_file

        model_data = load_yaml_with_macros(
            self.model_file,
            delete_macros=True,
        )

        dram_model = {
            DRAMProcess(key): units(value)
            for key, value in model_data.items()
        }

        energy_model = {}
        non_electric_model = {}

        if self.energy_file is not None:
            energy_data = load_yaml_with_macros(
                self.energy_file,
                delete_macros=True,
            )

            energy_model = {
                DRAMProcess(key): units(value)
                for key, value in energy_data.items()
            }

            non_electric_data = load_yaml_with_macros(
                self.non_electric_file,
                delete_macros=True,
            )

            non_electric_model = {
                DRAMProcess(key): units(value)
                for key, value in non_electric_data.items()
            }

        super().__init__(
            fab_model=dram_model,
            energy_model=energy_model,
            non_electric_model=non_electric_model,
            ci_model=ci_model,
        )