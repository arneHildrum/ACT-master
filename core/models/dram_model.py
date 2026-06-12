# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.

from act.core.common import ACT_ROOT
from act.core.models.storage_model import StorageModel
from act.core.processes import DRAMProcess
from act.core.utils.load_yaml_with_macros import load_yaml_with_macros
from act.core.utils.units import units

DEFAULT_DRAM_CONFIG = f"{ACT_ROOT}/models/dram/dram_hynix.yaml"


class DRAMModel(StorageModel):
    """Model for estimating carbon emissions from DRAM.

    This model calculates embodied carbon for dynamic random access memory
    based on capacity and manufacturing process.
    """

    MODEL_NAME = "dram"

    def __init__(self, model_file=DEFAULT_DRAM_CONFIG) -> None:
        """Initialize the DRAM Model.

        Args:
            model_file (str): Path to the DRAM model configuration file.
        """
        # Load the DRAM model
        self.model_file = model_file
        model_data: dict = load_yaml_with_macros(self.model_file, delete_macros=True)
        dram_model = {DRAMProcess(k): units(v) for k, v in model_data.items()}
        super().__init__(fab_model=dram_model)
