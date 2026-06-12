# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.

"""Base class for logic carbon models.

Provides the shared get_carbon flow (process resolution, area * CPA +
packaging) and closest-process fallback logic.  Subclasses implement
get_cpa() and is_process_supported() for their specific modeling approach.
"""

from abc import abstractmethod

import pint
from act.core.carbon import Carbon, SourceType
from act.core.common import CARBON_PER_IC_PACKAGE, DEFAULT_FAB_YIELD
from act.core.models.base_model import BaseModel
from act.core.processes import LOGIC_DATA, LogicProcess
from act.core.utils.logger import log
from act.core.utils.units import g, mm2


class BaseLogicModel(BaseModel):
    """Abstract base class for logic carbon models.

    Subclasses must implement:
      - get_cpa(): return carbon per area for a process and yield
      - is_process_supported(): check if a process is in the model
      - supported_processes(): return the set of supported processes
    """

    MODEL_NAME = "logic"

    @abstractmethod
    def get_cpa(
        self, process: LogicProcess, fab_yield: float = DEFAULT_FAB_YIELD, **kwargs
    ) -> pint.Quantity:
        """Return the carbon per area for a given process and yield."""
        raise NotImplementedError

    @abstractmethod
    def is_process_supported(self, process: LogicProcess) -> bool:
        """Return True if the process is supported by this model."""
        raise NotImplementedError

    @abstractmethod
    def supported_processes(self) -> set:
        """Return the set of supported LogicProcess values."""
        raise NotImplementedError

    def get_carbon(self, device_data) -> Carbon:
        """Get total carbon emissions for a logic device.

        Resolves the process (falling back to the closest supported
        process if needed), computes CPA, and returns fabrication +
        packaging carbon.
        """
        self.validate_data(device_data)

        if self.is_process_supported(device_data.process):
            process = device_data.process
        elif device_data.process is LogicProcess.NA:
            log.error(
                f"Device '{device_data.name}': Process node is not available or unsupported "
                f"by {self.__class__.__name__}. Returning zero carbon for this device."
            )
            return Carbon(0 * g, SourceType.OTHER)
        else:
            process = self.get_closest_supported_process(device_data.process)

        area = device_data.area
        assert area.check(mm2)

        cpa = self.get_cpa(
            process=process,
            fab_yield=device_data.fab_yield,
            device_data=device_data,
        )
        carbon = Carbon(area * cpa, SourceType.FABRICATION) + Carbon(
            device_data.n_ics * CARBON_PER_IC_PACKAGE, SourceType.PACKAGING
        )
        return carbon

    def get_closest_supported_process(self, process: LogicProcess) -> LogicProcess:
        """Find the closest supported process to the given one by year.

        Args:
            process: The target process.

        Returns:
            The closest supported process whose year <= target year.
        """
        process_year = LOGIC_DATA[process].year
        closest_delta = float("inf")
        closest_process = None

        for p in self.supported_processes():
            p_year = LOGIC_DATA[p].year
            if p_year is None or process_year is None:
                continue
            if p_year <= process_year:
                delta = abs(p_year - process_year)
                if closest_process is None or delta < closest_delta:
                    closest_process, closest_delta = p, delta

        # If no year-based match, fall back to any supported process
        if closest_process is None:
            supported = list(self.supported_processes())
            if supported:
                closest_process = supported[0]

        assert closest_process is not None
        return closest_process
