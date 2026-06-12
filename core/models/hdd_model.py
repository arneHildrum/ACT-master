# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.

from act.core.common import ACT_ROOT
from act.core.models.storage_model import StorageModel
from act.core.processes import HDDProcess
from act.core.utils.load_yaml_with_macros import load_yaml_with_macros
from act.core.utils.units import units

DEFAULT_HDD_CONFIG = [
    f"{ACT_ROOT}/models/hdd/hdd_consumer.yaml",
    f"{ACT_ROOT}/models/hdd/hdd_enterprise.yaml",
]


class HDDModel(StorageModel):
    """Model for estimating carbon emissions from hard disk drives.

    This model calculates embodied carbon for HDDs based on capacity
    and product model.
    """

    MODEL_NAME = "hdd"

    def __init__(self, model_files=DEFAULT_HDD_CONFIG) -> None:
        """Initialize the HDD Model.

        Args:
            model_files (list[str]): Paths to HDD model configuration files.
        """

        self.model_files = model_files
        hdd_model = dict()
        for mfile in self.model_files:
            model_data = load_yaml_with_macros(mfile, delete_macros=True)
            hdd_model.update(model_data)

        hdd_model = {HDDProcess(k): units(v) for k, v in hdd_model.items()}
        super().__init__(fab_model=hdd_model)
