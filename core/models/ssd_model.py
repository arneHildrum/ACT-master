# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.

from act.core.common import ACT_ROOT
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
    """Model for estimating carbon emissions from SSDs/flash storage.

    This model calculates embodied carbon for solid state drives based on
    capacity and manufacturing process.
    """

    MODEL_NAME = "flash"

    def __init__(self, model_files=DEFAULT_SSD_MODEL_FILES) -> None:
        """Initialize the SSD Model.

        Args:
            model_files (list[str]): Paths to SSD model configuration files.
        """
        self.model_files = model_files
        ssd_model = dict()
        for model_file in self.model_files:
            data = load_yaml_with_macros(model_file, delete_macros=True)
            ssd_model.update({SSDProcess(k): units(v) for k, v in data.items()})

        super().__init__(fab_model=ssd_model)
