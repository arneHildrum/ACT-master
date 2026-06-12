# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.

from act.core.common import ACT_ROOT
from act.core.processes import LogicProcess, NOT_SCALING_PROCESSES
from act.core.utils.logger import log

DEFAULT_SCALE_FACTORS = f"{ACT_ROOT}/assets/full_scale_factors.csv"


CSV_DELIMITER = ","
UNKNOWN = -1


class PowerScalingModel:
    """Model for scaling power consumption between technology nodes.

    This model provides scale factors for estimating power changes when
    moving between different logic process nodes.

    Attributes:
        scale_factors (dict): Nested dictionary of scale factors by source and destination process.
        scale_factors_config (str): Path to the scale factors CSV file.
    """

    def __init__(self, scale_factors_config=DEFAULT_SCALE_FACTORS):
        """Initialize the Power Scaling Model.

        Args:
            scale_factors_config (str): Path to the scale factors CSV file.
        """
        self.scale_factors = dict()
        self.scale_factors_config = scale_factors_config

        with open(self.scale_factors_config) as handle:
            lines = handle.readlines()
            header_line = lines[0].split(CSV_DELIMITER)
            headers = [
                x.strip() for x in header_line[1:]
            ]  # first entry is blank and last entry has \n

            for line in lines[1:]:
                fields = [x.strip() for x in line.split(CSV_DELIMITER)]
                src = fields[0]

                try:
                    src_process = LogicProcess(src)
                    self.scale_factors[src_process] = dict()
                except ValueError as e:
                    log.debug(
                        f"Source scale factor {src} not supported by ACT. Not loading this scale factor."
                    )
                    continue

                for idx in range(len(fields[1:])):
                    dst = headers[idx].strip()
                    try:
                        dst_process = LogicProcess(dst)
                        factor = float(fields[1 + idx])
                        self.scale_factors[src_process][dst_process] = factor
                    except ValueError as e:
                        log.debug(
                            f"Destination process {dst} not supported by ACT. Not loading this scale factor."
                        )

    def get_scale_factor(self, src, dst):
        """Get the power scale factor between two processes.

        Args:
            src (LogicProcess): Source process node.
            dst (LogicProcess): Destination process node.

        Returns:
            float: Scale factor for power consumption.
        """
        # don't scale if the src or dst process is NA
        if src in NOT_SCALING_PROCESSES or dst in NOT_SCALING_PROCESSES:
            return 1.0

        factor = self.scale_factors[src][dst]
        if factor == UNKNOWN:  # don't scale if the factor is known
            return 1.0
        else:
            return self.scale_factors[src][dst]

    def is_process_supported(self, process):
        """Check if a process is supported by the scaling model.

        Args:
            process (LogicProcess): The process to check.

        Returns:
            bool: True if the process is supported.
        """
        return process in self.scale_factors
