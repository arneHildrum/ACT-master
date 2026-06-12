# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.

import pint
from act.core.common import ACT_ROOT, DEFAULT_FAB_YIELD
from act.core.device_data import AREA, FAB_YIELD, N_ICS, PROCESS
from act.core.models.base_logic_model import BaseLogicModel
from act.core.processes import LogicProcess
from act.core.utils.load_yaml_with_macros import load_yaml_with_macros
from act.core.utils.logger import log
from act.core.utils.units import units

DEFAULT_CPA_CONFIG = f"{ACT_ROOT}/models/logic/imec-netzero-cpa.yaml"


class IMECLogicModel(BaseLogicModel):
    """Logic model using imec.netzero carbon-per-area data.

    A simpler alternative to LogicModel that derives carbon directly
    from a carbon-per-area configuration file rather than composing
    EPA, GPA, and materials models separately.
    """

    REQUIRED_FIELDS = [PROCESS, AREA, FAB_YIELD, N_ICS]

    def __init__(self, cpa_file=DEFAULT_CPA_CONFIG) -> None:
        """Initialize the IMEC Logic Model.

        Args:
            cpa_file (str): Path to the carbon-per-area YAML configuration.
        """
        self.cpa_file = cpa_file
        raw = load_yaml_with_macros(cpa_file, delete_macros=True)
        self.cpa_model = {LogicProcess(k): units(v) for k, v in raw.items()}

    def get_cpa(
        self,
        process: LogicProcess,
        fab_yield: float = DEFAULT_FAB_YIELD,
        **kwargs,
    ) -> pint.Quantity:
        """Get carbon per area from the CPA configuration."""
        if process not in self.cpa_model:
            log.error(f"Logic process {process} not found in CPA model.")
            exit(-1)
        return self.cpa_model[process] / fab_yield

    def is_process_supported(self, process: LogicProcess) -> bool:
        return process in self.cpa_model

    def supported_processes(self) -> set:
        return set(self.cpa_model.keys())
