# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.

from act.core.common import ACT_ROOT
from act.core.models.ci_model import CIModel
from act.core.models.storage_model import StorageModel
from act.core.processes import SSDProcess
from act.core.utils.load_yaml_with_macros import load_yaml_with_macros
from act.core.utils.units import units


DEFAULT_SSD_MODEL_FILES = [
    f"{ACT_ROOT}/models/ssd/ssd_hynix.yaml",
    f"{ACT_ROOT}/models/ssd/ssd_seagate.yaml",
    f"{ACT_ROOT}/models/ssd/ssd_western.yaml",
]


class SSDModel(StorageModel):
    """Model for estimating SSD and flash fabrication emissions."""

    MODEL_NAME = "flash"

    def __init__(
        self,
        model_files=DEFAULT_SSD_MODEL_FILES,
        energy_file: str | None = None,
        non_electric_file: str | None = None,
        ci_model: CIModel | None = None,
    ) -> None:
        """
        Args:
            model_files:
                Legacy total g/GB model files.

            energy_file:
                Optional kWh/GB model for location-aware fabrication.

            non_electric_file:
                Optional non-electric g/GB model.

            ci_model:
                Shared ACT carbon-intensity model.
        """

        if (energy_file is None) != (non_electric_file is None):
            raise ValueError(
                "SSD energy_file and non_electric_file must either "
                "both be specified or both be omitted."
            )

        self.model_files = model_files
        self.energy_file = energy_file
        self.non_electric_file = non_electric_file

        ssd_model = {}

        for model_file in self.model_files:
            data = load_yaml_with_macros(
                model_file,
                delete_macros=True,
            )

            ssd_model.update(
                {
                    SSDProcess(key): units(value)
                    for key, value in data.items()
                }
            )

        energy_model = {}
        non_electric_model = {}

        if self.energy_file is not None:
            energy_data = load_yaml_with_macros(
                self.energy_file,
                delete_macros=True,
            )

            energy_model = {
                SSDProcess(key): units(value)
                for key, value in energy_data.items()
            }

            non_electric_data = load_yaml_with_macros(
                self.non_electric_file,
                delete_macros=True,
            )

            non_electric_model = {
                SSDProcess(key): units(value)
                for key, value in non_electric_data.items()
            }

        super().__init__(
            fab_model=ssd_model,
            energy_model=energy_model,
            non_electric_model=non_electric_model,
            ci_model=ci_model,
        )